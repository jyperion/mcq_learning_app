import sqlite3
import json
import os

def check_database():
    db_path = 'instance/ml_app.sqlite'
    if not os.path.exists(db_path):
        print(f"Database file does not exist at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check questions
    cursor.execute('SELECT COUNT(*) as count FROM questions')
    question_count = cursor.fetchone()[0]
    print(f"Total questions: {question_count}")
    
    # Check concepts
    cursor.execute('SELECT COUNT(*) as count FROM concepts')
    concept_count = cursor.fetchone()[0]
    print(f"Total concepts: {concept_count}")
    
    # Check a sample question
    if question_count > 0:
        cursor.execute('''
            SELECT q.*, c.name as concept_name 
            FROM questions q 
            LEFT JOIN concepts c ON q.concept_id = c.id 
            LIMIT 1
        ''')
        sample = cursor.fetchone()
        print("\nSample question:")
        print(f"id: {sample['id']}")
        print(f"text: {sample['text']}")
        print(f"options: {json.loads(sample['options'])}")
        print(f"correct_answer: {sample['correct_answer']}")
        print(f"explanation: {sample['explanation']}")
        print(f"hint: {sample['hint']}")
        print(f"difficulty: {sample['difficulty']}")
        print(f"concept_id: {sample['concept_id']}")
        print(f"concept_name: {sample['concept_name']}")
    
    conn.close()

if __name__ == '__main__':
    check_database()
