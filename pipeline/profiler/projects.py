from constants import PROJECTS
from pathlib import Path
import ast
from ast import FunctionDef, AsyncFunctionDef, ClassDef
import json

class InvalidTask(Exception):
    pass

class Project:
    def __init__(self, name: str):
        self.name = name
        self.optimized = []
        self.root_dir = Path(__file__).parent / "projects" / name
        if name not in PROJECTS:
            raise InvalidTask(f"Invalid project passed! Must be in {PROJECTS}")
        
    def ready_to_patch(self) -> bool:
        return len(self.optimized) >= 10

class PyProj(Project):
    def __init__(self, name: str):
        super().__init__(name)
        self.top_functions = _speedscope_bottlenecks(name, self.root_dir)
        
def _speedscope_bottlenecks(name : str, root_dir):
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
    
        # weights rep the time on each sample
        for i, sample in enumerate(samples):
            weight = weights[i]
    
            # add weight to each frame in the stack
            if isinstance(sample, list):
                for frame_idx in sample:
                    if frame_idx not in frame_times:
                        frame_times[frame_idx] = 0
                    frame_times[frame_idx] += weight
            else:
                if sample not in frame_times:
                    frame_times[sample] = 0
                frame_times[sample] += weight
    
    # sort frames by total time (descending)
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
                line_no = frame.get('line', 0)

                snippet = _get_snippet(file_path, line_no, root_dir)
                if snippet:
                    top_functions.append(snippet)
                
                if len(top_functions) >= 10:
                    break
    
    return top_functions


# target here is 1-indexed
def _get_snippet(abs_path : str, target : int, root_dir : Path):
    with open(abs_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    relative_path = Path(abs_path).relative_to(root_dir)
    
    tree = ast.parse(''.join(lines), abs_path)
                
    best_match = None
    smallest_size = float('inf')
    for node in ast.walk(tree):
        if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
            if hasattr(node, 'decorator_list') and node.decorator_list:
                start_line = node.decorator_list[0].lineno
            else:
                start_line = node.lineno

            end_line = node.end_lineno
            
            if start_line <= target <= end_line:
                if isinstance(node, (FunctionDef, AsyncFunctionDef, ClassDef)):
                    size = end_line - start_line

                    if size < smallest_size:
                        smallest_size = size
                        best_match = node

                        start_idx, end_idx = start_line - 1, end_line - 1
                        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
                        
                        # get dedented snippet
                        snippet = '\n'.join([line[base_indent:] for line in lines[start_idx : end_line]])
                                                
                        # get enclosing scopes
                        enclosing_scopes = _get_enclosing_scopes(tree, node)

                        function = {'rel_path': relative_path,
                                    'line': lines[target - 1],
                                    'base_indent': base_indent,
                                    'code' : snippet,
                                    'start_line': start_idx,
                                    'end_line': end_idx,
                                    'scope': enclosing_scopes}
                
    if best_match:
        return function
    else:
        return None
    
def _get_enclosing_scopes(tree, target_node):
    parent_map = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    
    scopes = []
    current = target_node
    while current in parent_map:
        parent = parent_map[current]
        if isinstance(parent, (FunctionDef, AsyncFunctionDef, ClassDef)):
            scope_type = 'class' if isinstance(parent, ClassDef) else 'function'
            scopes.append({'type': scope_type, 'name': parent.name})
        current = parent
    
    return list(reversed(scopes))  # outermost first
