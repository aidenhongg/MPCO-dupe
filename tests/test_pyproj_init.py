import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change working directory to project root (needed for constants.py relative paths)
os.chdir(project_root)

from pipeline.profiler.projects import PyProj


def test_pyproj_init():
    """Test PyProj initialization on whisper_filtered0.speedscope"""
    
    # Initialize PyProj with whisper
    proj = PyProj("whisper")
    
    # Print list length
    print(f"\nLength of self.top_bottlenecks: {len(proj.top_bottlenecks)}")
    print(f"\nTop bottlenecks list:")
    print("=" * 80)
    
    # Print details for each node
    for i, node in enumerate(proj.top_bottlenecks, 1):
        print(f"\n[{i}] Node Type: {node.__class__.__name__}")
        print(f"    Name: {node.name if hasattr(node, 'name') else 'N/A'}")
        print(f"    File Location: {node.col_offset if hasattr(node, 'col_offset') else 'N/A'}")
        print(f"    Starting Line: {node.lineno if hasattr(node, 'lineno') else 'N/A'}")
        print(f"    Ending Line: {node.end_lineno if hasattr(node, 'end_lineno') else 'N/A'}")
    
    print("\n" + "=" * 80)
    print(f"\nSummary: Found {len(proj.top_bottlenecks)} bottleneck nodes")


if __name__ == "__main__":
    test_pyproj_init()
