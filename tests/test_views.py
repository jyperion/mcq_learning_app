import pytest
from flask import url_for

def test_index_page(client):
    """Test the main practice page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'ML Interview Practice' in response.data
    assert b'Question' in response.data

def test_stats_page(client):
    """Test the statistics page loads correctly"""
    response = client.get('/stats')
    assert response.status_code == 200
    assert b'Your Performance Statistics' in response.data
    assert b'Total Questions' in response.data
    assert b'Average Score' in response.data

def test_concepts_page(client):
    """Test the concepts page loads correctly"""
    response = client.get('/concepts')
    assert response.status_code == 200
    assert b'Machine Learning Concepts' in response.data
    assert b'Search concepts' in response.data

def test_static_files(client):
    """Test that static files are served correctly"""
    # Test JavaScript files
    js_files = ['practice.js', 'stats.js', 'concepts.js']
    for js_file in js_files:
        response = client.get(f'/static/js/{js_file}')
        assert response.status_code == 200
        assert response.content_type == 'application/javascript'

def test_question_api(client, mock_ollama_response):
    """Test question-related API endpoints"""
    # Test getting a random question
    response = client.get('/api/questions/random')
    assert response.status_code == 200
    data = response.get_json()
    assert 'id' in data
    assert 'text' in data
    assert 'options' in data

    # Test checking an answer
    question_id = data['id']
    response = client.post(f'/api/questions/{question_id}/check', 
                         json={'answer': 0})
    assert response.status_code == 200
    result = response.get_json()
    assert 'correct' in result
    assert 'explanation' in result

    # Test rechecking a question
    response = client.post(f'/api/questions/{question_id}/recheck')
    assert response.status_code == 200
    result = response.get_json()
    assert 'newAnswer' in result

def test_stats_api(client, test_user_progress):
    """Test statistics API endpoints"""
    # Test overview stats
    response = client.get('/api/stats/overview')
    assert response.status_code == 200
    data = response.get_json()
    assert 'totalQuestions' in data
    assert 'averageScore' in data
    assert 'totalTime' in data

    # Test concept performance stats
    response = client.get('/api/stats/concepts')
    assert response.status_code == 200
    data = response.get_json()
    assert 'concepts' in data
    assert 'scores' in data

    # Test progress over time
    response = client.get('/api/stats/progress')
    assert response.status_code == 200
    data = response.get_json()
    assert 'dates' in data
    assert 'scores' in data

    # Test recent activity
    response = client.get('/api/stats/activity')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert 'date' in data[0]
        assert 'concept' in data[0]
        assert 'score' in data[0]
        assert 'timeSpent' in data[0]

def test_concepts_api(client, test_concept):
    """Test concept-related API endpoints"""
    # Test getting all concepts
    response = client.get('/api/concepts')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Test getting concept details
    concept_id = data[0]['id']
    response = client.get(f'/api/concepts/{concept_id}')
    assert response.status_code == 200
    concept = response.get_json()
    assert 'name' in concept
    assert 'description' in concept
    assert 'topics' in concept
    assert 'difficulty' in concept
    assert 'prerequisites' in concept

def test_error_handling(client, mock_ollama_error_response):
    """Test error handling in API endpoints"""
    # Test invalid question ID
    response = client.get('/api/questions/999999')
    assert response.status_code == 404

    # Test invalid answer submission
    response = client.post('/api/questions/1/check', json={})
    assert response.status_code == 400

    # Test Ollama API error
    response = client.post('/api/questions/1/recheck')
    assert response.status_code == 500
    data = response.get_json()
    assert 'error' in data
