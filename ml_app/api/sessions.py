from flask import Blueprint, jsonify, request, current_app, make_response
from ..database import db

bp = Blueprint('sessions', __name__)

@bp.route('/start', methods=['POST', 'OPTIONS'])
def start_session():
    """Start a new practice session"""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json() or {}
        concept_id = data.get('conceptId')
        
        session_id = db.create_session(concept_id)
        response = jsonify({
            'sessionId': session_id,
            'message': 'Session started successfully'
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        current_app.logger.error(f"Error starting session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:session_id>/end', methods=['POST', 'OPTIONS'])
def end_session(session_id):
    """End a practice session"""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        db.end_session(session_id)
        response = jsonify({'message': 'Session ended successfully'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        current_app.logger.error(f"Error ending session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:session_id>/progress', methods=['POST', 'OPTIONS'])
def update_session_progress(session_id):
    """Update session progress"""
    if request.method == 'OPTIONS':
        response = make_response('')
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        question_id = data.get('questionId')
        is_correct = data.get('isCorrect')
        time_spent = data.get('timeSpent')
        
        if None in (question_id, is_correct, time_spent):
            return jsonify({'error': 'Missing required fields'}), 400
            
        db.update_session_progress(session_id, question_id, is_correct, time_spent)
        response = jsonify({'message': 'Progress updated successfully'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    except Exception as e:
        current_app.logger.error(f"Error updating session progress: {str(e)}")
        return jsonify({'error': str(e)}), 500
