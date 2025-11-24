import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.profiler.projects import _get_snippet


class TestGetSnippet:
    """Test suite for _get_snippet function covering various edge cases."""
    
    def test_target_line_on_function_signature(self):
        """Test when target line is on the function signature (def line)."""
        code = '''def my_function():
    """Docstring."""
    x = 1
    return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 1)  # Line 1 is "def my_function():"
            assert result is not None
            assert 'def my_function():' in result['code']
            assert result['start_line'] == 0
            assert result['end_line'] == 3
        finally:
            os.unlink(temp_path)
    
    def test_target_line_on_function_with_decorator(self):
        """Test when target line is on function signature with decorators."""
        code = '''@decorator1
@decorator2
def decorated_function():
    """Decorated function."""
    return True
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 3)  # Line 3 is "def decorated_function():"
            assert result is not None
            assert '@decorator1' in result['code']
            assert '@decorator2' in result['code']
            assert 'def decorated_function():' in result['code']
            assert result['start_line'] == 0  # Should start from first decorator
        finally:
            os.unlink(temp_path)
    
    def test_target_line_on_decorator(self):
        """Test when target line is on a decorator itself."""
        code = '''@my_decorator
def func_with_decorator():
    x = 42
    return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 1)  # Line 1 is "@my_decorator"
            assert result is not None
            assert '@my_decorator' in result['code']
            assert 'def func_with_decorator():' in result['code']
            assert result['start_line'] == 0
        finally:
            os.unlink(temp_path)
    
    def test_target_line_module_level_no_function(self):
        """Test when target line is at module level (not inside any function/class)."""
        code = '''import os
import sys

# Module level comment
MODULE_CONSTANT = 42

def some_function():
    return True
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 5)  # Line 5 is "MODULE_CONSTANT = 42"
            assert result is None  # Should return None for module-level code
        finally:
            os.unlink(temp_path)
    
    def test_target_line_on_import_statement(self):
        """Test when target line is on an import statement."""
        code = '''import os
import sys
from pathlib import Path

def my_function():
    return 1
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 2)  # Line 2 is "import sys"
            assert result is None  # Should return None for import statements
        finally:
            os.unlink(temp_path)
    
    def test_target_line_in_middle_of_function_body(self):
        """Test when target line is in the middle of a function body."""
        code = '''def calculate_sum(a, b):
    # Start of function
    result = a + b
    print(result)
    return result
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 3)  # Line 3 is "result = a + b"
            assert result is not None
            assert 'def calculate_sum(a, b):' in result['code']
            assert 'result = a + b' in result['code']
            assert result['start_line'] == 0
            assert result['end_line'] == 4
        finally:
            os.unlink(temp_path)
    
    def test_target_line_in_nested_function(self):
        """Test when target line is inside a nested function (should return innermost)."""
        code = '''def outer_function():
    x = 1
    
    def inner_function():
        y = 2
        return y
    
    return inner_function()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 5)  # Line 5 is "y = 2" in inner function
            assert result is not None
            assert 'def inner_function():' in result['code']
            # Should return the smallest matching scope (inner function)
            assert result['code'].count('def') == 1
        finally:
            os.unlink(temp_path)
    
    def test_target_line_in_class_method(self):
        """Test when target line is inside a class method."""
        code = '''class MyClass:
    def __init__(self):
        self.value = 42
    
    def my_method(self):
        """Method docstring."""
        return self.value * 2
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 7)  # Line 7 is "return self.value * 2"
            assert result is not None
            assert 'def my_method(self):' in result['code']
            # Should return just the method, not the entire class
            assert result['start_line'] == 4
        finally:
            os.unlink(temp_path)
    
    def test_target_line_on_class_definition(self):
        """Test when target line is on the class definition line."""
        code = '''class TestClass:
    """Test class docstring."""
    
    def method(self):
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 1)  # Line 1 is "class TestClass:"
            assert result is not None
            assert 'class TestClass:' in result['code']
            assert result['start_line'] == 0
        finally:
            os.unlink(temp_path)
    
    def test_target_line_in_class_with_decorator(self):
        """Test when target line is in a decorated class."""
        code = '''@dataclass
class DecoratedClass:
    value: int
    
    def method(self):
        return self.value
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 2)  # Line 2 is "class DecoratedClass:"
            assert result is not None
            assert '@dataclass' in result['code']
            assert 'class DecoratedClass:' in result['code']
            assert result['start_line'] == 0  # Should include decorator
        finally:
            os.unlink(temp_path)
    
    def test_target_line_async_function(self):
        """Test when target line is in an async function."""
        code = '''async def async_function():
    """Async function."""
    await some_operation()
    return True
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 3)  # Line 3 is "await some_operation()"
            assert result is not None
            assert 'async def async_function():' in result['code']
            assert result['start_line'] == 0
        finally:
            os.unlink(temp_path)
    
    def test_target_line_with_indented_code(self):
        """Test that base_indent is correctly calculated for indented code."""
        code = '''class OuterClass:
    class InnerClass:
        def inner_method(self):
            x = 1
            return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 4)  # Line 4 is "x = 1"
            assert result is not None
            assert 'def inner_method(self):' in result['code']
            # base_indent should be 8 spaces (2 levels of 4-space indentation)
            assert result['base_indent'] == 8
        finally:
            os.unlink(temp_path)
    
    def test_multiple_functions_returns_smallest(self):
        """Test that when target line is in nested scopes, smallest scope is returned."""
        code = '''def outer():
    def middle():
        def inner():
            x = 1
            return x
        return inner()
    return middle()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 4)  # Line 4 is "x = 1"
            assert result is not None
            # Should return the innermost function
            assert 'def inner():' in result['code']
            assert result['code'].strip().startswith('def inner():')
        finally:
            os.unlink(temp_path)
    
    def test_target_line_between_functions(self):
        """Test when target line is between functions at module level."""
        code = '''def function1():
    return 1

# Comment between functions
VARIABLE = 42

def function2():
    return 2
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 5)  # Line 5 is "VARIABLE = 42"
            assert result is None  # Should return None for module-level code
        finally:
            os.unlink(temp_path)
    
    def test_result_structure(self):
        """Test that the returned dictionary has the correct structure."""
        code = '''def test_function():
    return 42
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            result = _get_snippet(temp_path, 1)
            assert result is not None
            # Check all required keys exist
            assert 'file' in result
            assert 'line' in result
            assert 'base_indent' in result
            assert 'code' in result
            assert 'start_line' in result
            assert 'end_line' in result
            # Check types
            assert isinstance(result['file'], str)
            assert isinstance(result['line'], str)
            assert isinstance(result['base_indent'], int)
            assert isinstance(result['code'], str)
            assert isinstance(result['start_line'], int)
            assert isinstance(result['end_line'], int)
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
