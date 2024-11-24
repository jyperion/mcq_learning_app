from flask import Blueprint, jsonify, request, current_app
from ..database.db import get_db

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
            'LEFT JOIN question_concepts qc ON c.id = qc.concept_id '
            'LEFT JOIN questions q ON qc.question_id = q.id '
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
            'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as avg_score '
            'FROM concepts c '
            'JOIN question_concepts qc ON c.id = qc.concept_id '
            'JOIN questions q ON qc.question_id = q.id '
            'LEFT JOIN user_answers ua ON q.id = ua.question_id '
            'WHERE c.id = ?',
            (concept_id,)
        ).fetchone()
        
        return jsonify({
            'id': concept['id'],
            'name': concept['name'],
            'description': concept['description'],
            'totalQuestions': stats['total_questions'],
            'averageScore': round(stats['avg_score'] or 0, 2)
        })
    except Exception as e:
        current_app.logger.error(f"Error getting concept details: {str(e)}")
        return jsonify({'error': 'Failed to get concept details'}), 500

@bp.route('/<int:concept_id>/questions')
def get_concept_questions(concept_id):
    """Get questions for a specific concept"""
    db = get_db()
    try:
        questions = db.execute(
            'SELECT q.* '
            'FROM questions q '
            'JOIN question_concepts qc ON q.id = qc.question_id '
            'WHERE qc.concept_id = ? '
            'ORDER BY RANDOM() '
            'LIMIT 5',
            (concept_id,)
        ).fetchall()
        
        return jsonify([{
            'id': q['id'],
            'text': q['text'],
            'options': q['options'].split('|'),
            'difficulty': q['difficulty']
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
