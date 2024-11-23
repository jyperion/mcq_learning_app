"""Test seed file parser"""
import pytest
from ml_app.question_generation.seed_parser import parse_seed_file

def test_parse_seed_file(tmp_path):
    """Test parsing a seed file with multiple concepts"""
    # Create a temporary seed file
    seed_content = """# Neural Networks
Q: What is backpropagation?
A: First option
B: Second option
C: Third option
D: Fourth option
CORRECT: A
EXPLANATION: Some explanation

# Deep Learning
Q: What is a test question?
A: Option A
B: Option B
C: Option C
D: Option D
CORRECT: B
EXPLANATION: Test explanation"""
    
    seed_file = tmp_path / "test_seed.txt"
    seed_file.write_text(seed_content)
    
    # Parse the file
    questions = parse_seed_file(seed_file)
    
    # Check structure
    assert len(questions) == 2
    assert "Neural Networks" in questions
    assert "Deep Learning" in questions
    
    # Check first question
    nn_questions = questions["Neural Networks"]
    assert len(nn_questions) == 1
    q = nn_questions[0]
    assert q["question"] == "What is backpropagation?"
    assert len(q["options"]) == 4
    assert q["correct"] == "A"
    assert q["explanation"] == "Some explanation"
    
    # Check second question
    dl_questions = questions["Deep Learning"]
    assert len(dl_questions) == 1
    q = dl_questions[0]
    assert q["question"] == "What is a test question?"
    assert len(q["options"]) == 4
    assert q["correct"] == "B"
    assert q["explanation"] == "Test explanation"
