from flask import Blueprint, jsonify, request, current_app
from ..database import db
from ..question_generation.generate_questions import query_ollama_async
import asyncio
import json
import re

bp = Blueprint('questions', __name__)

@bp.route('/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get a specific question"""
    try:
        question = db.get_question(question_id)
        if not question:
            return jsonify({"error": "Question not found"}), 404
        return jsonify(question)
    except Exception as e:
        current_app.logger.error(f"Error getting question: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/recheck/<int:question_id>', methods=['POST'])
def recheck_question(question_id):
    """Recheck a question using Ollama"""
    try:
        question = db.get_question(question_id)
        if not question:
            current_app.logger.error(f"Question {question_id} not found")
            return jsonify({"error": "Question not found"}), 404

        prompt = f"""You are an expert in machine learning. Generate a multiple choice question about {question['concept']} in machine learning. 
        The question should be challenging and test deep understanding.
        
        Format your response as a JSON object with EXACTLY this structure:
        {{
            "question": "Your question text here?",
            "options": [
                "A) First option",
                "B) Second option",
                "C) Third option",
                "D) Fourth option"
            ],
            "correct": "A) First option",
            "explanation": "Detailed explanation of why this answer is correct"
        }}
        
        Do not include any text outside the JSON object. Ensure the JSON is valid and properly formatted."""

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response_text = loop.run_until_complete(query_ollama_async(prompt))
            json_match = re.search(r'({[\s\S]*})', response_text)
            if not json_match:
                raise Exception("No JSON object found in response")
            
            json_str = json_match.group(1)
            new_response = json.loads(json_str)
            
            # Validate response structure
            required_keys = ['question', 'options', 'correct', 'explanation']
            if not all(key in new_response for key in required_keys):
                raise Exception("Missing required fields in response")
            if not isinstance(new_response['options'], list) or len(new_response['options']) != 4:
                raise Exception("Invalid options format")
        finally:
            loop.close()

        return jsonify({
            "original": question,
            "new_response": new_response
        })

    except Exception as e:
        current_app.logger.error(f"Error in recheck_question: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/random', methods=['GET'])
def get_random_questions():
    """Get random questions, optionally filtered by concept"""
    try:
        concept_id = request.args.get('concept_id', type=int)
        count = request.args.get('count', 1, type=int)
        session_id = request.headers.get('X-Session-ID')
        
        db_conn = db.get_db()
        
        query = '''
            SELECT q.*, GROUP_CONCAT(c.name) as concepts
            FROM questions q
            LEFT JOIN concept_questions cq ON q.id = cq.question_id
            LEFT JOIN concepts c ON cq.concept_id = c.id
        '''
        
        params = []
        if concept_id:
            query += ' WHERE cq.concept_id = ?'
            params.append(concept_id)
        
        if session_id:
            answered = db_conn.execute('''
                SELECT question_id FROM user_answers
                WHERE session_id = ?
            ''', (session_id,)).fetchall()
            answered_questions = [q['question_id'] for q in answered]
            query += ' AND q.id NOT IN (%s)' % ','.join('?' * len(answered_questions))
            params.extend(answered_questions)
        
        query += ' GROUP BY q.id ORDER BY RANDOM() LIMIT ?'
        params.append(count)
        
        questions = db_conn.execute(query, params).fetchall()
        
        result = []
        for q in questions:
            question_data = {
                'id': q['id'],
                'question': q['question'],
                'options': json.loads(q['options']),
                'concepts': q['concepts'].split(',') if q['concepts'] else [],
                'explanation': q['explanation']
            }
            result.append(question_data)
        
        return jsonify(result if count > 1 else result[0] if result else None)
    except Exception as e:
        current_app.logger.error(f"Error getting random questions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:question_id>/feedback', methods=['POST'])
def update_question_status(question_id):
    """Update question status based on user feedback"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        status = data.get('status')
        new_answer = data.get('new_answer')

        if not status or status not in ['flagged', 'updated']:
            return jsonify({"error": "Invalid status"}), 400

        db.update_question_status(question_id, status, new_answer)
        return jsonify({"message": "Question updated successfully"})

    except Exception as e:
        current_app.logger.error(f"Error in update_question_status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/submit', methods=['POST'])
def submit_answer():
    """Submit an answer to a question"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        question_id = data.get('question_id')
        selected_option = data.get('selected_option')
        session_id = data.get('session_id')
        time_taken = data.get('time_taken')

        if not all([question_id, selected_option]):
            return jsonify({"error": "Missing required fields"}), 400

        # Get the question from database
        db_conn = db.get_db()
        question = db_conn.execute(
            'SELECT * FROM questions WHERE id = ?', 
            (question_id,)
        ).fetchone()

        if not question:
            return jsonify({"error": "Question not found"}), 404

        # Check if the answer is correct
        is_correct = selected_option == question['correct_option']
        
        # Update session progress if session_id is provided
        if session_id and time_taken is not None:
            db.update_session_progress(session_id, question_id, is_correct, time_taken)

        return jsonify({
            'isCorrect': is_correct,
            'correct_option': question['correct_option'],
            'explanation': question['explanation']
        })

    except Exception as e:
        current_app.logger.error(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Delete a question"""
    try:
        if db.delete_question(question_id):
            return jsonify({"message": "Question deleted successfully"})
        else:
            return jsonify({"error": "Question not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting question: {str(e)}")
        return jsonify({"error": str(e)}), 500
