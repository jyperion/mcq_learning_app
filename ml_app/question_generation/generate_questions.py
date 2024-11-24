import json
import requests
import time
import os
import asyncio
import aiohttp
from typing import List, Dict, Any
import argparse
import difflib

# Define valid concepts at module level
VALID_CONCEPTS = {
    "Neural Networks and Deep Learning": [
        "neural network", "deep learning", "cnn", "rnn", "lstm", "activation function", 
        "backpropagation", "transformer", "attention mechanism", "bert", "gpt"
    ],
    "Machine Learning Fundamentals": [
        "regression", "classification", "clustering", "dimensionality reduction", 
        "feature selection", "cross validation", "bias variance", "overfitting", 
        "underfitting", "ensemble methods", "decision trees", "random forest", "svm"
    ],
    "Large Language Models": [
        "llm", "language model", "transformer", "attention mechanism", "prompt engineering", 
        "fine-tuning", "few-shot learning", "zero-shot learning", "tokenization", 
        "embedding", "bert", "gpt", "prompt tuning"
    ],
    "Model Optimization": [
        "gradient descent", "optimization", "regularization", "hyperparameter", 
        "learning rate", "batch size", "momentum", "adam", "rmsprop", "dropout", 
        "batch normalization", "early stopping"
    ],
    "Model Evaluation": [
        "metrics", "evaluation", "validation", "testing", "performance measure", 
        "confusion matrix", "precision", "recall", "f1 score", "roc curve", "auc", 
        "cross validation", "holdout"
    ],
    "MLOps": [
        "model deployment", "model monitoring", "model versioning", "ci/cd", 
        "feature store", "model registry", "model serving", "a/b testing", 
        "model drift", "data drift", "mlflow", "kubeflow"
    ]
}

async def query_ollama_async(prompt: str, model: str = "qwen2.5:latest", session: aiohttp.ClientSession = None) -> str:
    """Query Ollama API asynchronously with a prompt."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "num_ctx": 4096,
            "num_predict": 512,
            "repeat_penalty": 1.1,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "tfs_z": 1.0,
            "mirostat": 2,
            "mirostat_tau": 5.0,
            "mirostat_eta": 0.1,
            "seed": 42
        }
    }
    
    try:
        if session is None:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["response"]
                    else:
                        print(f"Error querying Ollama: {response.status}")
                        return None
        else:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["response"]
                else:
                    print(f"Error querying Ollama: {response.status}")
                    return None
    except Exception as e:
        print(f"Exception in query_ollama_async: {str(e)}")
        return None

class OllamaQuerier:
    """Class to manage Ollama queries with concurrency control."""
    def __init__(self, max_concurrent_queries: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent_queries)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query(self, prompt: str, model: str = "qwen2.5:latest", max_retries: int = 3) -> str:
        """Query Ollama API with concurrency control."""
        async with self.semaphore:
            for attempt in range(max_retries):
                try:
                    result = await query_ollama_async(prompt, model, self.session)
                    if result:
                        return result
                    await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(1 * (attempt + 1))
            return None

async def generate_complete_questions(concept: str, num_questions: int, querier: OllamaQuerier, existing_questions: List[Dict[str, Any]] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
    """Generate complete questions with options and explanations in a single batch."""
    existing_questions = existing_questions or []
    existing_question_texts = [q['question'] for q in existing_questions]
    
    # Format existing questions as context
    existing_context = ""
    if existing_questions:
        existing_context = "\nAVOID these existing questions:\n"
        for i, q in enumerate(existing_questions, 1):  
            existing_context += f"- {q['question']}\n"

    prompt = f"""You are an expert in machine learning, particularly in {concept}.
    Generate exactly {num_questions} complete multiple choice questions.{existing_context}

    For each question, provide:
    1. A challenging question about {concept}
    2. Four multiple choice options (A, B, C, D)
    3. The correct answer
    4. A detailed explanation

    Guidelines:
    - Questions should test understanding and problem-solving
    - Make all options plausible but only one correct
    - Include detailed explanations
    - Cover different aspects of {concept}
    - Generate UNIQUE questions, different from the existing ones
    - Each question should focus on a different aspect or subtopic
    - IMPORTANT: Generate EXACTLY {num_questions} questions, no more, no less

    Format each question exactly like this:

    Q1. What is the most effective approach to handle vanishing gradients in deep neural networks?
    A) Use ReLU activation functions
    B) Increase the learning rate
    C) Remove all activation functions
    D) Add more layers
    Correct: A
    Explanation: ReLU activation functions help prevent vanishing gradients because they do not saturate for positive values...

    Q2. [Next question follows the same format]

    Remember: Generate EXACTLY {num_questions} complete questions."""

    all_valid_questions = []
    total_attempts = 0
    
    while len(all_valid_questions) < num_questions and total_attempts < max_retries:
        total_attempts += 1
        remaining = num_questions - len(all_valid_questions)
        
        try:
            response = await querier.query(prompt)
            questions = []
            current_question = {}
            
            # Split response into lines and process
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # New question starts
                if line.startswith('Q') and '.' in line:
                    if current_question and len(current_question.get('options', [])) == 4:
                        questions.append(current_question)
                    current_question = {'options': []}
                    current_question['question'] = line.split('.', 1)[1].strip()
                
                # Option line
                elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                    current_question['options'].append(line)
                
                # Correct answer line
                elif line.lower().startswith('correct:'):
                    correct_letter = line.split(':')[1].strip().upper()
                    if correct_letter in ['A', 'B', 'C', 'D']:
                        for opt in current_question['options']:
                            if opt.startswith(f"{correct_letter})"):
                                current_question['correct'] = opt
                                break
                
                # Explanation line
                elif line.lower().startswith('explanation:'):
                    explanation = [line.split(':', 1)[1].strip()]
                    # Collect multi-line explanation
                    while i + 1 < len(lines) and not lines[i + 1].startswith(('Q', 'A)', 'B)', 'C)', 'D)', 'Correct:')):
                        i += 1
                        explanation.append(lines[i])
                    current_question['explanation'] = ' '.join(explanation)
                
                i += 1
            
            # Add the last question if complete
            if current_question and len(current_question.get('options', [])) == 4:
                questions.append(current_question)
            
            # Validate questions and check for duplicates
            for q in questions:
                # Basic validation with more lenient requirements
                if not (len(q.get('options', [])) == 4 and
                       'question' in q and len(q['question']) >= 15 and  # Reduced minimum length
                       'correct' in q and q['correct'] in q['options'] and
                       'explanation' in q and len(q['explanation']) >= 50):  # Reduced minimum length
                    continue
                
                # Check for duplicates using fuzzy matching
                is_duplicate = False
                for existing_q in existing_question_texts:
                    similarity = difflib.SequenceMatcher(None, q['question'].lower(), existing_q.lower()).ratio()
                    if similarity > 0.85:  # Slightly higher threshold to allow more questions
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_valid_questions.append(q)
                    existing_question_texts.append(q['question'])  # Add to existing questions immediately
            
            if len(all_valid_questions) >= num_questions:
                return all_valid_questions[:num_questions]
            
            # If we didn't get enough questions, wait briefly before retrying
            if total_attempts < max_retries:
                await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Error generating questions (attempt {total_attempts}/{max_retries}): {str(e)}")
            if total_attempts < max_retries:
                await asyncio.sleep(1)
    
    return all_valid_questions

async def _generate_mcq_internal(concept: str, num_questions: int, querier: OllamaQuerier) -> List[Dict[str, Any]]:
    """Generate MCQs in batches of 10."""
    print(f"Generating {num_questions} questions for {concept}...")
    
    all_questions = []
    batch_size = 10
    num_batches = (num_questions + batch_size - 1) // batch_size
    
    for batch in range(num_batches):
        remaining = min(batch_size, num_questions - len(all_questions))
        batch_attempt = 1
        max_batch_attempts = 3
        
        while batch_attempt <= max_batch_attempts and remaining > 0:
            print(f"Generating batch {batch + 1}/{num_batches} (attempt {batch_attempt}, need {remaining} questions)...")
            
            # Generate next batch with context of existing questions
            batch_questions = await generate_complete_questions(
                concept, 
                remaining * 2,  # Ask for more questions than needed to increase chances of getting enough valid ones
                querier, 
                existing_questions=all_questions
            )
            
            if not batch_questions:
                print(f"Failed to generate batch {batch + 1} (attempt {batch_attempt})")
                batch_attempt += 1
                await asyncio.sleep(1)
                continue
            
            all_questions.extend(batch_questions)
            print(f"Generated {len(batch_questions)} valid questions in batch {batch + 1}")
            
            # Check if we have enough questions
            if len(batch_questions) >= remaining:
                break
            
            # If we don't have enough questions, update remaining and try again
            remaining = remaining - len(batch_questions)
            batch_attempt += 1
            await asyncio.sleep(1)
        
        # Small delay between batches
        if batch < num_batches - 1:
            await asyncio.sleep(1)
    
    print(f"Generated total of {len(all_questions)} valid questions")
    return all_questions[:num_questions]

async def generate_mcq_async(concept: str, num_questions: int = 1, querier: OllamaQuerier = None) -> List[Dict[str, Any]]:
    """Generate multiple-choice questions asynchronously."""
    if querier is None:
        async with OllamaQuerier() as querier:
            return await _generate_mcq_internal(concept, num_questions, querier)
    else:
        return await _generate_mcq_internal(concept, num_questions, querier)

def sanitize_json_string(s: str) -> str:
    """Sanitize a string to be valid in JSON."""
    if not s:
        return ""
    # Remove any potential JSON-breaking characters
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    s = s.replace('\b', '\\b')
    s = s.replace('\f', '\\f')
    return s

def validate_question_data(data: Dict[str, Any]) -> bool:
    """Validate question data against schema requirements."""
    try:
        # Check required fields
        required_fields = ['question', 'options', 'correct', 'explanation']
        if not all(field in data for field in required_fields):
            missing = [f for f in required_fields if f not in data]
            print(f"Missing required fields: {missing}")
            return False

        # Validate question
        if not isinstance(data['question'], str) or len(data['question']) < 20:
            print("Question is too short or invalid")
            return False

        # Validate options
        if not isinstance(data['options'], list) or len(data['options']) != 4:
            print("Options must be a list of exactly 4 items")
            return False

        prefixes = ['A)', 'B)', 'C)', 'D)']
        for i, opt in enumerate(data['options']):
            if not isinstance(opt, str) or not opt.startswith(prefixes[i]):
                print(f"Option {i+1} must be a string starting with {prefixes[i]}")
                return False

        # Validate correct answer
        if data['correct'] not in data['options']:
            print("Correct answer must match exactly one of the options")
            return False

        # Validate explanation
        if not isinstance(data['explanation'], str) or len(data['explanation']) < 100:
            print("Explanation must be at least 100 characters")
            return False

        return True
    except Exception as e:
        print(f"Validation error: {str(e)}")
        return False

def load_existing_questions(filepath: str) -> dict:
    """Load existing questions from file if it exists."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error loading {filepath}, starting fresh")
    return {
        "concepts": {concept: {"name": concept, "description": f"Questions related to {concept}", "questions": []} 
                    for concept in VALID_CONCEPTS.keys()}
    }

def is_duplicate_question(question: dict, existing_questions: list) -> bool:
    """Check if a question is a duplicate."""
    for existing in existing_questions:
        # Check for exact matches
        if question['question'] == existing['question']:
            return True
        # Check for similar questions (80% similarity)
        if len(question['question']) > 0 and len(existing['question']) > 0:
            similarity = difflib.SequenceMatcher(None, 
                question['question'].lower(), 
                existing['question'].lower()
            ).ratio()
            if similarity > 0.8:
                return True
    return False

def main():
    """Main function to generate ML interview questions."""
    parser = argparse.ArgumentParser(description='Generate ML interview questions')
    parser.add_argument('--questions-per-concept', type=int, default=10,
                      help='Number of questions to generate per concept')
    parser.add_argument('--output', type=str, default='data/ml_questions.json',
                      help='Output file path')
    parser.add_argument('--test', action='store_true',
                      help='Test mode: generate only 2 questions per concept')
    args = parser.parse_args()

    num_questions = 2 if args.test else args.questions_per_concept
    print(f"Generating {num_questions} questions per concept...")

    # Load existing questions
    questions_db = load_existing_questions(args.output)
    
    async def generate_all_questions():
        async with OllamaQuerier(max_concurrent_queries=3) as querier:
            for concept in VALID_CONCEPTS.keys():
                print(f"\nGenerating questions for: {concept}")
                existing_questions = questions_db["concepts"][concept]["questions"]
                questions_needed = num_questions - len(existing_questions)
                
                if questions_needed <= 0:
                    print(f"Already have enough questions for {concept}")
                    continue
                
                questions = await generate_mcq_async(concept, questions_needed, querier)
                new_questions = []
                
                for q in questions:
                    if not is_duplicate_question(q, existing_questions):
                        new_questions.append(q)
                    else:
                        print("Skipping duplicate question")
                
                questions_db["concepts"][concept]["questions"].extend(new_questions)
                print(f"Generated {len(new_questions)} new questions")
                # Small delay between concepts to avoid overloading
                await asyncio.sleep(1)
    
    try:
        asyncio.run(generate_all_questions())
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        
        # Save to JSON file
        with open(args.output, "w") as f:
            json.dump(questions_db, f, indent=2)
        
        print("\nSummary:")
        total_questions = 0
        for concept, data in questions_db["concepts"].items():
            num_questions = len(data["questions"])
            total_questions += num_questions
            print(f"- {concept}: {num_questions} questions")
        print(f"\nTotal questions generated: {total_questions}")
        print(f"Questions saved to: {args.output}")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
