import sys
from pathlib import Path

# Add parent directory to path to import projects module
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.components.projects import _get_snippet

def test_find_tokenizer_snippet():
    """
    Test _get_snippet() on tokenizer.py to find the snippet that matches oldobj.txt content.
    Iterates through each line of tokenizer.py until we find a snippet containing the target lines.
    """
    # Setup paths
    root_dir = Path(__file__).parent.parent / "pipeline" / "profiler" / "projects" / "whisper"
    tokenizer_path = root_dir / "whisper" / "tokenizer.py"
    oldobj_path = Path(__file__).parent.parent / "oldobj.txt"
    
    # Read oldobj.txt and get the target content (lines[1:-1] means skip first and last line)
    with open(oldobj_path, 'r', encoding='utf-8') as f:
        oldobj_lines = f.readlines()
    
    # Get target content: skip first line and last line
    target_lines = oldobj_lines[1:-1]
    target_content = ''.join(target_lines).strip()
    
    # Also create a version with normalized whitespace for matching
    target_content_normalized = '\n'.join(line.strip() for line in target_lines if line.strip())
    
    print(f"Target content from oldobj.txt (lines[1:-1]):")
    print("=" * 80)
    print(target_content)
    print("=" * 80)
    print()
    
    # Count total lines in tokenizer.py
    with open(tokenizer_path, 'r', encoding='utf-8') as f:
        total_lines = len(f.readlines())
    
    print(f"Testing {total_lines} lines in tokenizer.py...")
    print()
    
    # Test each line as a target line
    matches_found = []
    smallest_match = None
    smallest_size = float('inf')
    
    for target_line in range(1, total_lines + 1):
        snippet = _get_snippet(str(tokenizer_path), target_line, root_dir)
        
        if snippet:
            # Check if the snippet contains the target content
            snippet_code = snippet['code'].strip()
            snippet_normalized = '\n'.join(line.strip() for line in snippet_code.split('\n') if line.strip())
            
            # Check if target content is in the snippet (with flexible whitespace matching)
            if target_content in snippet_code or target_content_normalized in snippet_normalized:
                snippet_size = snippet['end_line'] - snippet['start_line']
                match_info = {
                    'target_line': target_line,
                    'start_line': snippet['start_line'],
                    'end_line': snippet['end_line'],
                    'base_indent': snippet['base_indent'],
                    'rel_path': snippet['rel_path'],
                    'code': snippet['code'],
                    'size': snippet_size
                }
                matches_found.append(match_info)
                
                # Track smallest match
                if snippet_size < smallest_size:
                    smallest_size = snippet_size
                    smallest_match = match_info
    
    # Summary
    print("=" * 80)
    print(f"SUMMARY: Found {len(matches_found)} matching snippet(s)")
    print("=" * 80)
    
    if smallest_match:
        print(f"\n✓ SMALLEST MATCH FOUND")
        print(f"  Target line: {smallest_match['target_line']}")
        print(f"  Start line (0-indexed): {smallest_match['start_line']}")
        print(f"  End line (0-indexed): {smallest_match['end_line']}")
        print(f"  Start line (1-indexed): {smallest_match['start_line'] + 1}")
        print(f"  End line (1-indexed): {smallest_match['end_line'] + 1}")
        print(f"  Size: {smallest_match['size']} lines")
        print(f"  Base indent: {smallest_match['base_indent']}")
        print(f"  Relative path: {smallest_match['rel_path']}")
        
        print(f"\nFull snippet code:")
        print("=" * 80)
        print(smallest_match['code'])
        print("=" * 80)
        
        assert len(matches_found) > 0, "Expected to find at least one matching snippet"
    else:
        print("\nNo matches found!")
        assert False, "Expected to find matching snippet containing oldobj.txt content"

if __name__ == "__main__":
    test_find_tokenizer_snippet()
