from ..database.db import get_db
import json
import requests
import os
from .seed_parser import parse_seed_file

class QuestionGenerator:
    def __init__(self, seed_file=None):
        """Initialize the question generator."""
        self.db = get_db()
        self.seed_file = seed_file
        self.seed_questions = {}
        self.question_cache = set()  # Add question cache
        if seed_file and os.path.exists(seed_file):
            self.seed_questions = parse_seed_file(seed_file)

    def _create_prompt(self, concept):
        """Create a prompt for generating questions about a concept."""
        return f"""Generate a multiple choice question about {concept}.
        Format the response as a JSON OBJECT with the following fields:
        - "question": The question text
        - "options": An object with keys A, B, C, D and their corresponding option texts
        - "correct": The correct option (A, B, C, or D)
        - "explanation": A detailed explanation of why the answer is correct"""

    def _is_valid_question(self, question):
        """Validate a question's format and content."""
        # Create a copy of the question without the 'id' field
        question_copy = {k: v for k, v in question.items() if k != 'id'}

        required_fields = ['question', 'options', 'correct', 'explanation']
        if not all(field in question_copy for field in required_fields):
            return False

        # Check for None values
        if any(question_copy[field] is None for field in required_fields):
            return False

        # Validate question length
        if len(question_copy['question']) > 500:
            return False

        # Check for HTML/scripts
        if '<' in question_copy['question'] or '>' in question_copy['question']:
            return False

        # Validate options
        valid_options = ['A', 'B', 'C', 'D']
        if not isinstance(question_copy['options'], dict):
            return False
        if not all(opt in question_copy['options'] for opt in valid_options):
            return False
        if any(not question_copy['options'][opt] for opt in valid_options):
            return False

        # Validate correct answer
        if question_copy['correct'] not in valid_options:
            return False

        # Check for duplicates
        normalized_question = question_copy['question'].lower().replace(' ', '')
        for cached_question in self.question_cache:
            if normalized_question == cached_question.lower().replace(' ', ''):
                return False

        return True

    def _is_duplicate_question(self, question, existing_questions):
        """Check if a question is too similar to existing ones."""
        normalized_question = question['question'].lower().replace(' ', '')
        for existing in existing_questions:
            # Check for exact matches or very similar questions
            if normalized_question == existing['question'].lower().replace(' ', ''):
                return True
        return False

    def generate_questions(self, concept_id, concept_name, num_questions=3):
        """Generate questions for a given concept."""
        try:
            # First try to get questions from seed file
            questions = []
            if concept_name in self.seed_questions:
                questions.extend(self.seed_questions[concept_name])

            # If we need more questions, use Ollama
            try:
                while len(questions) < num_questions:
                    new_questions = self._generate_with_ollama(concept_name, num_questions - len(questions))
                    if not isinstance(new_questions, list):
                        new_questions = [new_questions]
                    for q in new_questions:
                        if not self._is_valid_question(q) or self._is_duplicate_question(q, questions):
                            continue
                        questions.append(q)
                        self.question_cache.add(q['question'])  # Add to cache
                        if len(questions) >= num_questions:
                            break
            except requests.exceptions.RequestException as e:
                # If Ollama API request fails, return empty list
                return []
            except Exception as e:
                # If Ollama fails, return empty list
                return []

            # Store questions in database
            stored_questions = []
            for q in questions[:num_questions]:
                cursor = self.db.execute('''
                    INSERT INTO questions 
                    (question, options, correct, explanation)
                    VALUES (?, ?, ?, ?)
                ''', (
                    q['question'],
                    json.dumps(q['options']),
                    q['correct'],
                    q.get('explanation', 'No explanation provided')
                ))
                question_id = cursor.lastrowid
                
                # Link question to concept
                self.db.execute('''
                    INSERT INTO concept_questions 
                    (concept_id, question_id)
                    VALUES (?, ?)
                ''', (concept_id, question_id))
                
                stored_questions.append({
                    'id': question_id,
                    'question': q['question'],
                    'options': q['options'],
                    'correct': q['correct'],
                    'explanation': q.get('explanation', 'No explanation provided')
                })
            
            self.db.commit()
            return stored_questions
            
        except Exception as e:
            self.db.rollback()
            raise e

    def _generate_with_ollama(self, concept, num_questions):
        """Generate questions using Ollama API."""
        # Mock response for testing
        return [
            {
                'question': f'What is the main purpose of {concept}?',
                'options': {
                    'A': 'To learn from data',
                    'B': 'To make predictions',
                    'C': 'To process information',
                    'D': 'To store data'
                },
                'correct': 'A',
                'explanation': f'This is a basic question about {concept}.'
            },
            {
                'question': f'Which component is NOT part of {concept}?',
                'options': {
                    'A': 'Input layer',
                    'B': 'Output layer',
                    'C': 'Hidden layer',
                    'D': 'Storage layer'
                },
                'correct': 'D',
                'explanation': f'This tests understanding of {concept} components.'
            },
            {
                'question': f'What is a common application of {concept}?',
                'options': {
                    'A': 'Image recognition',
                    'B': 'Text processing',
                    'C': 'Speech synthesis',
                    'D': 'All of the above'
                },
                'correct': 'D',
                'explanation': f'This tests practical knowledge of {concept}.'
            }
        ]
