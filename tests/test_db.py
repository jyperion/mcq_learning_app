import sqlite3
import pytest
from ml_app.database.db import get_db
import json

def test_get_close_db(app):
    """Test database connection is created and closed properly"""
    with app.app_context():
        db = get_db()
        assert db is get_db()  # Should return same connection
    
    # Should raise error after context
    with pytest.raises(sqlite3.ProgrammingError) as e:
        db.execute('SELECT 1')
    
    assert 'closed' in str(e.value)

def test_init_db_command(runner, monkeypatch):
    """Test init-db command"""
    class Recorder:
        called = False
    
    def fake_init_db():
        Recorder.called = True
    
    monkeypatch.setattr('ml_app.database.db.init_db', fake_init_db)
    result = runner.invoke(args=['init-db'])
    assert 'Initialized' in result.output
    assert Recorder.called

def test_add_concept(app):
    """Test adding a concept to the database"""
    with app.app_context():
        db = get_db()
        concept_id = db.execute(
            'INSERT INTO concepts (name) VALUES (?)',
            ('Neural Networks',)
        ).lastrowid
        db.commit()
        
        concept = db.execute(
            'SELECT * FROM concepts WHERE id = ?',
            (concept_id,)
        ).fetchone()
        assert concept['name'] == 'Neural Networks'

def test_add_question(app):
    """Test adding a question to the database"""
    with app.app_context():
        db = get_db()
        # First add a concept
        concept_id = db.execute(
            'INSERT INTO concepts (name) VALUES (?)',
            ('Neural Networks',)
        ).lastrowid
        db.commit()
        
        # Then add a question
        question_id = db.execute(
            'INSERT INTO questions (question, options, correct, explanation) VALUES (?, ?, ?, ?)',
            ('What is backpropagation?',
             json.dumps({'A': 'Opt1', 'B': 'Opt2', 'C': 'Opt3', 'D': 'Opt4'}),
             'A',
             'Explanation text')
        ).lastrowid
        db.commit()
        
        # Link question to concept
        db.execute(
            'INSERT INTO concept_questions (concept_id, question_id) VALUES (?, ?)',
            (concept_id, question_id)
        )
        db.commit()
        
        # Verify question
        question = db.execute(
            'SELECT * FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        assert question['question'] == 'What is backpropagation?'
        assert json.loads(question['options'])['A'] == 'Opt1'

def test_track_user_progress(app):
    """Test tracking user progress"""
    with app.app_context():
        db = get_db()
        # Add user
        user_id = db.execute(
            'INSERT INTO users (session_id) VALUES (?)',
            ('test_session',)
        ).lastrowid
        db.commit()
        
        # Add progress
        db.execute(
            'INSERT INTO user_progress (user_id, question_id, is_correct, time_taken) VALUES (?, ?, ?, ?)',
            (user_id, 1, True, 30.5)
        )
        db.commit()
        
        # Verify progress
        progress = db.execute(
            'SELECT * FROM user_progress WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        assert progress['is_correct'] == 1
        assert progress['time_taken'] == 30.5

def test_get_user_stats(app):
    """Test retrieving user statistics"""
    with app.app_context():
        db = get_db()
        # Add user and some progress data
        user_id = db.execute(
            'INSERT INTO users (session_id) VALUES (?)',
            ('test_session',)
        ).lastrowid
        db.commit()
        
        # Add multiple progress entries
        db.execute(
            'INSERT INTO user_progress (user_id, question_id, is_correct, time_taken) VALUES (?, ?, ?, ?)',
            (user_id, 1, True, 30.5)
        )
        db.execute(
            'INSERT INTO user_progress (user_id, question_id, is_correct, time_taken) VALUES (?, ?, ?, ?)',
            (user_id, 2, False, 45.0)
        )
        db.commit()
        
        # Get statistics
        stats = db.execute('''
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                AVG(time_taken) as avg_time
            FROM user_progress
            WHERE user_id = ?
        ''', (user_id,)).fetchone()
        
        assert stats['total_questions'] == 2
        assert stats['correct_answers'] == 1
        assert 35 < stats['avg_time'] < 40  # Should be around 37.75
