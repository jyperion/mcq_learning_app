from flask import Blueprint, jsonify, request, current_app
from ml_app.database.db import get_db
import json
import uuid
from datetime import datetime

bp = Blueprint('practice', __name__, url_prefix='/api')

@bp.route('/practice/start', methods=['POST'])
def start_session():
    data = request.get_json()
    user_name = data.get('userName', 'Anonymous')
    
    session_id = str(uuid.uuid4())
    db = get_db()
    
    db.execute(
        'INSERT INTO sessions (id, user_name) VALUES (?, ?)',
        (session_id, user_name)
    )
    db.commit()
    
    return jsonify({'sessionId': session_id})

@bp.route('/practice/question', methods=['GET'])
def get_question():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
    
    db = get_db()
    
    # First, check if all questions have been answered
    total_questions = db.execute('SELECT COUNT(*) as count FROM questions').fetchone()['count']
    answered_questions = db.execute(
        'SELECT COUNT(DISTINCT question_id) as count FROM user_answers WHERE session_id = ?',
        (session_id,)
    ).fetchone()['count']
    
    if answered_questions >= total_questions:
        return jsonify({
            'error': 'No more questions available',
            'message': 'You have answered all available questions!'
        }), 404
    
    # Get a random question that hasn't been answered in this session
    question = db.execute('''
        SELECT q.*, c.name as concept_name
        FROM questions q
        LEFT JOIN concepts c ON q.concept_id = c.id
        WHERE q.id NOT IN (
            SELECT DISTINCT question_id 
            FROM user_answers 
            WHERE session_id = ?
        )
        ORDER BY RANDOM()
        LIMIT 1
    ''', (session_id,)).fetchone()
    
    if not question:
        return jsonify({'error': 'No more questions available'}), 404
    
    current_app.logger.info(f"Retrieved question {question['id']} for session {session_id}")
    
    return jsonify({
        'id': question['id'],
        'text': question['text'],
        'options': json.loads(question['options']),
        'difficulty': question['difficulty'],
        'concept': question['concept_name']
    })

@bp.route('/practice/answer', methods=['POST'])
def submit_answer():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
    
    data = request.get_json()
    question_id = data.get('questionId')
    answer = data.get('answer')
    time_taken = data.get('timeTaken', 0)
    
    if not question_id or not answer:
        return jsonify({'error': 'Question ID and answer are required'}), 400
    
    db = get_db()
    
    # Check if this question has already been answered in this session
    existing_answer = db.execute(
        'SELECT id FROM user_answers WHERE session_id = ? AND question_id = ?',
        (session_id, question_id)
    ).fetchone()
    
    if existing_answer:
        return jsonify({'error': 'Question already answered in this session'}), 400
    
    # Get correct answer
    question = db.execute(
        'SELECT correct_answer, explanation FROM questions WHERE id = ?',
        (question_id,)
    ).fetchone()
    
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    is_correct = answer == question['correct_answer']
    
    try:
        # Record answer
        db.execute('''
            INSERT INTO user_answers (session_id, question_id, answer, is_correct, time_taken)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, question_id, answer, is_correct, time_taken))
        db.commit()
        
        current_app.logger.info(f"Recorded answer for question {question_id} in session {session_id}")
        
        return jsonify({
            'correct': is_correct,
            'correctAnswer': question['correct_answer'],
            'explanation': question['explanation']
        })
    except Exception as e:
        current_app.logger.error(f"Error recording answer: {str(e)}")
        return jsonify({'error': 'Failed to record answer'}), 500

@bp.route('/practice/progress', methods=['GET'])
def get_progress():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
    
    db = get_db()
    
    # Get overall stats
    overall = db.execute('''
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
            ROUND(AVG(CASE WHEN is_correct THEN 100 ELSE 0 END), 2) as accuracy,
            ROUND(AVG(time_taken), 2) as average_time
        FROM user_answers
        WHERE session_id = ?
    ''', (session_id,)).fetchone()
    
    # Get concept mastery
    concepts = db.execute('''
        SELECT 
            c.name as concept,
            COUNT(ua.id) as attempted,
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct,
            ROUND(AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END), 2) as accuracy
        FROM concepts c
        LEFT JOIN questions q ON q.concept_id = c.id
        LEFT JOIN user_answers ua ON ua.question_id = q.id AND ua.session_id = ?
        GROUP BY c.id, c.name
        HAVING attempted > 0
        ORDER BY c.name
    ''', (session_id,)).fetchall()
    
    # Get difficulty breakdown
    difficulty = db.execute('''
        SELECT 
            q.difficulty,
            COUNT(ua.id) as attempted,
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct,
            ROUND(AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END), 2) as accuracy
        FROM questions q
        LEFT JOIN user_answers ua ON ua.question_id = q.id AND ua.session_id = ?
        GROUP BY q.difficulty
        HAVING attempted > 0
        ORDER BY q.difficulty
    ''', (session_id,)).fetchall()
    
    # Get session history
    history = db.execute('''
        SELECT 
            s.id as session_id,
            COUNT(ua.id) as total_questions,
            SUM(CASE WHEN ua.is_correct THEN 1 ELSE 0 END) as correct_answers,
            ROUND(AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END), 2) as accuracy
        FROM sessions s
        LEFT JOIN user_answers ua ON ua.session_id = s.id
        GROUP BY s.id
        HAVING total_questions > 0
        ORDER BY s.start_time DESC
        LIMIT 10
    ''').fetchall()
    
    return jsonify({
        'overall': {
            'totalQuestions': overall['total_questions'],
            'correctAnswers': overall['correct_answers'],
            'accuracy': overall['accuracy'] or 0,
            'averageTime': overall['average_time'] or 0
        },
        'byConcept': [{
            'concept': row['concept'],
            'attempted': row['attempted'],
            'correct': row['correct'],
            'accuracy': row['accuracy'] or 0
        } for row in concepts],
        'byDifficulty': [{
            'difficulty': row['difficulty'],
            'attempted': row['attempted'],
            'correct': row['correct'],
            'accuracy': row['accuracy'] or 0
        } for row in difficulty],
        'sessionHistory': [{
            'sessionId': row['session_id'],
            'totalQuestions': row['total_questions'],
            'correctAnswers': row['correct_answers'],
            'accuracy': row['accuracy'] or 0
        } for row in history]
    })

@bp.route('/session/end', methods=['POST'])
def end_session():
    session_id = request.headers.get('X-Session-ID')
    if not session_id:
        return jsonify({'error': 'No session ID provided'}), 400
    
    db = get_db()
    
    # Get session stats
    stats = db.execute('''
        SELECT 
            COUNT(*) as total_questions,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
            ROUND(AVG(CASE WHEN is_correct THEN 100 ELSE 0 END), 2) as accuracy
        FROM user_answers
        WHERE session_id = ?
    ''', (session_id,)).fetchone()
    
    # Update session end time
    db.execute('UPDATE sessions SET end_time = CURRENT_TIMESTAMP WHERE id = ?', (session_id,))
    db.commit()
    
    return jsonify({
        'score': stats['accuracy'] or 0,
        'totalQuestions': stats['total_questions'],
        'correctAnswers': stats['correct_answers']
    })
