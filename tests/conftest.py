import os
import tempfile
import pytest
from ml_app import create_app
from ml_app.database.db import get_db, init_db

@pytest.fixture
def app():
    """Create and configure a test Flask app instance"""
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'DATABASE': db_path,
        'OLLAMA_URL': 'http://localhost:11434'
    })
    
    # Initialize the database
    with app.app_context():
        init_db()
    
    yield app
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Test client for making requests"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Test CLI runner"""
    return app.test_cli_runner()

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self.json_data

@pytest.fixture
def mock_ollama_response(monkeypatch):
    """Mock successful Ollama API response"""
    questions = [
        {
            'response': '''{
                "question": "What is backpropagation?",
                "options": {
                    "A": "A method to initialize neural network weights",
                    "B": "An algorithm to compute gradients in neural networks",
                    "C": "A type of neural network architecture",
                    "D": "A method to normalize input data"
                },
                "correct": "B",
                "explanation": "Backpropagation is an algorithm used to calculate gradients..."
            }'''
        },
        {
            'response': '''{
                "question": "What is a neural network activation function?",
                "options": {
                    "A": "A function that determines the network architecture",
                    "B": "A function that initializes weights",
                    "C": "A function that introduces non-linearity",
                    "D": "A function that normalizes inputs"
                },
                "correct": "C",
                "explanation": "Activation functions introduce non-linearity..."
            }'''
        },
        {
            'response': '''{
                "question": "What is the purpose of dropout in neural networks?",
                "options": {
                    "A": "To speed up training",
                    "B": "To reduce memory usage",
                    "C": "To prevent overfitting",
                    "D": "To initialize weights"
                },
                "correct": "C",
                "explanation": "Dropout helps prevent overfitting by randomly deactivating neurons..."
            }'''
        }
    ]
    
    call_count = 0
    def mock_post(*args, **kwargs):
        nonlocal call_count
        response = questions[call_count % len(questions)]
        call_count += 1
        return MockResponse(response)
    
    monkeypatch.setattr("requests.post", mock_post)
    return mock_post

@pytest.fixture
def auth_headers():
    """Generate test authentication headers"""
    return {'X-Session-ID': 'test_session_123'}

@pytest.fixture
def test_concept(client, mock_ollama_response):
    """Create a test concept with questions"""
    response = client.post('/api/concepts',
                          json={'name': 'Test Concept'})
    assert response.status_code == 200
    return response.json

@pytest.fixture
def test_user_progress(client, test_concept, auth_headers):
    """Create test user with some progress"""
    # Submit answers for all questions
    for question in test_concept['questions']:
        client.post('/api/questions/submit',
                   headers=auth_headers,
                   json={
                       'question_id': question['id'],
                       'selected_option': question['correct'],
                       'time_taken': 25.0
                   })
    return auth_headers['X-Session-ID']

@pytest.fixture
def mock_ollama_error_response(monkeypatch):
    """Mock failed Ollama API response"""
    def mock_post(*args, **kwargs):
        return MockResponse({'error': 'API Error'}, status_code=500)
    
    monkeypatch.setattr("requests.post", mock_post)
    return mock_post
