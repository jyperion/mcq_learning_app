import sqlite3
import click
from flask import current_app, g
from datetime import datetime
from flask.cli import with_appcontext
import os
import json

def adapt_datetime(dt):
    """Convert datetime to string."""
    return dt.isoformat()

def convert_datetime(s):
    """Convert string to datetime."""
    try:
        return datetime.fromisoformat(s.decode())
    except (AttributeError, ValueError):
        return None

def get_db():
    """Get database connection."""
    if 'db' not in g:
        try:
            current_app.logger.debug(f"Connecting to database at: {current_app.config['DATABASE']}")
            # Register timestamp converter
            sqlite3.register_adapter(datetime, adapt_datetime)
            sqlite3.register_converter('timestamp', convert_datetime)
            
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            g.db.row_factory = sqlite3.Row
            current_app.logger.debug("Database connection successful")
        except Exception as e:
            current_app.logger.error(f"Database connection failed: {str(e)}")
            raise
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    
    if db is not None:
        try:
            db.close()
            current_app.logger.debug("Database connection closed successfully")
        except Exception as e:
            current_app.logger.error(f"Error closing database: {str(e)}")

def init_db(force=False):
    """Initialize the database."""
    db = get_db()
    
    # Create tables from schema
    with current_app.open_resource('database/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    db.commit()

def get_question(question_id):
    """Get a single question by ID"""
    db = get_db()
    question = db.execute(
        'SELECT q.*, c.name as concept FROM questions q '
        'JOIN concept_questions cq ON q.id = cq.question_id '
        'JOIN concepts c ON c.id = cq.concept_id '
        'WHERE q.id = ?',
        (question_id,)
    ).fetchone()
    return dict(question) if question else None

def update_question_status(question_id, status, new_answer=None):
    """Update a question's status and optionally its answer"""
    db = get_db()
    if status == 'updated' and new_answer:
        db.execute(
            'UPDATE questions SET status = ?, updated_answer = ? WHERE id = ?',
            (status, new_answer, question_id)
        )
    else:
        db.execute(
            'UPDATE questions SET status = ? WHERE id = ?',
            (status, question_id)
        )
    db.commit()

def delete_question(question_id):
    """Delete a question and its concept associations"""
    db = get_db()
    try:
        # Start a transaction
        db.execute('BEGIN')
        
        # Delete from concept_questions first (foreign key constraint)
        db.execute('DELETE FROM concept_questions WHERE question_id = ?', (question_id,))
        
        # Delete the question
        result = db.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        
        if result.rowcount == 0:
            db.execute('ROLLBACK')
            return False
            
        # Commit the transaction
        db.execute('COMMIT')
        return True
        
    except Exception as e:
        db.execute('ROLLBACK')
        current_app.logger.error(f"Error deleting question {question_id}: {str(e)}")
        raise

@click.command('init-db')
@click.option('--force', is_flag=True, help='Force reinitialize the database even if it exists')
@with_appcontext
def init_db_command(force):
    """Clear the existing data and create new tables."""
    init_db(force)
    click.echo('Initialized the database.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

def get_random_question():
    """Get a random question from the database"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT q.*, GROUP_CONCAT(c.name) as concepts '
        'FROM questions q '
        'LEFT JOIN question_concepts qc ON q.id = qc.question_id '
        'LEFT JOIN concepts c ON qc.concept_id = c.id '
        'GROUP BY q.id '
        'ORDER BY RANDOM() LIMIT 1'
    )
    question = cursor.fetchone()
    if question:
        question['concepts'] = question['concepts'].split(',') if question['concepts'] else []
        question['options'] = json.loads(question['options'])
    return question

def get_stats_overview():
    """Get overview statistics"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT COUNT(*) as total_questions, '
        'AVG(CASE WHEN is_correct THEN 100 ELSE 0 END) as average_score, '
        'SUM(time_spent) as total_time '
        'FROM user_answers'
    )
    return cursor.fetchone()

def get_concept_stats():
    """Get performance by concept"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT c.name as concept, '
        'AVG(CASE WHEN ua.is_correct THEN 100 ELSE 0 END) as score '
        'FROM concepts c '
        'JOIN question_concepts qc ON c.id = qc.concept_id '
        'JOIN user_answers ua ON qc.question_id = ua.question_id '
        'GROUP BY c.id, c.name'
    )
    return cursor.fetchall()

def get_progress_stats():
    """Get progress over time"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT date(created_at) as date, '
        'AVG(CASE WHEN is_correct THEN 100 ELSE 0 END) as score '
        'FROM user_answers '
        'GROUP BY date(created_at) '
        'ORDER BY date(created_at)'
    )
    return cursor.fetchall()

def get_recent_activity():
    """Get recent activity"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT ua.created_at as date, '
        'c.name as concept, '
        'CASE WHEN ua.is_correct THEN 100 ELSE 0 END as score, '
        'ua.time_spent '
        'FROM user_answers ua '
        'JOIN questions q ON ua.question_id = q.id '
        'JOIN question_concepts qc ON q.id = qc.question_id '
        'JOIN concepts c ON qc.concept_id = c.id '
        'ORDER BY ua.created_at DESC LIMIT 10'
    )
    return cursor.fetchall()

def get_all_concepts():
    """Get all concepts"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT c.*, '
        'GROUP_CONCAT(t.name) as topics '
        'FROM concepts c '
        'LEFT JOIN concept_topics ct ON c.id = ct.concept_id '
        'LEFT JOIN topics t ON ct.topic_id = t.id '
        'GROUP BY c.id'
    )
    concepts = cursor.fetchall()
    for concept in concepts:
        concept['topics'] = concept['topics'].split(',') if concept['topics'] else []
    return concepts

def get_concept(concept_id):
    """Get concept details"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'SELECT c.*, '
        'GROUP_CONCAT(DISTINCT t.name) as topics, '
        'GROUP_CONCAT(DISTINCT p.name) as prerequisites '
        'FROM concepts c '
        'LEFT JOIN concept_topics ct ON c.id = ct.concept_id '
        'LEFT JOIN topics t ON ct.topic_id = t.id '
        'LEFT JOIN concept_prerequisites cp ON c.id = cp.concept_id '
        'LEFT JOIN concepts p ON cp.prerequisite_id = p.id '
        'WHERE c.id = ? '
        'GROUP BY c.id',
        (concept_id,)
    )
    concept = cursor.fetchone()
    if concept:
        concept['topics'] = concept['topics'].split(',') if concept['topics'] else []
        concept['prerequisites'] = concept['prerequisites'].split(',') if concept['prerequisites'] else []
    return concept

def create_session(concept_id=None):
    """Create a new practice session"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            'INSERT INTO practice_sessions (concept_id, start_time) VALUES (?, CURRENT_TIMESTAMP)',
            (concept_id,)
        )
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        db.rollback()
        raise e

def end_session(session_id):
    """End a practice session"""
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            'UPDATE practice_sessions SET end_time = CURRENT_TIMESTAMP WHERE id = ?',
            (session_id,)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

def update_session_progress(session_id, question_id, is_correct, time_spent):
    """Update session progress with a new answer"""
    db = get_db()
    cursor = db.cursor()
    try:
        # Record the answer
        cursor.execute(
            'INSERT INTO user_answers (session_id, question_id, is_correct, time_spent) '
            'VALUES (?, ?, ?, ?)',
            (session_id, question_id, is_correct, time_spent)
        )
        
        # Update session statistics
        cursor.execute(
            'UPDATE practice_sessions SET '
            'questions_answered = questions_answered + 1, '
            'correct_answers = correct_answers + ?, '
            'total_time = total_time + ? '
            'WHERE id = ?',
            (1 if is_correct else 0, time_spent, session_id)
        )
        
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
