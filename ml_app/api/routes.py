from flask import Blueprint, jsonify, request, current_app
from ..database.db import get_db
import json
import uuid
import random
import sqlite3

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.errorhandler(Exception)
def handle_error(error):
    """Handle all errors and return JSON response."""
    current_app.logger.error(f"Error: {str(error)}")
    response = {
        "error": "Internal server error",
        "message": str(error)
    }
    return jsonify(response), 500

@bp.route('/concepts', methods=['GET'])
def concepts():
    """Get all available concepts."""
    try:
        db = get_db()
        current_app.logger.debug("Getting concepts from database")
        
        # First, check if we have any concepts
        count = db.execute('SELECT COUNT(*) as count FROM concepts').fetchone()
        current_app.logger.debug(f"Found {count['count']} concepts")
        
        concepts = db.execute('''
            SELECT c.*, COUNT(cq.question_id) as question_count 
            FROM concepts c 
            LEFT JOIN concept_questions cq ON c.id = cq.concept_id 
            GROUP BY c.id
        ''').fetchall()
        
        result = [{
            'id': c['id'],
            'name': c['name'],
            'description': c['description'],
            'question_count': c['question_count']
        } for c in concepts]
        
        current_app.logger.debug(f"Returning {len(result)} concepts")
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error in concepts endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/concepts/<int:concept_id>/questions')
def get_questions(concept_id):
    """Get questions for a concept with pagination."""
    try:
        db = get_db()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        offset = (page - 1) * per_page
        
        # Get concept
        concept = db.execute(
            'SELECT * FROM concepts WHERE id = ?',
            (concept_id,)
        ).fetchone()
        
        if not concept:
            return jsonify({"error": "Concept not found"}), 404
        
        # Get total questions count
        total = db.execute('''
            SELECT COUNT(*) as count FROM concept_questions 
            WHERE concept_id = ?
        ''', (concept_id,)).fetchone()['count']
        
        # Get paginated questions
        questions = db.execute('''
            SELECT q.* FROM questions q
            JOIN concept_questions cq ON q.id = cq.question_id
            WHERE cq.concept_id = ?
            LIMIT ? OFFSET ?
        ''', (concept_id, per_page, offset)).fetchall()
        
        return jsonify({
            'concept': {
                'id': concept['id'],
                'name': concept['name'],
                'description': concept['description']
            },
            'questions': [{
                'id': q['id'],
                'question': q['question'],
                'options': json.loads(q['options']),
                'correct': q['correct'],
                'explanation': q['explanation'],
                'difficulty': q['difficulty']
            } for q in questions],
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/questions/random', methods=['GET'])
def get_random_questions():
    """Get random questions, optionally filtered by concept."""
    try:
        db = get_db()
        concept_id = request.args.get('concept_id', type=int)
        count = min(request.args.get('count', 5, type=int), 20)  # Limit to 20 questions max
        
        current_app.logger.debug(f"Getting {count} random questions, concept_id: {concept_id}")
        
        # First check if we have any questions at all
        total_questions = db.execute('SELECT COUNT(*) as count FROM questions').fetchone()
        current_app.logger.debug(f"Total questions in database: {total_questions['count']}")
        
        if total_questions['count'] == 0:
            current_app.logger.error("No questions found in database")
            return jsonify({"error": "No questions available"}), 404
        
        if concept_id:
            # Check if concept exists
            concept = db.execute('SELECT * FROM concepts WHERE id = ?', (concept_id,)).fetchone()
            if not concept:
                current_app.logger.error(f"Concept {concept_id} not found")
                return jsonify({"error": "Concept not found"}), 404
            
            # Get questions for concept
            questions = db.execute('''
                SELECT q.* FROM questions q
                JOIN concept_questions cq ON q.id = cq.question_id
                WHERE cq.concept_id = ?
                ORDER BY RANDOM()
                LIMIT ?
            ''', (concept_id, count)).fetchall()
            
            if not questions:
                current_app.logger.error(f"No questions found for concept {concept_id}")
                return jsonify({"error": "No questions available for this concept"}), 404
        else:
            # Get random questions from any concept
            questions = db.execute('''
                SELECT q.* FROM questions q
                ORDER BY RANDOM()
                LIMIT ?
            ''', (count,)).fetchall()
            
            if not questions:
                current_app.logger.error("Failed to get random questions")
                return jsonify({"error": "Failed to get random questions"}), 500
        
        current_app.logger.debug(f"Found {len(questions)} questions")
        
        result = [{
            'id': q['id'],
            'question': q['question'],
            'options': json.loads(q['options']),
            'correct': q['correct'],
            'explanation': q['explanation'],
            'difficulty': q['difficulty']
        } for q in questions]
        
        current_app.logger.debug(f"Returning {len(result)} questions")
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error in get_random_questions: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/questions/submit', methods=['POST'])
def submit_answer():
    """Submit an answer to a question."""
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type"}), 400
        
        data = request.get_json()
        required_fields = ['question_id', 'selected_option', 'time_taken']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        db = get_db()
        question = db.execute(
            'SELECT * FROM questions WHERE id = ?',
            (data['question_id'],)
        ).fetchone()
        
        if not question:
            return jsonify({"error": "Question not found"}), 404
        
        # Get or create user
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            session_id = str(uuid.uuid4())
        
        user = db.execute(
            'SELECT * FROM users WHERE session_id = ?',
            (session_id,)
        ).fetchone()
        
        if not user:
            cursor = db.execute(
                'INSERT INTO users (session_id) VALUES (?)',
                (session_id,)
            )
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        # Record the answer
        is_correct = data['selected_option'] == question['correct']
        try:
            db.execute('''
                INSERT INTO user_progress 
                (user_id, question_id, selected_option, is_correct, time_taken) 
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                data['question_id'],
                data['selected_option'],
                is_correct,
                data['time_taken']
            ))
            db.commit()
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error: {str(e)}")
            return jsonify({"error": "Failed to record progress"}), 500
        
        # Get the correct answer text
        options = json.loads(question['options'])
        correct_index = ord(question['correct']) - ord('A')
        correct_answer = options[correct_index] if 0 <= correct_index < len(options) else None
        
        response = {
            "is_correct": is_correct,
            "correct_option": question['correct'],  # The letter (A, B, C, D)
            "correct_answer": correct_answer,       # The actual text of the correct answer
            "explanation": question['explanation']
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error in submit_answer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/progress', methods=['GET'])
def get_user_progress():
    """Get user's progress statistics."""
    try:
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            return jsonify({"error": "Session ID required"}), 400
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE session_id = ?',
            (session_id,)
        ).fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get overall stats
        stats = db.execute('''
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct_answers,
                AVG(time_taken) as avg_time,
                AVG(CASE WHEN is_correct THEN 1 ELSE 0 END) * 100 as accuracy
            FROM user_progress
            WHERE user_id = ?
        ''', (user['id'],)).fetchone()
        
        # Get concept-wise stats with recommendations
        concept_stats = db.execute('''
            WITH concept_progress AS (
                SELECT 
                    c.id,
                    c.name,
                    c.description,
                    COUNT(DISTINCT q.id) as total_questions,
                    COUNT(DISTINCT up.question_id) as attempted,
                    SUM(CASE WHEN up.is_correct THEN 1 ELSE 0 END) as correct
                FROM concepts c
                LEFT JOIN concept_questions cq ON c.id = cq.concept_id
                LEFT JOIN questions q ON cq.question_id = q.id
                LEFT JOIN user_progress up ON q.id = up.question_id AND up.user_id = ?
                GROUP BY c.id
            )
            SELECT 
                id,
                name,
                description,
                total_questions,
                attempted,
                correct,
                CASE 
                    WHEN attempted = 0 THEN 'Not started'
                    WHEN correct * 100.0 / attempted >= 80 THEN 'Mastered'
                    WHEN correct * 100.0 / attempted >= 50 THEN 'In progress'
                    ELSE 'Needs practice'
                END as status,
                CASE
                    WHEN attempted = 0 THEN 1
                    WHEN correct * 100.0 / attempted < 50 THEN 2
                    WHEN correct * 100.0 / attempted < 80 THEN 3
                    ELSE 4
                END as priority
            FROM concept_progress
            ORDER BY priority ASC, name ASC
        ''', (user['id'],)).fetchall()
        
        return jsonify({
            'user': {
                'name': user['name'],
                'session_id': user['session_id']
            },
            'overall_stats': {
                'total_questions': stats['total_questions'],
                'correct_answers': stats['correct_answers'],
                'accuracy': round(stats['accuracy'], 2) if stats['accuracy'] is not None else 0,
                'avg_time': round(stats['avg_time'], 2) if stats['avg_time'] is not None else 0
            },
            'concept_stats': [{
                'id': stat['id'],
                'name': stat['name'],
                'description': stat['description'],
                'total_questions': stat['total_questions'],
                'attempted': stat['attempted'],
                'correct': stat['correct'],
                'accuracy': round((stat['correct'] / stat['attempted']) * 100, 2) if stat['attempted'] > 0 else 0,
                'status': stat['status'],
                'priority': stat['priority']
            } for stat in concept_stats]
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_user_progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/session/start', methods=['POST'])
def start_session():
    """Start a new user session."""
    try:
        current_app.logger.debug("Starting new session")
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({"error": "No JSON data received"}), 400
            
        if 'name' not in data:
            current_app.logger.error("Name field missing from request")
            return jsonify({"error": "Name is required"}), 400
            
        session_id = str(uuid.uuid4())
        current_app.logger.debug(f"Generated session ID: {session_id}")
        
        try:
            db = get_db()
            current_app.logger.debug("Got database connection")
            
            cursor = db.execute(
                'INSERT INTO users (name, session_id) VALUES (?, ?)',
                (data['name'], session_id)
            )
            user_id = cursor.lastrowid
            current_app.logger.debug(f"Inserted user with ID: {user_id}")
            
            db.commit()
            current_app.logger.debug("Committed database transaction")
            
            return jsonify({
                "session_id": session_id,
                "user_id": user_id,
                "name": data['name']
            })
            
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error in start_session: {str(e)}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in start_session: {str(e)}")
        return jsonify({"error": str(e)}), 500
