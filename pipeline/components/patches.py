from pathlib import Path
import subprocess
import tempfile
import difflib
import os

class MyPatch:
    def __init__(self, code_object: dict, optimized_code: str, root : str):
        self.code_object = code_object
        self.optimized_code = optimized_code.splitlines(keepends=True)
        self.root = Path(root)
        self.patch = None

        self.empty = False

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
            
    def apply_patch(self) -> bool:
        if self.patch is None:
            self._make_patch()

        if not self.patch or self.patch.strip() == '':
            print(f"WARNING: Empty patch generated!")
            print(f"  start_line: {self.code_object['start_line']}")
            print(f"  end_line: {self.code_object['end_line']}")
            print(f"  optimized_code length: {len(self.optimized_code)}")
            self.empty = True
            return True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False, encoding='utf-8', newline='\n') as patch_file:
            patch_file.write(self.patch)
            patch_path = patch_file.name

        result = subprocess.run(['git', 'apply', '--whitespace=nowarn', patch_path], 
                              capture_output=True, 
                              text=True,
                              cwd=self.root)

        self.patch_path = patch_path

        if result.returncode != 0:
            print(f"Failed to apply patch: {result.stderr}")
            return False
        return True
    
    def revert_patch(self):
        if self.empty:
            return

        reversion = subprocess.run(['git', 'apply', '--whitespace=nowarn', '--reverse', self.patch_path],
                                    capture_output=True,
                                    cwd=self.root)
        if reversion.returncode != 0:
            print(f"Failed to revert patch: {reversion.stderr}")
            raise Exception("Failed to revert patch")

        try:
            os.unlink(self.patch_path)
        except:
            pass