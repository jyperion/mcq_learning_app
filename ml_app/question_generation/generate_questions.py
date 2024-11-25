import json
import requests
import time
import os
import asyncio
import aiohttp
from typing import List, Dict, Any
import argparse
import difflib
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path: str = None):
        """Initialize configuration from JSON file."""
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.valid_concepts = config['valid_concepts']
        self.ollama_config = config['ollama_config']
        self.question_gen_config = config['question_gen_config']
    
    def get_concept_keywords(self, concept: str) -> List[str]:
        """Get keywords for a specific concept."""
        return self.valid_concepts.get(concept, [])
    
    def get_all_concepts(self) -> List[str]:
        """Get list of all valid concepts."""
        return list(self.valid_concepts.keys())
    
    def is_valid_concept(self, concept: str) -> bool:
        """Check if a concept is valid."""
        return concept in self.valid_concepts

async def query_ollama_async(prompt: str, model: str = None, session: aiohttp.ClientSession = None, config: Config = None) -> str:
    """Query Ollama API asynchronously with a prompt."""
    if config is None:
        raise ValueError("Config is required")
    
    data = {
        "model": model or config.ollama_config["default_model"],
        "prompt": prompt,
        "stream": False,
        "options": config.ollama_config["generation_params"]
    }
    
    try:
        if session is None:
            async with aiohttp.ClientSession() as session:
                async with session.post(config.ollama_config["url"], json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["response"]
                    else:
                        logger.error(f"Error querying Ollama: {response.status}")
                        return None
        else:
            async with session.post(config.ollama_config["url"], json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["response"]
                else:
                    logger.error(f"Error querying Ollama: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Exception in query_ollama_async: {str(e)}")
        return None

class OllamaQuerier:
    def __init__(self, config: Config):
        """Initialize with configuration."""
        self.config = config
        self.url = config.ollama_config['url']
        self.model = config.ollama_config['default_model']
        self.generation_params = config.ollama_config['generation_params']
        self.session = None
        self.semaphore = asyncio.Semaphore(config.question_gen_config["max_concurrent_queries"])
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def query(self, prompt: str, model: str = None) -> str:
        """Query Ollama API with concurrency control."""
        if model is None:
            model = self.model
        
        async with self.semaphore:
            for attempt in range(self.config.question_gen_config["max_retries"]):
                try:
                    data = {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": self.generation_params
                    }
                    
                    async with self.session.post(self.url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            return result["response"]
                        else:
                            logger.error(f"Error querying Ollama: {response.status}")
                            return None
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == self.config.question_gen_config["max_retries"] - 1:
                        raise
                    await asyncio.sleep(1 * (attempt + 1))
            return None

async def generate_complete_questions(concept: str, num_questions: int, querier: OllamaQuerier, existing_questions: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Generate complete questions with options and explanations in a single batch."""
    if existing_questions is None:
        existing_questions = []
    
    # Format existing questions as context
    existing_context = ""
    if existing_questions:
        existing_context = "\n\nExisting questions to avoid duplicates:\n"
        for i, q in enumerate(existing_questions[-5:], 1):  # Only show last 5 questions as context
            existing_context += f"- {q['question']}\n"

    # Use question format from config
    prompt = querier.config.question_gen_config["question_format"].format(
        concept=concept,
        num_questions=min(num_questions, 5),  # Limit to 5 questions per batch for better quality
        existing_context=existing_context
    )

    # Get response from model
    try:
        response = await querier.query(prompt)
        if not response:
            logger.error("Empty response from model")
            return []
        
        # Extract questions from response
        questions = []
        current_question = {}
        current_field = None
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # New question starts with Q
            if line.startswith('Q') and '. ' in line:
                if current_question:
                    if validate_question_data(current_question, querier.config):
                        questions.append(current_question)
                    else:
                        logger.debug(f"Question failed validation: {current_question}")
                current_question = {
                    'question': line.split('. ', 1)[1].strip(),
                    'options': [],
                    'concept': concept
                }
                current_field = 'options'
            
            # Option line
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                if current_field == 'options':
                    current_question['options'].append(line[3:].strip())
            
            # Correct answer line
            elif line.startswith('Correct:'):
                current_field = 'correct'
                answer = line.split(':', 1)[1].strip()
                current_question['correct'] = answer
            
            # Explanation line
            elif line.startswith('Explanation:'):
                current_field = 'explanation'
                current_question['explanation'] = line.split(':', 1)[1].strip()
            
            # Continuation of explanation
            elif current_field == 'explanation' and 'explanation' in current_question:
                current_question['explanation'] += ' ' + line
        
        # Add last question if valid
        if current_question:
            if validate_question_data(current_question, querier.config):
                questions.append(current_question)
            else:
                logger.debug(f"Last question failed validation: {current_question}")
        
        logger.info(f"Generated {len(questions)} valid questions out of {min(num_questions, 5)} requested")
        return questions
    
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        return []

def validate_question_data(data: Dict[str, Any], config: Config) -> bool:
    """Validate question data against schema requirements."""
    try:
        # Check required fields
        required_fields = ['question', 'options', 'correct', 'explanation']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.debug(f"Missing required fields: {missing_fields}")
            return False
        
        # Validate question
        if not isinstance(data['question'], str):
            logger.debug("Question is not a string")
            return False
        if len(data['question']) < 15:
            logger.debug("Question is too short")
            return False
        
        # Validate options
        if not isinstance(data['options'], list):
            logger.debug("Options is not a list")
            return False
        if len(data['options']) != 4:
            logger.debug(f"Wrong number of options: {len(data['options'])}")
            return False
        
        # Validate each option is non-empty
        empty_options = [i for i, opt in enumerate(data['options']) if not isinstance(opt, str) or len(opt.strip()) == 0]
        if empty_options:
            logger.debug(f"Empty options at indices: {empty_options}")
            return False
        
        # Validate correct answer
        if not isinstance(data['correct'], str):
            logger.debug("Correct answer is not a string")
            return False
        if data['correct'] not in ['A', 'B', 'C', 'D']:
            logger.debug(f"Invalid correct answer: {data['correct']}")
            return False
        
        # Validate explanation
        if not isinstance(data['explanation'], str):
            logger.debug("Explanation is not a string")
            return False
        if len(data['explanation']) < 50:
            logger.debug("Explanation is too short")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating question data: {str(e)}")
        return False

async def generate_mcq_async(concept: str, num_questions: int = 1, querier: OllamaQuerier = None, config: Config = None) -> List[Dict[str, Any]]:
    """Generate multiple-choice questions asynchronously."""
    if config is None:
        raise ValueError("Config is required")
    
    if querier is None:
        async with OllamaQuerier(config) as querier:
            return await _generate_mcq_internal(concept, num_questions, querier)
    return await _generate_mcq_internal(concept, num_questions, querier)

def is_duplicate_question(question: dict, existing_questions: list, config: Config) -> bool:
    """Check if a question is a duplicate using fuzzy string matching."""
    if not existing_questions:
        return False
    
    new_q = question['question'].lower()
    for existing in existing_questions:
        existing_q = existing['question'].lower()
        similarity = difflib.SequenceMatcher(None, new_q, existing_q).ratio()
        if similarity > config.question_gen_config["similarity_threshold"]:
            return True
    return False

async def _generate_mcq_internal(concept: str, num_questions: int, querier: OllamaQuerier) -> List[Dict[str, Any]]:
    """Generate MCQs in batches."""
    logger.info(f"Generating {num_questions} questions for {concept}...")
    
    batch_size = querier.config.question_gen_config["batch_size"]
    all_questions = []
    num_batches = (num_questions + batch_size - 1) // batch_size
    
    for batch in range(num_batches):
        remaining = min(batch_size, num_questions - len(all_questions))
        if remaining <= 0:
            break
        
        batch_attempt = 1
        max_batch_attempts = querier.config.question_gen_config["max_retries"]
        
        while batch_attempt <= max_batch_attempts and remaining > 0:
            logger.info(f"Generating batch {batch + 1}/{num_batches} (attempt {batch_attempt}, need {remaining} questions)...")
            
            # Generate next batch with context of existing questions
            batch_questions = await generate_complete_questions(
                concept, 
                remaining * 2,  # Ask for more questions than needed to increase chances of getting enough valid ones
                querier,
                existing_questions=all_questions
            )
            
            if not batch_questions:
                logger.error(f"Failed to generate batch {batch + 1} (attempt {batch_attempt})")
                batch_attempt += 1
                await asyncio.sleep(1)
                continue
            
            # Filter out duplicates and invalid questions
            valid_questions = []
            for q in batch_questions:
                if not validate_question_data(q, querier.config):
                    continue
                if not is_duplicate_question(q, all_questions + valid_questions, querier.config):
                    valid_questions.append(q)
            
            all_questions.extend(valid_questions)
            logger.info(f"Generated {len(valid_questions)} valid questions in batch {batch + 1}")
            
            # Check if we have enough questions
            if len(all_questions) >= num_questions:
                break
            
            remaining = num_questions - len(all_questions)
            batch_attempt += 1
        
        # Small delay between batches
        if batch < num_batches - 1:
            await asyncio.sleep(1)
    
    logger.info(f"Generated total of {len(all_questions)} valid questions")
    return all_questions[:num_questions]

def load_existing_questions(filepath: str) -> List[Dict]:
    """Load existing questions from a JSON file."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error loading existing questions: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error loading questions: {str(e)}")
    return []

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

def main():
    """Main function to generate practice questions."""
    parser = argparse.ArgumentParser(description='Generate practice questions')
    parser.add_argument('--questions-per-concept', type=int, default=10,
                      help='Number of questions to generate per concept')
    parser.add_argument('--output', type=str, default='questions.json',
                      help='Output file path')
    parser.add_argument('--test', action='store_true',
                      help='Test mode: generate only 2 questions per concept')
    parser.add_argument('--config', type=str,
                      help='Path to custom configuration file', default='ml_app/config/default_question_gen_config.json')
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = Config(args.config)
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return
    
    num_questions = 2 if args.test else args.questions_per_concept
    existing_questions = load_existing_questions(args.output) or []
    
    # Organize existing questions by concept
    questions_by_concept = {}
    for q in existing_questions:
        if isinstance(q, dict):  # Ensure q is a dictionary
            concept = q.get('concept', 'Unknown')
            if concept not in questions_by_concept:
                questions_by_concept[concept] = []
            questions_by_concept[concept].append(q)
    
    async def generate_all():
        async with OllamaQuerier(config) as querier:
            all_questions = []
            concepts_to_generate = config.get_all_concepts()
            
            for concept in concepts_to_generate:
                logger.info(f"\nGenerating {num_questions} questions for: {concept}")
                existing = questions_by_concept.get(concept, [])
                questions_needed = max(0, num_questions - len(existing))
                
                if questions_needed == 0:
                    logger.info(f"Already have enough questions for {concept}")
                    all_questions.extend(existing)
                    continue
                
                try:
                    questions = await _generate_mcq_internal(concept, questions_needed, querier)
                    if questions:
                        # Add concept to each question
                        for q in questions:
                            q['concept'] = concept
                        all_questions.extend(existing)  # Keep existing questions
                        all_questions.extend(questions)  # Add new questions
                        logger.info(f"Generated {len(questions)} new questions for {concept}")
                    else:
                        logger.warning(f"Failed to generate questions for {concept}")
                        all_questions.extend(existing)  # Keep existing questions even if generation fails
                except Exception as e:
                    logger.error(f"Error generating questions for {concept}: {str(e)}")
                    all_questions.extend(existing)  # Keep existing questions on error
                
                # Small delay between concepts to avoid overloading
                await asyncio.sleep(1)
            
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            
            # Save all questions to file
            with open(args.output, 'w') as f:
                json.dump(all_questions, f, indent=2)
            
            # Print summary
            logger.info("\nGeneration Summary:")
            concept_counts = {}
            for q in all_questions:
                concept = q.get('concept', 'Unknown')
                concept_counts[concept] = concept_counts.get(concept, 0) + 1
            
            logger.info("\nQuestions per concept:")
            for concept, count in concept_counts.items():
                logger.info(f"- {concept}: {count} questions")
            logger.info(f"\nTotal questions: {len(all_questions)}")
            logger.info(f"Questions saved to: {args.output}")
    
    try:
        asyncio.run(generate_all())
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
