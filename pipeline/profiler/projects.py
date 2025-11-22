from constants import PROJECTS
from pathlib import Path
import json

class InvalidTask(Exception):
    pass

class Project:
    def __init__(self, name: str):
        self.name = name
        self.optimized = []
        if name not in PROJECTS:
            raise InvalidTask(f"Invalid project passed! Must be in {PROJECTS}")
        
    def ready_to_patch(self) -> bool:
        return len(self.optimized) >= 10

class PyProj(Project):
    def __init__(self, name: str):
        super().__init__(name)
        self.top_functions = _speedscope_bottlenecks(name)
        
# im not entirely sure how this function works so just close it & dont open it
def _speedscope_bottlenecks(name : str):
    """
    Identify the 10 unique functions with the longest runtimes from a filtered speedscope profile.
    Returns:
        List of dicts containing file path, line number, and function name for the longest runtime functions
    """
    # Define paths
    profiler_dir = Path(__file__).parent
    filtered_file = profiler_dir / "profiles" / f"{name}_filtered.speedscope"
    if not filtered_file.exists():
        raise FileNotFoundError(f"Filtered profile not found: {filtered_file}")
    print(f"Loading filtered profile from: {filtered_file}")
    
    # Load the filtered speedscope file
    with open(filtered_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get frames from shared section
    shared = data.get('shared', {})
    frames = shared.get('frames', [])
    
    if not frames:
        print("ERROR: No frames found in filtered profile")
        return []
    
    # frame time tracking
    frame_times = {}  # {frame_index : total_time}
    for profile in data.get('profiles', []):
        samples, weights = profile.get('samples', []), profile.get('weights', [])
    
        # Each sample is a stack trace, weights represent the time for that sample
        for i, sample in enumerate(samples):
            weight = weights[i]
    
            # Add weight to each frame in the stack
            if isinstance(sample, list):
                for frame_idx in sample:
                    if frame_idx not in frame_times:
                        frame_times[frame_idx] = 0
                    frame_times[frame_idx] += weight
            else:
                if sample not in frame_times:
                    frame_times[sample] = 0
                frame_times[sample] += weight
    
    # Sort frames by total time (descending)
    sorted_frames = sorted(frame_times.items(), key=lambda x: x[1], reverse=True)
    top_functions = []
    seen_names = set()
    
    for frame_idx, _ in sorted_frames:
        if frame_idx < len(frames):
            frame = frames[frame_idx]
            frame_name = frame.get('name', '')
            # avoid dupes
            if frame_name not in seen_names:
                seen_names.add(frame_name)
                file_path = frame.get('file', '')
                target_line = frame.get('line', 0)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    if target_line > len(lines) or target_line < 1:
                        continue
                    
                    line_idx = target_line - 1

                    target_line_text = lines[line_idx]
                    target_indent = len(target_line_text) - len(target_line_text.lstrip())

                    # if module level
                    if target_indent == 0:
                        # Module-level: find boundaries to next object definition

                        # Find start: go backwards until we hit another object definition or start of file
                        start_idx = line_idx
                        for i in range(line_idx - 1, -1, -1):
                            line = lines[i]
                            stripped = line.lstrip()
                            # Check if this is a module-level definition (class/def/async def at indent 0)
                            if stripped and not line[0].isspace() and (stripped.startswith('def ') or 
                                                                         stripped.startswith('class ') or 
                                                                         stripped.startswith('async def ')):
                                start_idx = i + 1
                                break
                        else:
                            start_idx = 0

                        # Find end: go forwards until we hit another object definition or end of file
                        end_idx = line_idx
                        for i in range(line_idx + 1, len(lines)):
                            line = lines[i]
                            stripped = line.lstrip()
                            # Check if this is a module-level definition (class/def/async def at indent 0)
                            if stripped and not line[0].isspace() and (stripped.startswith('def ') or 
                                                                         stripped.startswith('class ') or 
                                                                         stripped.startswith('async def ')):
                                end_idx = i
                                break
                        else:
                            end_idx = len(lines)

                    else:
                        # Not module-level: find the complete object (function/method/class) containing this line

                        # Find the start of the object by going backwards to find the definition line
                        start_idx = line_idx
                        for i in range(line_idx, -1, -1):
                            line = lines[i]
                            line_indent = len(line) - len(line.lstrip())

                            # Look for a definition line at a lower or equal indentation level
                            if line_indent < target_indent or (line_indent == target_indent and i == line_idx):
                                stripped = line.lstrip()
                                if stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('async def '):
                                    start_idx = i
                                    obj_indent = line_indent
                                    break
                        else:
                            # Couldn't find definition, use target line as start
                            start_idx = line_idx
                            obj_indent = target_indent

                        # Find the end: continue until we find a line at the same or lower indentation
                        # that's not empty and not part of the current block
                        end_idx = start_idx + 1
                        for i in range(start_idx + 1, len(lines)):
                            line = lines[i]
                            stripped = line.strip()

                            # Skip empty lines and comments
                            if not stripped or stripped.startswith('#'):
                                end_idx = i + 1
                                continue
                            
                            line_indent = len(line) - len(line.lstrip())

                            # If we find a line at same or lower indentation than the object definition, we've reached the end
                            if line_indent <= obj_indent:
                                break
                            
                            end_idx = i + 1

                        # Extract snippet
                    
                    snippet = ''.join(lines[start_idx:end_idx])
                    base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())

                    function = {'name': frame_name,
                                'file': file_path,
                                'line': target_line,
                                'base_indent': base_indent,
                                'code' : snippet,
                                'start_line': start_idx,
                                'end_line': end_idx}
                    
                    top_functions.append(function)
                    if len(top_functions) >= 10:
                        break

                except Exception as e:
                    print(f"Error extracting snippet from {file_path}:{target_line}: {e}")
                    continue

    
    return top_functions