import json
import sqlite3
import os
from flask import current_app
from ml_app.database.db import get_db, init_db

def database_exists():
    """Check if database exists and has data."""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if tables exist and have data
        cursor.execute("SELECT COUNT(*) FROM questions")
        question_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM concepts")
        concept_count = cursor.fetchone()[0]
        
        current_app.logger.info(f"Found {concept_count} concepts and {question_count} questions in database")
        
        return question_count > 0 and concept_count > 0
    except sqlite3.Error as e:
        current_app.logger.error(f"Error checking database: {str(e)}")
        return False

def get_concept_id(db, concept_name, concept_map):
    """Get or create concept ID for a given concept name."""
    if concept_name not in concept_map:
        try:
            cursor = db.execute(
                'INSERT INTO concepts (name, description) VALUES (?, ?)',
                (concept_name, '')
            )
            concept_map[concept_name] = cursor.lastrowid
        except sqlite3.IntegrityError:
            # If concept was added by another process, get its ID
            cursor = db.execute('SELECT id FROM concepts WHERE name = ?', (concept_name,))
            concept_map[concept_name] = cursor.fetchone()[0]
    return concept_map[concept_name]

def letter_to_index(letter):
    """Convert letter answer (A, B, C, D) to index (0, 1, 2, 3)."""
    return ord(letter.upper()) - ord('A')

def load_questions(json_path=None):
    """Load questions from JSON file into database."""
    if not json_path:
        json_path = 'data/ml_questions_large.json'
    
    current_app.logger.info(f"Loading questions from {json_path}...")
    
    try:
        # Read questions from JSON file
        with open(json_path, 'r') as f:
            questions = json.load(f)
        
        current_app.logger.info(f"Found {len(questions)} questions in JSON file")
        
        # Get database connection
        db = get_db()
        
        # First, load existing concepts into our map
        concept_map = {}
        cursor = db.execute('SELECT id, name FROM concepts')
        for row in cursor.fetchall():
            concept_map[row[1]] = row[0]
        
        question_count = 0
        for question in questions:
            # Get or create concept
            concept_name = question.get('concept', 'General')
            concept_id = get_concept_id(db, concept_name, concept_map)
            
            # Convert letter answer to index
            correct_index = letter_to_index(question['correct'])
            
            # Convert options to JSON string
            options_json = json.dumps(question['options'])
            
            # Insert question
            try:
                cursor = db.execute('SELECT id FROM questions WHERE text = ?', (question['question'],))
                existing_question = cursor.fetchone()
                if not existing_question:
                    cursor = db.execute('''
                        INSERT INTO questions 
                        (text, options, correct_answer, explanation, difficulty, concept_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        question['question'],
                        options_json,
                        correct_index,
                        question.get('explanation', ''),
                        question.get('difficulty', 'medium'),
                        concept_id
                    ))
                    question_count += 1
                
                if question_count % 10 == 0:
                    current_app.logger.debug(f"Loaded {question_count} questions...")
            except sqlite3.IntegrityError as e:
                current_app.logger.warning(f"Skipping duplicate question: {question['question'][:50]}... ({str(e)})")
                continue
            except Exception as e:
                current_app.logger.error(f"Error loading question: {str(e)}")
                continue
        
        # Commit all changes
        db.commit()
        
        # Verify the data was loaded
        cursor = db.execute('SELECT COUNT(*) FROM concepts')
        final_concept_count = cursor.fetchone()[0]
        
        cursor = db.execute('SELECT COUNT(*) FROM questions')
        final_question_count = cursor.fetchone()[0]
        
        current_app.logger.info("\nVerification:")
        current_app.logger.info(f"- Concepts in database: {final_concept_count}")
        current_app.logger.info(f"- Questions in database: {final_question_count}")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error loading data: {str(e)}")
        db.rollback()
        return False

def setup_database(force=False):
    """Setup database and load questions."""
    try:
        # Check if database already exists and has data
        if database_exists() and not force:
            current_app.logger.info("Database already exists with data")
            return True
            
        # Initialize database
        current_app.logger.info("Initializing database...")
        if not init_db():
            return False
            
        # Load questions
        if load_questions():
            current_app.logger.info("Successfully loaded questions into database")
            load_questions('data/ml_questions_new.json')
            return True
        else:
            current_app.logger.error("Failed to load questions into database")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error setting up database: {str(e)}")
        return False

if __name__ == '__main__':
    # Create Flask app
    from ml_app import create_app
    app = create_app()
    with app.app_context():
        setup_database()
