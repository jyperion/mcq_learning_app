import json
import sqlite3
import os
from flask import Flask
from ml_app import create_app
from ml_app.database.db import init_db, get_db

def database_exists(app):
    """Check if database exists and has data."""
    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        return False
    
    try:
        db = sqlite3.connect(db_path)
        cursor = db.cursor()
        
        # Check if tables exist and have data
        cursor.execute("SELECT COUNT(*) FROM questions")
        question_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM concepts")
        concept_count = cursor.fetchone()[0]
        
        print(f"Found {concept_count} concepts and {question_count} questions in database")
        
        cursor.close()
        db.close()
        
        return question_count > 0 and concept_count > 0
    except sqlite3.Error as e:
        print(f"Error checking database: {str(e)}")
        return False

def load_questions():
    """Load questions from JSON file into database."""
    print("Loading questions from JSON file...")
    # Read questions from JSON file
    with open('data/ml_questions.json', 'r') as f:
        data = json.load(f)
    
    print(f"Found {len(data['concepts'])} concepts in JSON file")
    
    # Get database connection
    db = get_db()
    
    try:
        # Insert concepts and questions
        concept_count = 0
        question_count = 0
        
        for concept_name, concept_data in data['concepts'].items():
            print(f"Loading concept: {concept_name}")
            # Add concept
            cursor = db.execute(
                'INSERT INTO concepts (name, description) VALUES (?, ?)',
                (concept_data['name'], concept_data.get('description', ''))
            )
            concept_id = cursor.lastrowid
            concept_count += 1
            
            # Add questions for this concept
            for question in concept_data['questions']:
                # Convert options list to pipe-separated string
                options_str = '|'.join(question['options'])
                
                # Insert question
                cursor = db.execute('''
                    INSERT INTO questions 
                    (text, options, correct_answer, explanation, difficulty, hint)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    question['question'],
                    options_str,
                    question['correct'],
                    question.get('explanation', ''),
                    question.get('difficulty', 'medium'),
                    question.get('hint', '')
                ))
                question_id = cursor.lastrowid
                question_count += 1
                
                # Link question to concept
                db.execute('''
                    INSERT INTO question_concepts 
                    (question_id, concept_id)
                    VALUES (?, ?)
                ''', (question_id, concept_id))
                
                if question_count % 10 == 0:
                    print(f"Loaded {question_count} questions...")
        
        # Commit all changes
        db.commit()
        
        # Verify the data was loaded
        cursor = db.execute('SELECT COUNT(*) FROM concepts')
        final_concept_count = cursor.fetchone()[0]
        
        cursor = db.execute('SELECT COUNT(*) FROM questions')
        final_question_count = cursor.fetchone()[0]
        
        print("\nVerification:")
        print(f"- Concepts in database: {final_concept_count}")
        print(f"- Questions in database: {final_question_count}")
        
        return True
        
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        db.rollback()
        return False

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Check if database already exists and has data
        if database_exists(app):
            print("Database already exists with data")
        else:
            print("Initializing database...")
            init_db()
            if load_questions():
                print("Successfully loaded questions into database")
            else:
                print("Failed to load questions into database")
