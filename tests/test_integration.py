import pytest
import json
from ml_app.database.db import get_db
from ml_app import create_app

def test_end_to_end_concept_flow(client, mock_ollama_response):
    """Test the complete flow of adding a concept and interacting with its questions"""
    # Step 1: Add a new concept
    response = client.post('/api/concepts',
                          json={'name': 'Neural Networks'})
    assert response.status_code == 200
    data = response.json
    assert data['name'] == 'Neural Networks'
    assert 'id' in data
    concept_id = data['id']
    initial_questions = data['questions']
    assert len(initial_questions) == 3
    
    # Step 2: Get questions for the concept
    response = client.get(f'/api/concepts/{concept_id}/questions')
    assert response.status_code == 200
    questions = response.json
    assert len(questions) == 3
    
    # Verify question structure
    for q in questions:
        assert 'id' in q
        assert 'question' in q
        assert 'options' in q
        assert 'correct' in q
        assert 'explanation' in q
        assert isinstance(q['options'], dict)
        assert all(opt in q['options'] for opt in ['A', 'B', 'C', 'D'])
        assert q['correct'] in ['A', 'B', 'C', 'D']
    
    # Step 3: Submit answers and track progress
    session_id = 'test_session_1'
    headers = {'X-Session-ID': session_id}
    
    # Submit multiple answers to build up statistics
    for i, question in enumerate(questions):
        response = client.post('/api/questions/submit',
                             headers=headers,
                             json={
                                 'question_id': question['id'],
                                 'selected_option': question['correct'] if i % 2 == 0 else 'A',
                                 'time_taken': 30.5
                             })
        assert response.status_code == 200
        result = response.json
        assert 'is_correct' in result
        assert 'correct' in result
        assert 'explanation' in result
        assert result['correct'] == question['correct']
    
    # Step 4: Check user progress
    response = client.get('/api/user/progress', headers=headers)
    assert response.status_code == 200
    progress = response.json
    assert progress['total_questions'] == 3
    assert progress['correct_answers'] == 2  # We got 2 correct (i % 2 == 0)
    assert isinstance(progress['average_time'], float)
    
    # Step 5: Check concept-specific stats
    response = client.get(f'/api/concepts/{concept_id}/stats', headers=headers)
    assert response.status_code == 200
    stats = response.json
    assert stats['total_questions'] == 3
    assert stats['correct_answers'] == 2
    assert isinstance(stats['average_time'], float)

def test_multiple_users_isolation(client, mock_ollama_response):
    """Test that multiple users' progress is tracked separately"""
    # Add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Deep Learning'})
    assert response.status_code == 200
    concept_id = response.json['id']
    questions = response.json['questions']
    
    # Create two users
    users = ['user1', 'user2']
    for user in users:
        headers = {'X-Session-ID': user}
        # Each user answers all questions
        for question in questions:
            response = client.post('/api/questions/submit',
                                 headers=headers,
                                 json={
                                     'question_id': question['id'],
                                     'selected_option': question['correct'],
                                     'time_taken': 25.0
                                 })
            assert response.status_code == 200
    
    # Verify each user's progress is separate
    for user in users:
        headers = {'X-Session-ID': user}
        response = client.get('/api/user/progress', headers=headers)
        assert response.status_code == 200
        progress = response.json
        assert progress['total_questions'] == 3
        assert progress['correct_answers'] == 3  # All correct
        
        # Check concept stats
        response = client.get(f'/api/concepts/{concept_id}/stats', headers=headers)
        assert response.status_code == 200
        stats = response.json
        assert stats['total_questions'] == 3
        assert stats['correct_answers'] == 3

def test_error_handling_flow(client):
    """Test error handling in various scenarios"""
    # Test invalid concept ID
    response = client.get('/api/concepts/999/questions')
    assert response.status_code == 404
    assert 'error' in response.json
    
    # Test invalid question submission
    headers = {'X-Session-ID': 'error_test_user'}
    response = client.post('/api/questions/submit',
                          headers=headers,
                          json={
                              'question_id': 999,
                              'selected_option': 'A',
                              'time_taken': 30.0
                          })
    assert response.status_code == 404
    assert 'error' in response.json
    
    # Test missing required fields
    response = client.post('/api/questions/submit',
                          headers=headers,
                          json={
                              'selected_option': 'A'
                          })
    assert response.status_code == 400
    assert 'error' in response.json
    
    # Test invalid content type
    response = client.post('/api/concepts',
                          data='not json')
    assert response.status_code == 400
    assert 'error' in response.json

def test_question_validation_flow(client, mock_ollama_response):
    """Test that questions meet all validation requirements"""
    # Add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Machine Learning'})
    assert response.status_code == 200
    questions = response.json['questions']
    
    # Verify each question meets requirements
    for question in questions:
        # Check question structure
        assert len(question['question']) <= 500
        assert '<' not in question['question']  # No HTML
        assert '>' not in question['question']
        
        # Check options
        assert isinstance(question['options'], dict)
        assert all(opt in question['options'] for opt in ['A', 'B', 'C', 'D'])
        assert all(question['options'][opt] for opt in ['A', 'B', 'C', 'D'])
        
        # Check correct answer
        assert question['correct'] in ['A', 'B', 'C', 'D']
        
        # Check explanation
        assert question['explanation']

def test_concurrent_sessions(client, mock_ollama_response):
    """Test handling of concurrent user sessions"""
    # Create multiple session IDs
    session_ids = [f'concurrent_user_{i}' for i in range(3)]
    
    # Add a concept
    response = client.post('/api/concepts',
                          json={'name': 'Data Science'})
    assert response.status_code == 200
    concept_id = response.json['id']
    questions = response.json['questions']
    
    # Simulate concurrent users
    for session_id in session_ids:
        headers = {'X-Session-ID': session_id}
        
        # Each user answers questions
        for question in questions:
            response = client.post('/api/questions/submit',
                                 headers=headers,
                                 json={
                                     'question_id': question['id'],
                                     'selected_option': 'A',
                                     'time_taken': 20.0
                                 })
            assert response.status_code == 200
    
    # Verify each session's data is intact
    for session_id in session_ids:
        headers = {'X-Session-ID': session_id}
        
        # Check progress
        response = client.get('/api/user/progress', headers=headers)
        assert response.status_code == 200
        progress = response.json
        assert progress['total_questions'] == 3
        
        # Check concept stats
        response = client.get(f'/api/concepts/{concept_id}/stats', headers=headers)
        assert response.status_code == 200
        stats = response.json
        assert stats['total_questions'] == 3