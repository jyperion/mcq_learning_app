import json
import pytest
from ml_app.database.db import get_db

def test_list_concepts_empty(client):
    """Test listing concepts when empty"""
    response = client.get('/api/concepts')
    assert response.status_code == 200
    assert response.json == []

def test_add_concept(client, mock_ollama_response):
    """Test adding a new concept"""
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    assert response.status_code == 200
    data = response.json
    assert data['name'] == 'Neural Networks'
    assert 'id' in data
    assert len(data['questions']) == 3

def test_add_concept_invalid(client):
    """Test adding concept with invalid data"""
    # Missing name
    response = client.post('/api/concepts', json={})
    assert response.status_code == 400
    assert 'error' in response.json
    
    # Empty name
    response = client.post('/api/concepts', json={'name': ''})
    assert response.status_code == 400
    assert 'error' in response.json
    
    # Invalid content type
    response = client.post('/api/concepts', data='not json')
    assert response.status_code == 400
    assert 'error' in response.json

def test_get_concept_details(client, mock_ollama_response):
    """Test getting concept details"""
    # First add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    concept_id = response.json['id']
    
    # Get concept details
    response = client.get(f'/api/concepts/{concept_id}')
    assert response.status_code == 200
    data = response.json
    assert data['id'] == concept_id
    assert data['name'] == 'Neural Networks'
    assert 'description' in data
    assert 'stats' in data
    assert 'total_questions' in data['stats']
    assert 'avg_score' in data['stats']
    assert 'avg_time' in data['stats']
    assert 'recent_questions' in data
    assert isinstance(data['recent_questions'], list)

def test_get_concept_questions(client, mock_ollama_response):
    """Test getting questions for a concept"""
    # First add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    concept_id = response.json['id']
    
    # Get questions
    response = client.get(f'/api/concepts/{concept_id}/questions')
    assert response.status_code == 200
    questions = response.json
    assert len(questions) > 0
    
    # Check question format
    question = questions[0]
    assert 'id' in question
    assert 'text' in question
    assert 'options' in question
    assert isinstance(question['options'], list)
    assert 'difficulty' in question
    assert 'attempts' in question
    assert 'success_rate' in question

def test_get_concept_nonexistent(client):
    """Test getting details for nonexistent concept"""
    response = client.get('/api/concepts/999')
    assert response.status_code == 404
    assert 'error' in response.json

def test_submit_answer(client, mock_ollama_response):
    """Test submitting an answer"""
    # First add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    concept_id = response.json['id']
    
    # Get a question
    response = client.get(f'/api/concepts/{concept_id}/questions')
    question = response.json[0]
    
    # Create a session
    response = client.post('/api/sessions', json={'user_name': 'Test User'})
    session_id = response.json['session_id']
    
    # Submit an answer
    response = client.post(f'/api/questions/{question["id"]}/submit',
                          headers={'X-Session-ID': session_id},
                          json={'answer': 0, 'time_taken': 30})
    assert response.status_code == 200
    data = response.json
    assert 'correct' in data
    assert isinstance(data['correct'], bool)
    assert 'explanation' in data
    assert 'correct_answer' in data
    assert 'correct_answer_text' in data
    
    # Verify it was recorded in the database
    db = get_db()
    record = db.execute(
        'SELECT * FROM user_answers WHERE question_id = ?',
        (question['id'],)
    ).fetchone()
    assert record is not None
    assert record['answer'] == 0
    assert record['time_taken'] == 30
    assert record['session_id'] == session_id

def test_submit_answer_invalid(client):
    """Test submitting invalid answers"""
    # Missing session ID
    response = client.post('/api/questions/1/submit',
                          json={'answer': 0, 'time_taken': 30})
    assert response.status_code == 400
    assert 'error' in response.json
    
    # Invalid question ID
    response = client.post('/api/questions/999/submit',
                          headers={'X-Session-ID': 'test-session'},
                          json={'answer': 0, 'time_taken': 30})
    assert response.status_code == 404
    assert 'error' in response.json
    
    # Missing answer
    response = client.post('/api/questions/1/submit',
                          headers={'X-Session-ID': 'test-session'},
                          json={'time_taken': 30})
    assert response.status_code == 400
    assert 'error' in response.json
    
    # Invalid answer type
    response = client.post('/api/questions/1/submit',
                          headers={'X-Session-ID': 'test-session'},
                          json={'answer': 'not a number', 'time_taken': 30})
    assert response.status_code == 500
    assert 'error' in response.json

def test_get_user_progress(client, mock_ollama_response):
    """Test getting user progress"""
    # First add a concept and submit some answers
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    concept_id = response.json['id']
    
    # Get questions
    response = client.get(f'/api/concepts/{concept_id}/questions')
    question_id = response.json[0]['id']
    
    # Submit answer
    client.post('/api/questions/submit',
                json={
                    'question_id': question_id,
                    'selected_option': 'A',
                    'time_taken': 30.5
                })
    
    # Get progress
    response = client.get('/api/user/progress')
    assert response.status_code == 200
    data = response.json
    assert 'total_questions' in data
    assert 'correct_answers' in data
    assert 'average_time' in data
    assert data['total_questions'] == 1

def test_get_concept_stats(client, mock_ollama_response):
    """Test getting concept-wise statistics"""
    # First add a concept and submit some answers
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    concept_id = response.json['id']
    
    # Get questions and submit answers
    response = client.get(f'/api/concepts/{concept_id}/questions')
    for question in response.json[:2]:
        client.post('/api/questions/submit',
                   json={
                       'question_id': question['id'],
                       'selected_option': 'A',
                       'time_taken': 30.5
                   })
    
    # Get concept stats
    response = client.get(f'/api/concepts/{concept_id}/stats')
    assert response.status_code == 200
    data = response.json
    assert 'total_questions' in data
    assert 'correct_answers' in data
    assert 'average_time' in data
    assert data['total_questions'] == 2

def test_start_session(client):
    """Test starting a new user session."""
    response = client.post('/api/session/start')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'session_id' in data
    assert 'user_id' in data
    assert isinstance(data['session_id'], str)
    assert isinstance(data['user_id'], int)
    assert len(data['session_id']) > 0
    assert data['user_id'] > 0
    
    # Test that session_id is unique
    response2 = client.post('/api/session/start')
    data2 = response2.get_json()
    assert data2['session_id'] != data['session_id']
