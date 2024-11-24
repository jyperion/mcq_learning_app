from flask import Blueprint, jsonify, request, current_app
from ..database.db import get_db
from datetime import datetime
import json

bp = Blueprint('practice', __name__, url_prefix='/api/practice')

@bp.route('/question', methods=['GET'])
def get_question():
    """Get a random question based on user's performance and preferences"""
    concept_id = request.args.get('concept_id', type=int)
    difficulty = request.args.get('difficulty')
    
    db = get_db()
    try:
        # Build query based on filters
        sql = '''
            SELECT q.*, GROUP_CONCAT(c.name) as concepts
            FROM questions q
            JOIN question_concepts qc ON q.id = qc.question_id
            JOIN concepts c ON qc.concept_id = c.id
        '''
        params = []
        
        if concept_id:
            sql += ' WHERE qc.concept_id = ?'
            params.append(concept_id)
        
        if difficulty:
            sql += ' AND' if concept_id else ' WHERE'
            sql += ' q.difficulty = ?'
            params.append(difficulty)
        
        # Group and order randomly
        sql += ' GROUP BY q.id ORDER BY RANDOM() LIMIT 1'
        
        question = db.execute(sql, params).fetchone()
        
        if not question:
            return jsonify({'error': 'No questions found matching criteria'}), 404
        
        return jsonify({
            'id': question['id'],
            'text': question['text'],
            'options': question['options'].split('|'),
            'difficulty': question['difficulty'],
            'concepts': question['concepts'].split(',')
        })
    except Exception as e:
        current_app.logger.error(f"Error getting question: {str(e)}")
        return jsonify({'error': 'Failed to get question'}), 500

@bp.route('/answer', methods=['POST'])
def submit_answer():
    """Submit an answer for a question"""
    data = request.get_json()
    if not data or 'questionId' not in data or 'answer' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    question_id = data['questionId']
    user_answer = data['answer']
    time_taken = data.get('timeTaken', 0)  # in seconds
    
    db = get_db()
    try:
        # Get correct answer
        question = db.execute(
            'SELECT correct_answer, explanation FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not question:
            return jsonify({'error': 'Question not found'}), 404
        
        is_correct = user_answer == question['correct_answer']
        
        # Record answer
        db.execute(
            'INSERT INTO user_answers (question_id, answer, is_correct, time_taken, timestamp) '
            'VALUES (?, ?, ?, ?, ?)',
            (question_id, user_answer, is_correct, time_taken, datetime.now())
        )
        db.commit()
        
        return jsonify({
            'correct': is_correct,
            'correctAnswer': question['correct_answer'],
            'explanation': question['explanation']
        })
    except Exception as e:
        current_app.logger.error(f"Error submitting answer: {str(e)}")
        return jsonify({'error': 'Failed to submit answer'}), 500

@bp.route('/hint', methods=['GET'])
def get_hint():
    """Get a hint for a specific question"""
    question_id = request.args.get('questionId', type=int)
    if not question_id:
        return jsonify({'error': 'Question ID required'}), 400
    
    db = get_db()
    try:
        hint = db.execute(
            'SELECT hint FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not hint or not hint['hint']:
            return jsonify({'error': 'No hint available'}), 404
        
        return jsonify({'hint': hint['hint']})
    except Exception as e:
        current_app.logger.error(f"Error getting hint: {str(e)}")
        return jsonify({'error': 'Failed to get hint'}), 500

@bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a question"""
    data = request.get_json()
    if not data or 'questionId' not in data or 'feedback' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    
    question_id = data['questionId']
    feedback = data['feedback']
    feedback_type = data.get('type', 'general')
    
    db = get_db()
    try:
        db.execute(
            'INSERT INTO question_feedback (question_id, feedback, type, timestamp) '
            'VALUES (?, ?, ?, ?)',
            (question_id, feedback, feedback_type, datetime.now())
        )
        db.commit()
        
        return jsonify({'message': 'Feedback submitted successfully'})
    except Exception as e:
        current_app.logger.error(f"Error submitting feedback: {str(e)}")
        return jsonify({'error': 'Failed to submit feedback'}), 500
