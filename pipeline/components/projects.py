from ast import FunctionDef, AsyncFunctionDef, ClassDef
import ast

from pathlib import Path
import json

from constants import PROJECTS
 
class InvalidTask(Exception):
    pass

class Project:
    def __init__(self, name: str):
        self.name = name
        self.optimized = []
        self.root_dir = Path(__file__).parent.parent / "profiler" / "projects" / name
        self.revisions = 0

        if name not in PROJECTS:
            raise InvalidTask(f"Invalid project passed! Must be in {PROJECTS}")
        
    def ready_to_patch(self) -> bool:
        return len(self.optimized) >= 10

class PyProj(Project):
    def __init__(self, name: str):
        super().__init__(name)
        self.top_bottlenecks = _speedscope_bottlenecks(self.name) # should return list of nodes

    def load_function(self): # rename to load bottleneck
        current_node = self.top_bottlenecks[self.revisions]
        return _node_to_obj(current_node, self.root_dir)
        
def _speedscope_bottlenecks(name : str):
    # Define paths
    profiler_dir = Path(__file__).parent.parent / "profiler"
    filtered_file = profiler_dir / "profiles" / f"{name}_filtered{0}.speedscope"
    if not filtered_file.exists():
        raise FileNotFoundError(f"Filtered profile not found: {filtered_file}")
    
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
    seen_names = set()
    seen_nodes = set()
    
    top_nodes = []

    for frame_idx, _ in sorted_frames:
        if frame_idx < len(frames):
            frame = frames[frame_idx]
            frame_name = frame.get('name', '')
            # avoid dupes
            if frame_name not in seen_names:
                seen_names.add(frame_name)
                file_path = frame.get('file', '')
                line_no = frame.get('line', 0)

                node = _get_node(file_path, line_no)
                node_dump = ast.dump(node) 
                if node_dump not in seen_nodes:
                    seen_nodes.add(node_dump)
                    top_nodes.append(node)

                    if len(top_nodes) >= 10:
                        break
    
    if len(top_nodes) < 10:
        print("WARNING: Not enough top nodes found in profile")

    return top_nodes
    
def _get_node(abs_path : str, target : int):
    with open(abs_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
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
    best_match.filename = abs_path
    return best_match

def _node_to_obj(node, root_dir : Path):
    abs_path = node.filename

    with open(abs_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    relative_path = Path(abs_path).relative_to(root_dir)
    
    tree = ast.parse(''.join(lines), abs_path)
    node_dump = ast.dump(node, include_attributes=False)

    for node_tmp in ast.walk(tree):
        if node_dump == ast.dump(node_tmp, include_attributes=False):
            node = node_tmp
            break

    if hasattr(node, 'decorator_list') and node.decorator_list:
        start_line = node.decorator_list[0].lineno
    else:
        start_line = node.lineno

    end_line = node.end_lineno
    
    start_idx, end_idx = start_line - 1, end_line - 1
    base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    # get dedented snippet
    snippet = '\n'.join([line[base_indent:] for line in lines[start_idx : end_line]])
    
    # get enclosing scopes
    enclosing_scopes = _get_enclosing_scopes(tree, node)

    function = {'rel_path': relative_path,
                'base_indent': base_indent,
                'code' : snippet,
                'start_line': start_idx,
                'end_line': end_idx,
                'scope': enclosing_scopes}
        
    return function

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

# two methods here:
# 1. comapre clean dumps of nodes in edited files to find the target
# 2. Include info about enclosing scopes & just compare enclosing scopes + name

# Using method 1 for now but if not working 2
# ALSO: edge case of encloding object being edited
#   -Not worried because if signature of inner objects are altered then tests will fail