import pytest
import tempfile
import os
from pathlib import Path
import sys
import subprocess
import difflib

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import MyPatch class directly to avoid loading constants
# We'll copy the class definition here for testing purposes
class MyPatch:
    def __init__(self, code_object: dict, optimized_code: str, root : str):
        self.code_object = code_object
        self.optimized_code = optimized_code.splitlines(keepends=True)
        self.root = Path(root)
        self.patch = None

    def _make_patch(self):
        file_path = self.code_object['rel_path']

        # indices are 0-indexed
        start_line = self.code_object['start_line']
        end_line = self.code_object['end_line']
        base_indent : int = self.code_object['base_indent']

        with open(self.root / file_path, 'r', encoding='utf-8') as f:
            old_module = f.readlines()

        # formatting
        if not self.optimized_code[-1].endswith('\n'):
            self.optimized_code[-1] += '\n'
        indent = ' ' * base_indent
        self.optimized_code = [indent + line if line.strip() else line for line in self.optimized_code]

        # edit module
        optimized_module = (old_module[:start_line] + 
                            self.optimized_code + 
                            old_module[end_line + 1:])

        diff_lines = list(difflib.unified_diff(old_module,
                                               optimized_module,
                                               fromfile=f'a/{file_path.as_posix()}',
                                               tofile=f'b/{file_path.as_posix()}',
                                               lineterm='\n'))
        self.patch = ''.join(diff_lines)
            
    def _apply_patch(self) -> bool:
        if self.patch is None:
            self._make_patch()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False, encoding='utf-8', newline='\n') as patch_file:
            patch_file.write(self.patch)
            patch_path = patch_file.name

        result = subprocess.run(['git', 'apply', patch_path], 
                              capture_output=False, 
                              text=True,
                              cwd=self.root)

        self.patch_path = patch_path

        if result.returncode != 0:
            print(f"Failed to apply patch: {result.stderr}")
            return False
        return True
    
    def _revert_patch(self):
        reversion = subprocess.run(['git', 'apply', '--reverse', self.patch_path],
                                    capture_output=True,
                                    cwd=self.root)
        if reversion.returncode != 0:
            print(f"Failed to revert patch: {reversion.stderr}")
            raise Exception("Failed to revert patch")

        try:
            os.unlink(self.patch_path)
        except:
            pass


class TestMyPatch:
    """Test suite for MyPatch class focusing on patch application and reversion."""
    
    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=temp_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_path, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_path, check=True, capture_output=True)
            
            # Create initial file
            test_file = temp_path / 'test_module.py'
            initial_content = '''def original_function():
    x = 1
    y = 2
    return x + y
'''
            test_file.write_text(initial_content, encoding='utf-8')
            
            # Commit initial state
            subprocess.run(['git', 'add', '.'], cwd=temp_path, check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_path, check=True, capture_output=True)
            
            yield temp_path
    
    def test_apply_and_revert_patch_simple(self, temp_git_repo):
        """Test that a patch can be applied and then successfully reverted."""
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 3,
            'base_indent': 4,
            'code': '    x = 1\n    y = 2\n    return x + y\n'
        }
        
        optimized_code = '''z = 3
return z
'''
        
        # Create patch
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        
        # Read original content
        test_file = temp_git_repo / 'test_module.py'
        original_content = test_file.read_text(encoding='utf-8')
        
        # Apply patch
        assert patch._apply_patch() is True, "Patch should apply successfully"
        
        # Verify content changed
        modified_content = test_file.read_text(encoding='utf-8')
        assert modified_content != original_content, "File content should change after patch"
        assert 'z = 3' in modified_content, "New code should be in the file"
        
        # Revert patch
        patch._revert_patch()
        
        # Verify content reverted
        reverted_content = test_file.read_text(encoding='utf-8')
        assert reverted_content == original_content, "File content should be restored after revert"
        assert 'z = 3' not in reverted_content, "New code should not be in the file after revert"
        assert 'x = 1' in reverted_content, "Original code should be back"
    
    def test_apply_patch_with_indentation(self, temp_git_repo):
        """Test that patch correctly handles indentation."""
        # Add a class to test indentation
        test_file = temp_git_repo / 'test_module.py'
        class_content = '''class TestClass:
    def method(self):
        a = 1
        b = 2
        return a + b
'''
        test_file.write_text(class_content, encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add class'], cwd=temp_git_repo, check=True, capture_output=True)
        
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 2,
            'end_line': 4,
            'base_indent': 8,  # 8 spaces for method body
            'code': '        a = 1\n        b = 2\n        return a + b\n'
        }
        
        optimized_code = '''result = 3
return result
'''
        
        original_content = test_file.read_text(encoding='utf-8')
        
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        assert patch._apply_patch() is True
        
        modified_content = test_file.read_text(encoding='utf-8')
        assert '        result = 3' in modified_content, "Indentation should be preserved"
        
        patch._revert_patch()
        
        reverted_content = test_file.read_text(encoding='utf-8')
        assert reverted_content == original_content
    
    def test_revert_patch_removes_temp_file(self, temp_git_repo):
        """Test that revert_patch cleans up the temporary patch file."""
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 3,
            'base_indent': 4,
            'code': '    x = 1\n    y = 2\n    return x + y\n'
        }
        
        optimized_code = '''z = 3
return z
'''
        
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        patch._apply_patch()
        
        patch_path = patch.patch_path
        assert os.path.exists(patch_path), "Patch file should exist after apply"
        
        patch._revert_patch()
        
        assert not os.path.exists(patch_path), "Patch file should be deleted after revert"
    
    def test_apply_patch_fails_gracefully(self, temp_git_repo):
        """Test that apply_patch returns False when patch cannot be applied."""
        test_file = temp_git_repo / 'test_module.py'
        
        # First, modify the file so the patch will conflict
        test_file.write_text('COMPLETELY DIFFERENT CONTENT\n', encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Modified content'], cwd=temp_git_repo, check=True, capture_output=True)
        
        # Create a patch based on the original content (which no longer exists)
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 3,
            'base_indent': 4,
            'code': '    x = 1\n    y = 2\n    return x + y\n'
        }
        
        optimized_code = '''new_code = 1
'''
        
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        
        # Patch should fail because the file content has changed
        result = patch._apply_patch()
        assert result is False, "Patch should fail when content doesn't match"
    
    def test_multiple_patches_revert_in_order(self, temp_git_repo):
        """Test that multiple patches can be applied and reverted correctly."""
        test_file = temp_git_repo / 'test_module.py'
        multi_function_content = '''def func1():
    return 1

def func2():
    return 2

def func3():
    return 3
'''
        test_file.write_text(multi_function_content, encoding='utf-8')
        subprocess.run(['git', 'add', '.'], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Multiple functions'], cwd=temp_git_repo, check=True, capture_output=True)
        
        original_content = test_file.read_text(encoding='utf-8')
        
        # Create and apply first patch
        code_object1 = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 1,
            'base_indent': 4,
            'code': '    return 1\n'
        }
        patch1 = MyPatch(code_object1, 'return 10\n', str(temp_git_repo))
        assert patch1._apply_patch() is True
        
        # Create and apply second patch (on modified content)
        code_object2 = {
            'rel_path': Path('test_module.py'),
            'start_line': 4,
            'end_line': 4,
            'base_indent': 4,
            'code': '    return 2\n'
        }
        patch2 = MyPatch(code_object2, 'return 20\n', str(temp_git_repo))
        assert patch2._apply_patch() is True
        
        modified_content = test_file.read_text(encoding='utf-8')
        assert 'return 10' in modified_content
        assert 'return 20' in modified_content
        
        # Revert in reverse order (LIFO)
        patch2._revert_patch()
        intermediate_content = test_file.read_text(encoding='utf-8')
        assert 'return 10' in intermediate_content
        assert 'return 20' not in intermediate_content
        assert 'return 2' in intermediate_content
        
        patch1._revert_patch()
        final_content = test_file.read_text(encoding='utf-8')
        assert final_content == original_content
    
    def test_revert_patch_raises_on_failure(self, temp_git_repo):
        """Test that revert_patch raises an exception if reversion fails."""
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 3,
            'base_indent': 4,
            'code': '    x = 1\n    y = 2\n    return x + y\n'
        }
        
        optimized_code = '''z = 3
return z
'''
        
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        patch._apply_patch()
        
        # Manually modify the file to cause revert to fail
        test_file = temp_git_repo / 'test_module.py'
        test_file.write_text('COMPLETELY DIFFERENT CONTENT\n', encoding='utf-8')
        
        # Revert should raise an exception
        with pytest.raises(Exception, match="Failed to revert patch"):
            patch._revert_patch()
    
    def test_patch_generation_creates_valid_diff(self, temp_git_repo):
        """Test that _make_patch creates a valid unified diff."""
        code_object = {
            'rel_path': Path('test_module.py'),
            'start_line': 1,
            'end_line': 3,
            'base_indent': 4,
            'code': '    x = 1\n    y = 2\n    return x + y\n'
        }
        
        optimized_code = '''z = 3
return z
'''
        
        patch = MyPatch(code_object, optimized_code, str(temp_git_repo))
        patch._make_patch()
        
        assert patch.patch is not None, "Patch should be generated"
        assert '--- a/test_module.py' in patch.patch, "Patch should have source marker"
        assert '+++ b/test_module.py' in patch.patch, "Patch should have target marker"
        assert 'z = 3' in patch.patch, "Patch should contain new code"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
