import pytest
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.pipeline import _assemble_results


class TestAssembleResults:
    """Test suite for _assemble_results function."""
    
    def test_basic_single_snippet(self):
        """Test assembling results with a single snippet and single original-edited pair."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{'original_code_1': 'edited_code_1'}]
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = [3]
        runtimes = [1.5, 2.0, 1.8]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 1
        assert master_table.iloc[0]['original_snippet'] == 'original_code_1'
        assert master_table.iloc[0]['edited_snippet'] == 'edited_code_1'
        assert master_table.iloc[0]['project'] == 'test_project'
        assert master_table.iloc[0]['optimizer'] == 'test_optimizer'
        assert master_table.iloc[0]['prompt'] == 'test prompt'
        assert master_table.iloc[0]['prompt_type'] == 'task'
        assert master_table.iloc[0]['failed_attempts'] == 3
        assert master_table.iloc[0]['avg_runtime'] == pytest.approx(1.7666666, rel=1e-5)
    
    def test_multiple_snippets_single_pair_each(self):
        """Test assembling results with multiple snippets, each with one original-edited pair."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [
            {'original_1': 'edited_1'},
            {'original_2': 'edited_2'},
            {'original_3': 'edited_3'}
        ]
        proj_name = 'project_x'
        optim_name = 'optimizer_y'
        prompt = 'optimize this code'
        prompt_type = 'model'
        all_attempts = [1, 2, 3]
        runtimes = [2.0, 3.0, 4.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 3
        assert master_table.iloc[0]['original_snippet'] == 'original_1'
        assert master_table.iloc[0]['failed_attempts'] == 1
        assert master_table.iloc[1]['original_snippet'] == 'original_2'
        assert master_table.iloc[1]['failed_attempts'] == 2
        assert master_table.iloc[2]['original_snippet'] == 'original_3'
        assert master_table.iloc[2]['failed_attempts'] == 3
        # All should have same avg_runtime
        assert master_table.iloc[0]['avg_runtime'] == 3.0
        assert master_table.iloc[1]['avg_runtime'] == 3.0
        assert master_table.iloc[2]['avg_runtime'] == 3.0
    
    def test_single_snippet_multiple_pairs(self):
        """Test assembling results with a single snippet containing multiple original-edited pairs."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{
            'original_a': 'edited_a',
            'original_b': 'edited_b',
            'original_c': 'edited_c'
        }]
        proj_name = 'multi_pair_project'
        optim_name = 'multi_pair_optimizer'
        prompt = 'refactor code'
        prompt_type = 'project'
        all_attempts = [5]
        runtimes = [10.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 3
        # All rows should have the same failed_attempts and avg_runtime
        for i in range(3):
            assert master_table.iloc[i]['failed_attempts'] == 5
            assert master_table.iloc[i]['avg_runtime'] == 10.0
            assert master_table.iloc[i]['project'] == 'multi_pair_project'
        
        # Check that all original-edited pairs are present
        originals = set(master_table['original_snippet'])
        assert 'original_a' in originals
        assert 'original_b' in originals
        assert 'original_c' in originals
    
    def test_multiple_snippets_multiple_pairs(self):
        """Test assembling results with multiple snippets, each containing multiple pairs."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [
            {'orig_1a': 'edit_1a', 'orig_1b': 'edit_1b'},
            {'orig_2a': 'edit_2a', 'orig_2b': 'edit_2b', 'orig_2c': 'edit_2c'}
        ]
        proj_name = 'complex_project'
        optim_name = 'complex_optimizer'
        prompt = 'improve performance'
        prompt_type = 'task'
        all_attempts = [2, 4]
        runtimes = [5.0, 6.0, 7.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        # Should have 2 + 3 = 5 rows total
        assert len(master_table) == 5
        
        # First two rows should have 2 failed_attempts
        assert master_table.iloc[0]['failed_attempts'] == 2
        assert master_table.iloc[1]['failed_attempts'] == 2
        
        # Next three rows should have 4 failed_attempts
        assert master_table.iloc[2]['failed_attempts'] == 4
        assert master_table.iloc[3]['failed_attempts'] == 4
        assert master_table.iloc[4]['failed_attempts'] == 4
        
        # All should have the same avg_runtime
        avg_runtime = 6.0
        for i in range(5):
            assert master_table.iloc[i]['avg_runtime'] == avg_runtime
    
    def test_empty_runtimes_list(self):
        """Test that empty runtimes list results in 0 avg_runtime."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{'original': 'edited'}]
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = [0]
        runtimes = []
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 1
        assert master_table.iloc[0]['avg_runtime'] == 0
    
    def test_empty_snippets_list(self):
        """Test that empty snippets list results in no rows added."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = []
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = []
        runtimes = [1.0, 2.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 0
    
    def test_snippet_with_empty_dict(self):
        """Test that snippets containing empty dictionaries add no rows."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{}]
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = [0]
        runtimes = [1.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 0
    
    def test_appends_to_existing_table(self):
        """Test that results are appended to existing table, not replacing it."""
        master_table = pd.DataFrame({
            'original_snippet': ['existing_original'],
            'edited_snippet': ['existing_edited'],
            'project': ['existing_project'],
            'optimizer': ['existing_optimizer'],
            'prompt': ['existing_prompt'],
            'prompt_type': ['existing_type'],
            'failed_attempts': [1],
            'avg_runtime': [2.0]
        })
        
        all_snippets = [{'new_original': 'new_edited'}]
        proj_name = 'new_project'
        optim_name = 'new_optimizer'
        prompt = 'new prompt'
        prompt_type = 'new_type'
        all_attempts = [3]
        runtimes = [4.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 2
        # First row should still be the existing one
        assert master_table.iloc[0]['original_snippet'] == 'existing_original'
        assert master_table.iloc[0]['project'] == 'existing_project'
        # Second row should be the new one
        assert master_table.iloc[1]['original_snippet'] == 'new_original'
        assert master_table.iloc[1]['project'] == 'new_project'
    
    def test_special_characters_in_snippets(self):
        """Test that special characters in code snippets are handled correctly."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        original_code = "def test():\n    return 'hello\\nworld'"
        edited_code = 'def test():\n    return "hello\\nworld"'
        
        all_snippets = [{original_code: edited_code}]
        proj_name = 'special_chars'
        optim_name = 'optimizer'
        prompt = 'test "quotes" and \\ backslashes'
        prompt_type = 'task'
        all_attempts = [1]
        runtimes = [1.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 1
        assert master_table.iloc[0]['original_snippet'] == original_code
        assert master_table.iloc[0]['edited_snippet'] == edited_code
        assert master_table.iloc[0]['prompt'] == 'test "quotes" and \\ backslashes'
    
    def test_zero_attempts(self):
        """Test that zero failed_attempts is handled correctly."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{'original': 'edited'}]
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = [0]
        runtimes = [1.0]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 1
        assert master_table.iloc[0]['failed_attempts'] == 0
    
    def test_large_runtime_values(self):
        """Test handling of large runtime values."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        all_snippets = [{'original': 'edited'}]
        proj_name = 'test_project'
        optim_name = 'test_optimizer'
        prompt = 'test prompt'
        prompt_type = 'task'
        all_attempts = [1]
        runtimes = [1000.5, 2000.7, 3000.3]
        
        _assemble_results(master_table, all_snippets, proj_name, optim_name,
                         prompt, prompt_type, all_attempts, runtimes)
        
        assert len(master_table) == 1
        expected_avg = (1000.5 + 2000.7 + 3000.3) / 3
        assert master_table.iloc[0]['avg_runtime'] == pytest.approx(expected_avg, rel=1e-9)
    
    def test_prompt_types(self):
        """Test different prompt_type values."""
        master_table = pd.DataFrame(columns=[
            'original_snippet', 'edited_snippet', 'project', 'optimizer',
            'prompt', 'prompt_type', 'failed_attempts', 'avg_runtime'
        ])
        
        for prompt_type in ['task', 'model', 'project']:
            all_snippets = [{'orig': 'edit'}]
            _assemble_results(master_table, all_snippets, 'proj', 'opt',
                             'prompt', prompt_type, [1], [1.0])
        
        assert len(master_table) == 3
        assert master_table.iloc[0]['prompt_type'] == 'task'
        assert master_table.iloc[1]['prompt_type'] == 'model'
        assert master_table.iloc[2]['prompt_type'] == 'project'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
