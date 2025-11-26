import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOptimizerGenerationFunctions:
    """Test suite for _gen_functions in each Optimizer class."""
    
    @pytest.fixture
    def api_keys(self):
        """Load API keys from API_KEYS.json."""
        api_keys_path = Path(__file__).parent.parent / 'API_KEYS.json'
        with open(api_keys_path, 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_prompt(self):
        """Sample optimization prompt."""
        return "Optimize this code for better runtime performance"
    
    @pytest.fixture
    def sample_snippet(self):
        """Sample code snippet to optimize."""
        return "for i in range(len(arr)):\n    if arr[i] > 5:\n        result.append(arr[i])"
    
    @pytest.fixture
    def sample_scope(self):
        """Sample enclosing scope."""
        return "def process_data(arr):\n    result = []\n    # snippet goes here\n    return result"
    
    @pytest.fixture
    def expected_code_output(self):
        """Expected optimized code output."""
        return "result = [x for x in arr if x > 5]"
    
    # ===== GeminiOptimizer Tests =====
    
    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_gemini_optimizer_gen_function(self, mock_configure, mock_model_class, 
                                          api_keys, sample_prompt, sample_snippet, 
                                          sample_scope, expected_code_output):
        """Test GeminiOptimizer._gemini_gen function."""
        from pipeline.optimizers import GeminiOptimizer
        
        # Create mock response
        mock_response = Mock()
        mock_response.text = json.dumps({"code": expected_code_output})
        
        # Setup mock model instance
        mock_model_instance = Mock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        # Create optimizer
        optimizer = GeminiOptimizer()
        
        # Call the generation function
        result = optimizer._gemini_gen(sample_prompt, sample_snippet, sample_scope)
        
        # Assertions
        assert result == expected_code_output
        mock_model_instance.generate_content.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_model_instance.generate_content.call_args
        assert 'contents' in call_args.kwargs
        assert sample_prompt in call_args.kwargs['contents']
        assert sample_snippet in call_args.kwargs['contents']
        assert sample_scope in call_args.kwargs['contents']
        
        # Verify generation config
        assert 'generation_config' in call_args.kwargs
        gen_config = call_args.kwargs['generation_config']
        assert gen_config.response_mime_type == "application/json"
    
    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_gemini_optimizer_gen_with_multiline_code(self, mock_configure, mock_model_class, 
                                                       api_keys, sample_prompt, sample_scope):
        """Test GeminiOptimizer._gemini_gen with multiline code output."""
        from pipeline.optimizers import GeminiOptimizer
        
        multiline_code = "def optimized_func(arr):\n    return [x for x in arr if x > 5]"
        
        mock_response = Mock()
        mock_response.text = json.dumps({"code": multiline_code})
        
        mock_model_instance = Mock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        optimizer = GeminiOptimizer()
        result = optimizer._gemini_gen(sample_prompt, "snippet", sample_scope)
        
        assert result == multiline_code
        assert "\n" in result
    
    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_gemini_optimizer_name_attribute(self, mock_configure, mock_model_class, api_keys):
        """Test that GeminiOptimizer has correct name attribute."""
        from pipeline.optimizers import GeminiOptimizer
        
        mock_model_instance = Mock()
        mock_model_class.return_value = mock_model_instance
        
        optimizer = GeminiOptimizer()
        assert optimizer.name == "25"
        assert hasattr(optimizer, 'generate')
    
    # ===== OpenOptimizer Tests =====
    
    @patch('openai.OpenAI')
    def test_open_optimizer_gen_function(self, mock_openai_class, api_keys, 
                                        sample_prompt, sample_snippet, 
                                        sample_scope, expected_code_output):
        """Test OpenOptimizer._openai_gen function."""
        from pipeline.optimizers import OpenOptimizer
        
        # Create mock completion response
        mock_message = Mock()
        mock_message.content = json.dumps({"code": expected_code_output})
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        
        # Setup mock client
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        # Create optimizer
        optimizer = OpenOptimizer()
        
        # Call the generation function
        result = optimizer._openai_gen(sample_prompt, sample_snippet, sample_scope)
        
        # Assertions
        assert result == expected_code_output
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs['model'] == "gpt-4o"
        assert 'max_tokens' in call_args.kwargs
        assert 'response_format' in call_args.kwargs
        assert call_args.kwargs['response_format']['type'] == "json_schema"
        
        # Check message content
        messages = call_args.kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert sample_prompt in messages[0]['content']
        assert sample_snippet in messages[0]['content']
        assert sample_scope in messages[0]['content']
    
    @patch('openai.OpenAI')
    def test_open_optimizer_gen_with_special_characters(self, mock_openai_class, 
                                                        api_keys, sample_prompt, sample_scope):
        """Test OpenOptimizer._openai_gen with special characters in code."""
        from pipeline.optimizers import OpenOptimizer
        
        special_code = 'result = "hello\\nworld"\nprint(\'test\')'
        
        mock_message = Mock()
        mock_message.content = json.dumps({"code": special_code})
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        optimizer = OpenOptimizer()
        result = optimizer._openai_gen(sample_prompt, "snippet", sample_scope)
        
        assert result == special_code
        assert "\\" in result
        assert "'" in result
    
    @patch('openai.OpenAI')
    def test_open_optimizer_name_attribute(self, mock_openai_class, api_keys):
        """Test that OpenOptimizer has correct name attribute."""
        from pipeline.optimizers import OpenOptimizer
        
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        optimizer = OpenOptimizer()
        assert optimizer.name == "4o"
        assert hasattr(optimizer, 'generate')
    
    # ===== AnthroOptimizer Tests =====
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_gen_function(self, mock_anthropic_class, api_keys, 
                                          sample_prompt, sample_snippet, 
                                          sample_scope, expected_code_output):
        """Test AnthroOptimizer._anthropic_gen function."""
        from pipeline.optimizers import AnthroOptimizer
        
        # Create mock tool use block
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "code_output"
        mock_tool_block.input = {"code": expected_code_output}
        
        # Create mock response
        mock_response = Mock()
        mock_response.content = [mock_tool_block]
        
        # Setup mock client
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        # Create optimizer
        optimizer = AnthroOptimizer()
        
        # Call the generation function
        result = optimizer._anthropic_gen(sample_prompt, sample_snippet, sample_scope)
        
        # Assertions
        assert result == expected_code_output
        mock_client.messages.create.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs['model'] == "claude-sonnet-4-20250514"
        assert 'max_tokens' in call_args.kwargs
        assert 'tools' in call_args.kwargs
        assert 'tool_choice' in call_args.kwargs
        
        # Verify tool configuration
        tools = call_args.kwargs['tools']
        assert len(tools) == 1
        assert tools[0]['name'] == "code_output"
        assert call_args.kwargs['tool_choice']['name'] == "code_output"
        
        # Check messages
        messages = call_args.kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert sample_prompt in messages[0]['content']
        assert sample_snippet in messages[0]['content']
        assert sample_scope in messages[0]['content']
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_gen_with_complex_code(self, mock_anthropic_class, 
                                                    api_keys, sample_prompt, sample_scope):
        """Test AnthroOptimizer._anthropic_gen with complex multiline code."""
        from pipeline.optimizers import AnthroOptimizer
        
        complex_code = """def optimized_function(data):
    # Process data efficiently
    result = []
    for item in data:
        if item > threshold:
            result.append(item)
    return result"""
        
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "code_output"
        mock_tool_block.input = {"code": complex_code}
        
        mock_response = Mock()
        mock_response.content = [mock_tool_block]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        optimizer = AnthroOptimizer()
        result = optimizer._anthropic_gen(sample_prompt, "snippet", sample_scope)
        
        assert result == complex_code
        assert "def optimized_function" in result
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_no_tool_use_raises_error(self, mock_anthropic_class, 
                                                       api_keys, sample_prompt, 
                                                       sample_snippet, sample_scope):
        """Test that AnthroOptimizer raises error when no tool_use block is found."""
        from pipeline.optimizers import AnthroOptimizer
        
        # Create mock response without tool_use
        mock_text_block = Mock()
        mock_text_block.type = "text"
        mock_text_block.text = "Some text response"
        
        mock_response = Mock()
        mock_response.content = [mock_text_block]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        optimizer = AnthroOptimizer()
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No code_output tool use found in response"):
            optimizer._anthropic_gen(sample_prompt, sample_snippet, sample_scope)
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_wrong_tool_name_raises_error(self, mock_anthropic_class, 
                                                           api_keys, sample_prompt, 
                                                           sample_snippet, sample_scope):
        """Test that AnthroOptimizer raises error when wrong tool name is used."""
        from pipeline.optimizers import AnthroOptimizer
        
        # Create mock tool use block with wrong name
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "wrong_tool"
        mock_tool_block.input = {"code": "some code"}
        
        mock_response = Mock()
        mock_response.content = [mock_tool_block]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        optimizer = AnthroOptimizer()
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No code_output tool use found in response"):
            optimizer._anthropic_gen(sample_prompt, sample_snippet, sample_scope)
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_name_attribute(self, mock_anthropic_class, api_keys):
        """Test that AnthroOptimizer has correct name attribute."""
        from pipeline.optimizers import AnthroOptimizer
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        optimizer = AnthroOptimizer()
        assert optimizer.name == "40"
        assert hasattr(optimizer, 'generate')
    
    # ===== Test assemble_prompt helper function =====
    
    def test_assemble_prompt_function(self):
        """Test the assemble_prompt helper function."""
        from pipeline.optimizers import assemble_prompt
        
        prompt = "Optimize this code"
        snippet = "for i in range(10): print(i)"
        scope = "def main(): pass"
        
        result = assemble_prompt(prompt, snippet, scope)
        
        assert prompt in result
        assert snippet in result
        assert scope in result
        assert "Object to be optimized:" in result
        assert "Enclosing scope of object:" in result
    
    def test_assemble_prompt_with_empty_strings(self):
        """Test assemble_prompt with empty strings."""
        from pipeline.optimizers import assemble_prompt
        
        result = assemble_prompt("", "", "")
        
        assert "Object to be optimized:" in result
        assert "Enclosing scope of object:" in result
    
    def test_assemble_prompt_with_multiline_inputs(self):
        """Test assemble_prompt with multiline inputs."""
        from pipeline.optimizers import assemble_prompt
        
        prompt = "Line 1\nLine 2\nLine 3"
        snippet = "def func():\n    pass"
        scope = "class MyClass:\n    pass"
        
        result = assemble_prompt(prompt, snippet, scope)
        
        assert prompt in result
        assert snippet in result
        assert scope in result
        assert result.count("\n") >= 6  # Multiple newlines from inputs
    
    # ===== Integration-style tests for generate attribute =====
    
    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_gemini_optimizer_generate_attribute_callable(self, mock_configure, 
                                                          mock_model_class, api_keys):
        """Test that GeminiOptimizer.generate is callable and points to _gemini_gen."""
        from pipeline.optimizers import GeminiOptimizer
        
        mock_response = Mock()
        mock_response.text = json.dumps({"code": "test"})
        
        mock_model_instance = Mock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        optimizer = GeminiOptimizer()
        
        assert callable(optimizer.generate)
        result = optimizer.generate("prompt", "snippet", "scope")
        assert result == "test"
    
    @patch('openai.OpenAI')
    def test_open_optimizer_generate_attribute_callable(self, mock_openai_class, api_keys):
        """Test that OpenOptimizer.generate is callable and points to _openai_gen."""
        from pipeline.optimizers import OpenOptimizer
        
        mock_message = Mock()
        mock_message.content = json.dumps({"code": "test"})
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_completion = Mock()
        mock_completion.choices = [mock_choice]
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        
        optimizer = OpenOptimizer()
        
        assert callable(optimizer.generate)
        result = optimizer.generate("prompt", "snippet", "scope")
        assert result == "test"
    
    @patch('anthropic.Anthropic')
    def test_anthro_optimizer_generate_attribute_callable(self, mock_anthropic_class, api_keys):
        """Test that AnthroOptimizer.generate is callable and points to _anthropic_gen."""
        from pipeline.optimizers import AnthroOptimizer
        
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "code_output"
        mock_tool_block.input = {"code": "test"}
        
        mock_response = Mock()
        mock_response.content = [mock_tool_block]
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client
        
        optimizer = AnthroOptimizer()
        
        assert callable(optimizer.generate)
        result = optimizer.generate("prompt", "snippet", "scope")
        assert result == "test"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
