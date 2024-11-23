"""Parse seed file containing questions."""
from typing import Dict, List
import re

def parse_seed_file(file_path: str) -> Dict[str, List[Dict]]:
    """Parse a seed file containing questions and return them organized by concept."""
    questions_by_concept = {}
    current_concept = None
    current_question = None
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # Check for concept header
            if line.startswith('#'):
                current_concept = line[1:].strip()
                if current_concept not in questions_by_concept:
                    questions_by_concept[current_concept] = []
                continue
                
            # Parse question components
            if line.startswith('Q:'):
                # Save previous question if exists
                if current_question and current_concept:
                    questions_by_concept[current_concept].append(current_question)
                
                # Start new question
                current_question = {
                    'question': line[2:].strip(),
                    'options': {},
                    'correct': None,
                    'explanation': None
                }
            elif line.startswith(('A:', 'B:', 'C:', 'D:')):
                if current_question:
                    option = line[0]
                    current_question['options'][option] = line[2:].strip()
            elif line.startswith('CORRECT:'):
                if current_question:
                    current_question['correct'] = line[8:].strip()
            elif line.startswith('EXPLANATION:'):
                if current_question:
                    current_question['explanation'] = line[12:].strip()
    
    # Add the last question
    if current_question and current_concept:
        questions_by_concept[current_concept].append(current_question)
    
    return questions_by_concept
