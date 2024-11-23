import pytest
from ml_app.question_generation.generator import QuestionGenerator
from pathlib import Path

def test_create_prompt(app):
    """Test prompt creation"""
    with app.app_context():
        generator = QuestionGenerator()
        prompt = generator._create_prompt("Neural Networks")
        assert "Neural Networks" in prompt
        assert "multiple choice" in prompt.lower()

def test_is_valid_question_success(app):
    """Test question validation with valid data"""
    with app.app_context():
        generator = QuestionGenerator()
        question = {
            'question': 'What is backpropagation?',
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        assert generator._is_valid_question(question) == True

def test_is_valid_question_missing_fields(app):
    """Test question validation with missing fields"""
    with app.app_context():
        generator = QuestionGenerator()
        question = {
            'question': 'What is backpropagation?',
            'options': {'A': 'Opt1', 'B': 'Opt2'}  # Missing fields
        }
        assert generator._is_valid_question(question) == False

def test_is_valid_question_invalid_options(app):
    """Test question validation with invalid options"""
    with app.app_context():
        generator = QuestionGenerator()
        question = {
            'question': 'What is backpropagation?',
            'options': {'A': 'Opt1', 'E': 'Invalid'},  # Invalid option key
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        assert generator._is_valid_question(question) == False

def test_is_valid_question_invalid_correct(app):
    """Test question validation with invalid correct answer"""
    with app.app_context():
        generator = QuestionGenerator()
        question = {
            'question': 'What is backpropagation?',
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'E',  # Invalid correct answer
            'explanation': 'Some explanation'
        }
        assert generator._is_valid_question(question) == False

def test_generate_questions_from_seed(app, tmp_path):
    """Test generating questions from seed file"""
    # Create a temporary seed file
    seed_content = """# Neural Networks
Q: What is backpropagation?
A: First option
B: Second option
C: Third option
D: Fourth option
CORRECT: A
EXPLANATION: Some explanation"""

    seed_file = tmp_path / "test_seed.txt"
    seed_file.write_text(seed_content)

    with app.app_context():
        # Create generator with seed file
        generator = QuestionGenerator(seed_file=str(seed_file))  # Convert Path to string
        questions = generator.generate_questions(1, "Neural Networks")  # Add concept_id
        assert len(questions) > 0
        assert all(generator._is_valid_question(q) for q in questions)

def test_generate_questions_fallback_to_ollama(app, mock_ollama_response):
    """Test fallback to Ollama when concept not in seed"""
    with app.app_context():
        generator = QuestionGenerator(seed_file="nonexistent_file.txt")
        questions = generator.generate_questions(1, "Neural Networks")  # Add concept_id
        assert len(questions) > 0
        assert all(generator._is_valid_question(q) for q in questions)

def test_generate_questions_success(app, mock_ollama_response):
    """Test successful question generation"""
    with app.app_context():
        generator = QuestionGenerator()
        questions = generator.generate_questions(1, "Neural Networks")  # Add concept_id
        assert len(questions) > 0
        assert all(generator._is_valid_question(q) for q in questions)

def test_ollama_api_error(app, monkeypatch):
    """Test handling of Ollama API errors"""
    def mock_post(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.status_code = 500
                self.text = "Internal Server Error"
            def json(self):
                raise ValueError("Invalid JSON")
        return MockResponse()

    monkeypatch.setattr('requests.post', mock_post)
    
    with app.app_context():
        generator = QuestionGenerator()
        questions = generator.generate_questions(1, "Neural Networks")  # Add concept_id
        assert len(questions) == 0  # Should return empty list on error

def test_duplicate_prevention(app):
    """Test prevention of duplicate questions"""
    with app.app_context():
        generator = QuestionGenerator()
        
        # Create two similar questions
        question1 = {
            'question': 'What is backpropagation?',
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        
        question2 = {
            'question': 'What is back propagation?',  # Very similar
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        
        # First question should be valid
        assert generator._is_valid_question(question1) == True
        
        # Add first question to cache
        generator.question_cache.add(question1['question'])
        
        # Second question should be detected as duplicate
        assert generator._is_valid_question(question2) == False

def test_question_validation_edge_cases(app):
    """Test validation of edge cases in questions"""
    with app.app_context():
        generator = QuestionGenerator()
        
        # Test empty question
        assert generator._is_valid_question({}) == False
        
        # Test None values
        question_none = {
            'question': None,
            'options': None,
            'correct': None,
            'explanation': None
        }
        assert generator._is_valid_question(question_none) == False
        
        # Test very long question
        question_long = {
            'question': 'A' * 1000,  # Very long question
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        assert generator._is_valid_question(question_long) == False
        
        # Test HTML injection
        question_html = {
            'question': '<script>alert("test")</script>',
            'options': {'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'},
            'correct': 'A',
            'explanation': 'Some explanation'
        }
        assert generator._is_valid_question(question_html) == False
