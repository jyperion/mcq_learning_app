from flask import Blueprint, jsonify, request, current_app
from ..database.db import get_db
import json

bp = Blueprint('concepts', __name__, url_prefix='/api/concepts')

@bp.route('/')
def get_concepts():
    """Get list of all ML concepts"""
    db = get_db()
    try:
        concepts = db.execute(
            'SELECT c.id, c.name, c.description, '
            'COUNT(DISTINCT q.id) as question_count '
            'FROM concepts c '
            'LEFT JOIN questions q ON c.id = q.concept_id '
            'GROUP BY c.id'
        ).fetchall()
        
        return jsonify([{
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'question_count': row['question_count'],
            'status': 'Not started'  # Default status
        } for row in concepts])
    except Exception as e:
        current_app.logger.error(f"Error getting concepts: {str(e)}")
        return jsonify({'error': 'Failed to get concepts'}), 500

@bp.route('/<int:concept_id>')
def get_concept_details(concept_id):
    """Get detailed information about a specific concept"""
    db = get_db()
    try:
        # Get concept details
        concept = db.execute(
            'SELECT c.* '
            'FROM concepts c '
            'WHERE c.id = ?',
            (concept_id,)
        ).fetchone()
        
        if not concept:
            return jsonify({'error': 'Concept not found'}), 404
        
        # Get performance statistics
        stats = db.execute(
            'SELECT COUNT(DISTINCT q.id) as total_questions, '
            'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as avg_score, '
            'AVG(ua.time_taken) as avg_time '
            'FROM concepts c '
            'JOIN questions q ON c.id = q.concept_id '
            'LEFT JOIN user_answers ua ON q.id = ua.question_id '
            'WHERE c.id = ? '
            'GROUP BY c.id',
            (concept_id,)
        ).fetchone()
        
        # Get recent questions
        recent_questions = db.execute(
            'SELECT q.id, q.text, q.difficulty, '
            'COUNT(ua.id) as attempts, '
            'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as success_rate '
            'FROM questions q '
            'LEFT JOIN user_answers ua ON q.id = ua.question_id '
            'WHERE q.concept_id = ? '
            'GROUP BY q.id '
            'ORDER BY q.id DESC '
            'LIMIT 5',
            (concept_id,)
        ).fetchall()
        
        return jsonify({
            'id': concept['id'],
            'name': concept['name'],
            'description': concept['description'],
            'stats': {
                'total_questions': stats['total_questions'] if stats else 0,
                'avg_score': round(stats['avg_score'], 2) if stats and stats['avg_score'] is not None else 0,
                'avg_time': round(stats['avg_time'], 2) if stats and stats['avg_time'] is not None else 0
            },
            'recent_questions': [{
                'id': q['id'],
                'text': q['text'],
                'difficulty': q['difficulty'],
                'attempts': q['attempts'],
                'success_rate': round(q['success_rate'], 2) if q['success_rate'] is not None else 0
            } for q in recent_questions]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting concept details: {str(e)}")
        return jsonify({'error': 'Failed to get concept details'}), 500

@bp.route('/<int:concept_id>/questions')
def get_concept_questions(concept_id):
    """Get all questions for a specific concept"""
    db = get_db()
    try:
        questions = db.execute(
            'SELECT q.*, '
            'COUNT(ua.id) as attempts, '
            'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as success_rate '
            'FROM questions q '
            'LEFT JOIN user_answers ua ON q.id = ua.question_id '
            'WHERE q.concept_id = ? '
            'GROUP BY q.id '
            'ORDER BY q.id',
            (concept_id,)
        ).fetchall()
        
        return jsonify([{
            'id': q['id'],
            'text': q['text'],
            'options': json.loads(q['options']),
            'difficulty': q['difficulty'],
            'hint': q.get('hint', ''),
            'attempts': q['attempts'],
            'success_rate': round(q['success_rate'], 2) if q['success_rate'] is not None else 0
        } for q in questions])
    except Exception as e:
        current_app.logger.error(f"Error getting concept questions: {str(e)}")
        return jsonify({'error': 'Failed to get concept questions'}), 500

@bp.route('/search')
def search_concepts():
    """Search concepts by name or description"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    db = get_db()
    try:
        concepts = db.execute(
            'SELECT c.id, c.name, c.description, '
            'COUNT(DISTINCT q.id) as question_count '
            'FROM concepts c '
            'LEFT JOIN question_concepts qc ON c.id = qc.concept_id '
            'LEFT JOIN questions q ON qc.question_id = q.id '
            'WHERE c.name LIKE ? OR c.description LIKE ? '
            'GROUP BY c.id '
            'LIMIT 10',
            (f'%{query}%', f'%{query}%')
        ).fetchall()
        
        return jsonify([{
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'question_count': row['question_count']
        } for row in concepts])
    except Exception as e:
        current_app.logger.error(f"Error searching concepts: {str(e)}")
        return jsonify({'error': 'Failed to search concepts'}), 500
