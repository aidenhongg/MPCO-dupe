from pathlib import Path
import xml.etree.ElementTree as ET

import sys
import subprocess
import json

PROFILER_DIR = Path(__file__).parent
VENV_PYTHON = PROFILER_DIR / "venv" / "Scripts" / "python.exe"

def fix_venv(proj_name : str):
    if not VENV_PYTHON.exists():
        print(f"Error: Virtual environment not found at {VENV_PYTHON}")
        sys.exit(1)

    print(f"Reinitializing {proj_name} at correct path...")
    proj_path = PROFILER_DIR / "projects" / proj_name

    install_result = subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "install", "-e", str(proj_path)],
        cwd=PROFILER_DIR,
        capture_output=True)
    
    if install_result.returncode != 0:
        print(f"Failed to install {proj_name}")
        sys.exit(1)


# fixing venv should be refactored into different func
def get_pyprofile(proj_name : str, revision_no = 0, testing_patch = False) -> float:
    output_file = PROFILER_DIR / "profiles" / f"{proj_name}_profile{revision_no}.speedscope"

    test_path = PROFILER_DIR / "projects" / proj_name / "tests"
    report_file = PROFILER_DIR / "temp" / "report.xml"
    
    # run py-spy with pytest
    print("Running py-spy profiler...")
    try:
        profile_results = subprocess.run(["py-spy", "record",
                                            "-f", "speedscope",
                                            "--full-filenames",
                                            "-o", str(output_file),
                                            "--subprocesses",
                                            "--",
                                            str(VENV_PYTHON), "-m", "pytest", 
                                            str(test_path), f"--tb={"short" if testing_patch else "no"}", 
                                            f"--junit-xml={report_file}"],
                                            capture_output=testing_patch,
                                            cwd=PROFILER_DIR)

    except KeyboardInterrupt:
        print("Tests halted - speedscope saved")
    
    root = ET.parse(report_file).getroot()
    report = root if root.tag == 'testsuite' else root.find('testsuite')

    errors = int(report.get('errors', 0))
    if errors > 0:
        print(f"Error: Test suite encountered {errors} errors")
        return None, None, None
    
    failure_count = int(report.get('failures', 0))
    duration = float(report.get('time', 0.0))
    
    # finally generate filtered speedscope
    _filter_speedscope(proj_name, revision_no)

    return failure_count, duration, profile_results

# probably merge into get_pyprofile
def _filter_speedscope(proj_name : str, revision_no = 0):
    """
    Filter speedscope profile to keep only functions from a given project.
    Removes external library calls and import statements.
    """
    profiler_dir = Path(__file__).parent
    input_file = profiler_dir / "profiles" / f"{proj_name}_profile{revision_no}.speedscope"
    output_file = profiler_dir / "profiles" / f"{proj_name}_filtered{revision_no}.speedscope"
    project_path = profiler_dir / "projects" / proj_name
    
    project_abs = str(project_path.resolve()).replace('\\', '/')
        
    # Load the speedscope file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get frames from shared section
    shared = data.get('shared', {})
    if 'frames' not in shared:
        print("ERROR: No frames found in shared section")
        return
    
    original_frames = shared['frames']
        
    # Filter frames
    filtered_frames = []
    frame_index_map = {}  # Map old index to new index
    
    for idx, frame in enumerate(original_frames):
        frame_name = frame.get('name', '')
        frame_file = frame.get('file', '')
        
        # Normalize file path for comparison
        if frame_file:
            frame_file_normalized = frame_file.replace('\\', '/')
        else:
            frame_file_normalized = ''
        
        # Skip import statements and frozen importlib
        if '<frozen importlib' in frame_file or 'import>' in frame_name:
            continue
        
        # Skip <module> frames that are on import lines
        if frame_name == '<module>' and frame_file and _is_import_line(frame_file, frame.get('line', 0)):
            continue
        
        # Skip test files
        if '/tests/' in frame_file_normalized or '\\tests\\' in frame_file_normalized:
            continue
        
        # Skip frames that mention tests in their name (like pytest commands)
        if 'pytest' in frame_name.lower() or '/tests' in frame_name or '\\tests' in frame_name:
            continue
        
        # Keep frames from  project
        if frame_file_normalized and project_abs.lower() in frame_file_normalized.lower():
            frame_index_map[idx] = len(filtered_frames)
            filtered_frames.append(frame)
        # Also keep frames without file info but with project-related names (but not test-related)
        elif not frame_file_normalized and (proj_name in frame_name.lower()):
            frame_index_map[idx] = len(filtered_frames)
            filtered_frames.append(frame)
        
    # Update the shared frames
    data['shared']['frames'] = filtered_frames
    
    # Update sample indices in all profiles to match new frame indices
    for profile in data.get('profiles', []):
        if 'samples' in profile:
            new_samples = []
            new_weights = []
            original_weights = profile.get('weights', [])
            
            for i, sample in enumerate(profile['samples']):
                if isinstance(sample, list):
                    # Remap frame indices in the stack
                    new_sample = [frame_index_map[frame_idx] for frame_idx in sample if frame_idx in frame_index_map]
                    if new_sample:  # Only keep non-empty samples
                        new_samples.append(new_sample)
                        # Keep corresponding weight if it exists
                        if i < len(original_weights):
                            new_weights.append(original_weights[i])
                else:
                    if sample in frame_index_map:
                        new_samples.append(frame_index_map[sample])
                        # Keep corresponding weight if it exists
                        if i < len(original_weights):
                            new_weights.append(original_weights[i])
            
            profile['samples'] = new_samples
            if original_weights:
                profile['weights'] = new_weights
    
    # Save the filtered profile
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    

def _is_import_line(file_path: str, line_number: int) -> bool:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
                        
        line = lines[line_number - 1].strip()
        
        if line.startswith('import ') or line.startswith('from '):
            return True
            
        return False
    except Exception:
        return False

