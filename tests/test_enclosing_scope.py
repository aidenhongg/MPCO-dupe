import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.components.projects import _get_snippet


class TestEnclosingScope:
    """Test suite for _get_snippet function focusing on enclosing scope detection."""
    
    def test_no_enclosing_scope_module_level_function(self):
        """Test that a module-level function has no enclosing scope."""
        code = '''def module_function():
    x = 1
    return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 2, root_dir)  # Line 2 is "x = 1"
            assert result is not None
            assert 'scope' in result
            assert result['scope'] == []  # No enclosing scope
        finally:
            os.unlink(temp_path)
    
    def test_no_enclosing_scope_module_level_class(self):
        """Test that a module-level class has no enclosing scope."""
        code = '''class MyClass:
    def method(self):
        pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 1, root_dir)  # Line 1 is class definition
            assert result is not None
            assert 'scope' in result
            assert result['scope'] == []  # No enclosing scope
        finally:
            os.unlink(temp_path)
    
    def test_method_enclosed_in_class(self):
        """Test that a method correctly identifies its enclosing class."""
        code = '''class MyClass:
    def my_method(self):
        x = 42
        return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 3, root_dir)  # Line 3 is "x = 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 1
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'MyClass'
        finally:
            os.unlink(temp_path)
    
    def test_nested_function_enclosed_in_function(self):
        """Test that a nested function identifies its enclosing function."""
        code = '''def outer_function():
    def inner_function():
        return 42
    return inner_function()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 3, root_dir)  # Line 3 is "return 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 1
            assert result['scope'][0]['type'] == 'function'
            assert result['scope'][0]['name'] == 'outer_function'
        finally:
            os.unlink(temp_path)
    
    def test_deeply_nested_functions(self):
        """Test multiple levels of nested functions."""
        code = '''def level1():
    def level2():
        def level3():
            x = 1
            return x
        return level3()
    return level2()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 4, root_dir)  # Line 4 is "x = 1"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 2
            # Outermost first
            assert result['scope'][0]['type'] == 'function'
            assert result['scope'][0]['name'] == 'level1'
            assert result['scope'][1]['type'] == 'function'
            assert result['scope'][1]['name'] == 'level2'
        finally:
            os.unlink(temp_path)
    
    def test_nested_class_in_class(self):
        """Test nested class structure."""
        code = '''class OuterClass:
    class InnerClass:
        def inner_method(self):
            return 42
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 4, root_dir)  # Line 4 is "return 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 2
            # Outermost first
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'OuterClass'
            assert result['scope'][1]['type'] == 'class'
            assert result['scope'][1]['name'] == 'InnerClass'
        finally:
            os.unlink(temp_path)
    
    def test_method_in_nested_class(self):
        """Test method inside a nested class."""
        code = '''class Outer:
    class Inner:
        def method(self):
            x = 1
            return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 3, root_dir)  # Line 3 is method definition
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 2
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'Outer'
            assert result['scope'][1]['type'] == 'class'
            assert result['scope'][1]['name'] == 'Inner'
        finally:
            os.unlink(temp_path)
    
    def test_function_inside_class_method(self):
        """Test nested function inside a class method."""
        code = '''class MyClass:
    def method(self):
        def nested_func():
            return 42
        return nested_func()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 4, root_dir)  # Line 4 is "return 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 2
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'MyClass'
            assert result['scope'][1]['type'] == 'function'
            assert result['scope'][1]['name'] == 'method'
        finally:
            os.unlink(temp_path)
    
    def test_async_function_nested(self):
        """Test async function properly identified in enclosing scope."""
        code = '''async def outer_async():
    async def inner_async():
        await something()
        return True
    return await inner_async()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 3, root_dir)  # Line 3 is "await something()"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 1
            assert result['scope'][0]['type'] == 'function'  # async is still type 'function'
            assert result['scope'][0]['name'] == 'outer_async'
        finally:
            os.unlink(temp_path)
    
    def test_complex_nesting_mixed(self):
        """Test complex nesting with mixed classes and functions."""
        code = '''class A:
    def method_a(self):
        class B:
            def method_b(self):
                def func_c():
                    return 42
                return func_c()
        return B()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 6, root_dir)  # Line 6 is "return 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 4
            # Verify the chain from outermost to innermost
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'A'
            assert result['scope'][1]['type'] == 'function'
            assert result['scope'][1]['name'] == 'method_a'
            assert result['scope'][2]['type'] == 'class'
            assert result['scope'][2]['name'] == 'B'
            assert result['scope'][3]['type'] == 'function'
            assert result['scope'][3]['name'] == 'method_b'
        finally:
            os.unlink(temp_path)
    
    def test_scope_order_is_outermost_first(self):
        """Explicitly test that scope order is from outermost to innermost."""
        code = '''class Outer:
    class Middle:
        class Inner:
            def method(self):
                x = 1
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 5, root_dir)  # Line 5 is "x = 1"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 3
            # Must be in order from outermost to innermost
            assert result['scope'][0]['name'] == 'Outer'
            assert result['scope'][1]['name'] == 'Middle'
            assert result['scope'][2]['name'] == 'Inner'
        finally:
            os.unlink(temp_path)
    
    def test_decorated_class_method(self):
        """Test that decorators don't affect scope detection."""
        code = '''class MyClass:
    @property
    def my_property(self):
        return self._value
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 4, root_dir)  # Line 4 is "return self._value"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 1
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'MyClass'
        finally:
            os.unlink(temp_path)
    
    def test_staticmethod_in_class(self):
        """Test static method correctly identifies class scope."""
        code = '''class MyClass:
    @staticmethod
    def static_method():
        x = 42
        return x
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        
        try:
            root_dir = Path(temp_path).parent
            result = _get_snippet(temp_path, 4, root_dir)  # Line 4 is "x = 42"
            assert result is not None
            assert 'scope' in result
            assert len(result['scope']) == 1
            assert result['scope'][0]['type'] == 'class'
            assert result['scope'][0]['name'] == 'MyClass'
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
