from flask import Blueprint, jsonify, request, current_app
from ..database import db
import json

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
            JOIN concept_questions cq ON q.id = cq.question_id
            WHERE cq.concept_id = ?
        '''
        total_result = db_conn.execute(total_query, (concept_id,)).fetchone()
        total_questions = total_result['total'] if total_result else 0
        current_app.logger.info(f"Total questions for concept {concept_id}: {total_questions}")
        
        # Get answered questions for this session and concept
        answered_count = 0
        if session_id and concept_id:
            # Get answered questions count for this concept in this session
            answered_query = '''
                SELECT COUNT(DISTINCT ua.question_id) as answered
                FROM user_answers ua
                JOIN concept_questions cq ON ua.question_id = cq.question_id
                WHERE ua.session_id = ? AND cq.concept_id = ?
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
                        JOIN concept_questions cq ON q.id = cq.question_id
                        WHERE cq.concept_id = ?
                    )
                ''', (session_id, concept_id))
                db_conn.commit()
                current_app.logger.info("Progress reset complete")
                # Reset answered count since we cleared progress
                answered_count = 0
        
        # Build the main query for random questions
        query = '''
            WITH available_questions AS (
                SELECT DISTINCT q.id, q.question, q.options, q.explanation, GROUP_CONCAT(c.name) as concepts
                FROM questions q
                JOIN concept_questions cq ON q.id = cq.question_id
                LEFT JOIN concepts c ON cq.concept_id = c.id
                WHERE cq.concept_id = ?
                AND q.id NOT IN (
                    SELECT DISTINCT ua.question_id
                    FROM user_answers ua
                    WHERE ua.session_id = ?
                )
                GROUP BY q.id
            )
            SELECT * FROM available_questions
            ORDER BY RANDOM()
            LIMIT ?
        '''
        
        params = [concept_id, session_id if session_id else '', count]
        current_app.logger.debug(f"Final query: {query}")
        current_app.logger.debug(f"Query parameters: {params}")
        
        questions = db_conn.execute(query, params).fetchall()
        current_app.logger.info(f"Found {len(questions)} questions")
        
        # If no questions found and we have answered some questions, clear progress and try again
        if len(questions) == 0 and answered_count > 0:
            current_app.logger.info("No questions found, clearing progress and retrying...")
            db_conn.execute('''
                DELETE FROM user_answers 
                WHERE session_id = ? AND question_id IN (
                    SELECT q.id 
                    FROM questions q
                    JOIN concept_questions cq ON q.id = cq.question_id
                    WHERE cq.concept_id = ?
                )
            ''', (session_id, concept_id))
            db_conn.commit()
            
            # Retry the query
            questions = db_conn.execute(query, params).fetchall()
            current_app.logger.info(f"After reset, found {len(questions)} questions")
        
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
            current_app.logger.debug(f"Added question ID {q['id']} to results")
        
        return jsonify(result if count > 1 else result[0] if result else None)
    except Exception as e:
        current_app.logger.error(f"Error getting random questions: {str(e)}")
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

        current_app.logger.info(f"Submitting answer - question_id: {question_id}, session_id: {session_id}")

        if not all([question_id, selected_option]):
            return jsonify({"error": "Missing required fields"}), 400

        # Get the question from database
        db_conn = db.get_db()
        question = db_conn.execute(
            'SELECT * FROM questions WHERE id = ?', 
            (question_id,)
        ).fetchone()

        if not question:
            current_app.logger.error(f"Question {question_id} not found")
            return jsonify({"error": "Question not found"}), 404

        # Check if the answer is correct
        is_correct = selected_option == question['correct_option']
        current_app.logger.info(f"Answer is {'correct' if is_correct else 'incorrect'}")
        
        # Update session progress if session_id is provided
        if session_id and time_taken is not None:
            db.update_session_progress(session_id, question_id, is_correct, time_taken)
            current_app.logger.info(f"Updated session progress for session {session_id}")

        return jsonify({
            'isCorrect': is_correct,
            'correct_option': question['correct_option'],
            'explanation': question['explanation']
        })

    except Exception as e:
        current_app.logger.error(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": str(e)}), 500
