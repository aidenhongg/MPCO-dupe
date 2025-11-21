from pathlib import Path
import sys
import subprocess
import json

def is_import_line(file_path: str, line_number: int) -> bool:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
                        
        line = lines[line_number - 1].strip()
        
        if line.startswith('import ') or line.startswith('from '):
            return True
            
        return False
    except Exception:
        return False

def get_speedscope(proj_name : str):
    profiler_dir = Path(__file__).parent
    
    venv_python = profiler_dir / "venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print(f"Error: Virtual environment not found at {venv_python}")
        sys.exit(1)
    
    print("Installing whisper in editable mode...")
    whisper_path = profiler_dir / "projects" / "whisper"
    install_result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-e", str(whisper_path)],
        cwd=profiler_dir
    )
    
    if install_result.returncode != 0:
        print("Failed to install whisper")
        sys.exit(1)
    
    # Run py-spy with pytest
    print("Running py-spy profiler...")
    output_file = profiler_dir / "profiles" / "whisper_profile.speedscope"
    test_path = profiler_dir / "projects" / "whisper" / "tests"
    
    profile_result = subprocess.run(
        [
            "py-spy", "record",
            "-f", "speedscope",
            "--full-filenames",
            "-o", str(output_file),
            "--subprocesses",
            "--",
            str(venv_python), "-m", "pytest", str(test_path)
        ],
        cwd=profiler_dir
    )
    
    if profile_result.returncode != 0:
        print("Profiling failed")
        sys.exit(1)
    
    print(f"Profiling complete. Output saved to {output_file}")

def filter_speedscope(proj_name : str):
    """
    Filter speedscope profile to keep only functions from a given project.
    Removes external library calls and import statements.
    """
    profiler_dir = Path(__file__).parent
    input_file = profiler_dir / "profiles" / f"{proj_name}_profile.speedscope"
    output_file = profiler_dir / "profiles" / f"{proj_name}_filtered.speedscope"
    project_path = profiler_dir / "projects" / proj_name
    
    project_abs = str(project_path.resolve()).replace('\\', '/')
    
    print(f"Loading profile from: {input_file}")
    print(f"Project path: {project_abs}")
    
    # Load the speedscope file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get frames from shared section
    shared = data.get('shared', {})
    if 'frames' not in shared:
        print("ERROR: No frames found in shared section")
        return
    
    original_frames = shared['frames']
    original_frame_count = len(original_frames)
    
    print(f"Original frame count: {original_frame_count}")
    
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
        if frame_name == '<module>' and frame_file and is_import_line(frame_file, frame.get('line', 0)):
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
    
    filtered_frame_count = len(filtered_frames)
    print(f"Filtered frame count: {filtered_frame_count}")
    
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
                print(f"Updated {len(new_samples)} samples and {len(new_weights)} weights in profile")
            else:
                print(f"Updated {len(new_samples)} samples in profile")
    
    # Save the filtered profile
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nFiltered profile saved to: {output_file}")
    print(f"Remaining frames: {filtered_frame_count}")
    
    print(f"\n✓ Success: {filtered_frame_count} frames remaining")
