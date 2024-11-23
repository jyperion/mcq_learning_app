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

def load_questions(app):
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
                # Insert question
                cursor = db.execute('''
                    INSERT INTO questions 
                    (question, options, correct, explanation)
                    VALUES (?, ?, ?, ?)
                ''', (
                    question['question'],
                    json.dumps(question['options']),
                    question['correct'],
                    question['explanation']
                ))
                question_id = cursor.lastrowid
                question_count += 1
                
                # Link question to concept
                db.execute('''
                    INSERT INTO concept_questions 
                    (concept_id, question_id)
                    VALUES (?, ?)
                ''', (concept_id, question_id))
                
                if question_count % 10 == 0:
                    print(f"Loaded {question_count} questions...")
        
        # Commit all changes
        db.commit()
        
        # Verify the data was loaded
        cursor = db.execute('SELECT COUNT(*) as count FROM concepts')
        final_concept_count = cursor.fetchone()['count']
        
        cursor = db.execute('SELECT COUNT(*) as count FROM questions')
        final_question_count = cursor.fetchone()['count']
        
        print("\nVerification:")
        print(f"- Concepts in database: {final_concept_count}")
        print(f"- Questions in database: {final_question_count}")
        
        if final_concept_count == concept_count and final_question_count == question_count:
            print("\nSuccessfully loaded all concepts and questions!")
            print("\nSummary:")
            print(f"- Loaded {concept_count} concepts")
            print(f"- Loaded {question_count} questions")
            print("\nDatabase setup complete!")
        else:
            print("\nWarning: Mismatch in loaded data!")
            print(f"Expected: {concept_count} concepts, {question_count} questions")
            print(f"Found: {final_concept_count} concepts, {final_question_count} questions")
        
    except Exception as e:
        db.rollback()
        print(f"Error loading questions: {str(e)}")
        raise

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        if not database_exists(app):
            print("Initializing empty database")
            init_db()
            load_questions(app)
        else:
            print("Database already exists with questions loaded. Skipping initialization.")
            print("To force reinitialization, delete the database file and run this script again.")
