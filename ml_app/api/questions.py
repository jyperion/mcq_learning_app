from flask import Blueprint, jsonify, request, current_app
from ..database import db
import json

bp = Blueprint('questions', __name__, url_prefix='/api/questions')

@bp.route('/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get a specific question"""
    try:
        db_conn = db.get_db()
        question = db_conn.execute(
            'SELECT q.*, c.name as concept_name '
            'FROM questions q '
            'LEFT JOIN concepts c ON q.concept_id = c.id '
            'WHERE q.id = ?',
            (question_id,)
        ).fetchone()
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
            
        # Parse options from JSON string
        options = json.loads(question['options'])
        
        return jsonify({
            'id': question['id'],
            'text': question['text'],
            'options': options,
            'explanation': question['explanation'],
            'difficulty': question['difficulty'],
            'hint': question.get('hint', ''),  # Use dict access with default
            'concepts': [question['concept_name']] if question['concept_name'] else []
        })
    except Exception as e:
        current_app.logger.error(f"Error getting question: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/random', methods=['GET'])
def get_random_questions():
    """Get random questions, optionally filtered by concept"""
    try:
        concept_id = request.args.get('concept_id', type=int)
        count = request.args.get('count', 1, type=int)
        session_id = request.headers.get('X-Session-ID')
        
        current_app.logger.info(f"Getting random questions - concept_id: {concept_id}, count: {count}, session_id: {session_id}")
        
        db_conn = db.get_db()
        
        # First, get total questions for this concept
        total_query = '''
            SELECT COUNT(DISTINCT q.id) as total
            FROM questions q
            WHERE q.concept_id = ?
        '''
        total_result = db_conn.execute(total_query, (concept_id,)).fetchone()
        total_questions = total_result['total'] if total_result else 0
        current_app.logger.info(f"Total questions for concept {concept_id}: {total_questions}")
        
        # Get answered questions for this session and concept
        answered_count = 0
        if session_id and concept_id:
            answered_query = '''
                SELECT COUNT(DISTINCT ua.question_id) as answered
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                WHERE ua.session_id = ? AND q.concept_id = ?
            '''
            answered_result = db_conn.execute(answered_query, (session_id, concept_id)).fetchone()
            answered_count = answered_result['answered'] if answered_result else 0
            current_app.logger.info(f"Answered questions for session {session_id} and concept {concept_id}: {answered_count}")
            
            # If all questions are answered, clear the session progress for this concept
            if answered_count >= total_questions and total_questions > 0:
                current_app.logger.info(f"All questions answered for concept {concept_id}. Resetting progress...")
                db_conn.execute('''
                    DELETE FROM user_answers 
                    WHERE session_id = ? AND question_id IN (
                        SELECT q.id 
                        FROM questions q
                        WHERE q.concept_id = ?
                    )
                ''', (session_id, concept_id))
                db_conn.commit()
                current_app.logger.info("Progress reset complete")
                answered_count = 0
        
        # Build the main query for random questions
        query = '''
            WITH available_questions AS (
                SELECT DISTINCT q.id, q.text, q.options, q.explanation, 
                       q.difficulty, q.hint, c.name as concept_name
                FROM questions q
                LEFT JOIN concepts c ON q.concept_id = c.id
                WHERE q.concept_id = ?
                AND q.id NOT IN (
                    SELECT DISTINCT ua.question_id
                    FROM user_answers ua
                    WHERE ua.session_id = ?
                )
            )
            SELECT * FROM available_questions
            ORDER BY RANDOM()
            LIMIT ?
        '''
        
        params = [concept_id, session_id if session_id else '', count]
        current_app.logger.debug(f"Query parameters: {params}")
        
        questions = db_conn.execute(query, params).fetchall()
        current_app.logger.info(f"Found {len(questions)} questions")
        
        # If no questions found and we have answered some questions, clear progress and try again
        if len(questions) == 0 and answered_count > 0:
            current_app.logger.info("No questions found but some were answered. Clearing progress and trying again...")
            db_conn.execute('''
                DELETE FROM user_answers 
                WHERE session_id = ? AND question_id IN (
                    SELECT q.id 
                    FROM questions q
                    WHERE q.concept_id = ?
                )
            ''', (session_id, concept_id))
            db_conn.commit()
            
            # Try query again
            questions = db_conn.execute(query, params).fetchall()
            current_app.logger.info(f"Found {len(questions)} questions after reset")
        
        return jsonify([{
            'id': q['id'],
            'text': q['text'],
            'options': json.loads(q['options']),
            'explanation': q['explanation'],
            'difficulty': q['difficulty'],
            'hint': q['hint'] if 'hint' in q else '',  # Use dict access with default
            'concepts': [q['concept_name']] if q['concept_name'] else []
        } for q in questions])
        
    except Exception as e:
        current_app.logger.error(f"Error getting random questions: {str(e)}")
        return jsonify({"error": "Failed to get questions"}), 500

@bp.route('/<int:question_id>/submit', methods=['POST'])
def submit_answer(question_id):
    """Submit an answer to a question"""
    try:
        data = request.get_json()
        if not data or 'answer' not in data:
            return jsonify({"error": "No answer provided"}), 400
            
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            return jsonify({"error": "No session ID provided"}), 400
            
        answer = int(data['answer'])  # Convert to int since we store indices
        time_taken = int(data.get('time_taken', 0))  # Time taken in seconds
        
        db_conn = db.get_db()
        
        # Get the question to check the answer
        question = db_conn.execute(
            'SELECT * FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
            
        # Record the answer
        is_correct = answer == int(question['correct_answer'])
        db_conn.execute(
            'INSERT INTO user_answers (session_id, question_id, answer, is_correct, time_taken) VALUES (?, ?, ?, ?, ?)',
            (session_id, question_id, answer, is_correct, time_taken)
        )
        db_conn.commit()
        
        # Parse options from JSON string
        options = json.loads(question['options'])
        
        response = {
            "correct": is_correct,
            "correct_answer": int(question['correct_answer']),  # Always include correct answer
            "explanation": question['explanation'],
            "correct_answer_text": options[int(question['correct_answer'])]
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error submitting answer: {str(e)}")
        return jsonify({"error": "Failed to submit answer"}), 500
