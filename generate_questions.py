import json
import requests
import time

def query_ollama(prompt, model="llama3.2:latest"):
    """Query Ollama API with a prompt."""
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        print(f"Error querying Ollama: {str(e)}")
        return None

def generate_mcq(question):
    """Generate MCQ options and correct answer for a question."""
    prompt = f"""
    You are helping create a question bank for Large Language Model (LLM) interview preparation.
    For the following question, generate 4 multiple choice options (A, B, C, D) and indicate the correct answer.
    Also provide a brief explanation for the correct answer.
    Format the response exactly as shown in the example:

    Example format:
    OPTIONS:
    A: First option
    B: Second option
    C: Third option
    D: Fourth option
    CORRECT: A
    EXPLANATION: Brief explanation of why A is correct.

    Question: {question}
    """
    
    response = query_ollama(prompt)
    if not response:
        return None
    
    # Parse the response
    try:
        lines = response.split('\n')
        options = []
        correct = None
        explanation = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('A:'):
                options.append(line[2:].strip())
            elif line.startswith('B:'):
                options.append(line[2:].strip())
            elif line.startswith('C:'):
                options.append(line[2:].strip())
            elif line.startswith('D:'):
                options.append(line[2:].strip())
            elif line.startswith('CORRECT:'):
                correct = line.split(':')[1].strip()
            elif line.startswith('EXPLANATION:'):
                explanation = line.split(':')[1].strip()
        
        if len(options) == 4 and correct and explanation:
            return {
                "options": options,
                "correct": correct,
                "explanation": explanation
            }
    except Exception as e:
        print(f"Error parsing response: {str(e)}")
    
    return None

def identify_concept(question):
    """Identify the ML concept a question belongs to."""
    prompt = f"""
    You are categorizing questions for a Large Language Model (LLM) interview preparation platform.
    Identify which ONE of the following concepts this question belongs to:
    - Neural Networks and Deep Learning
    - Machine Learning Fundamentals
    - Natural Language Processing
    - Large Language Models (LLMs)
    - Retrieval-Augmented Generation (RAG)
    - Model Evaluation and Optimization
    - Transformer Architecture
    - Attention Mechanisms
    - Fine-tuning and Transfer Learning
    
    Important Notes:
    - RAG refers specifically to Retrieval-Augmented Generation, a technique used with LLMs
    - Focus on modern LLM-related concepts and architectures
    - Choose the most specific category that applies
    
    Question: {question}
    
    Respond with ONLY the concept name, nothing else.
    """
    
    response = query_ollama(prompt)
    if response:
        return response.strip()
    return "General ML"

def main():
    # Read questions from seed.txt
    with open('seed.txt', 'r') as f:
        content = f.read()
    
    # Split into questions (assuming each question is separated by blank lines)
    questions_raw = [q.strip() for q in content.split('\n\n') if q.strip()]
    
    # Filter out questions that don't end with question marks
    questions = [q for q in questions_raw if q.endswith('?')]
    
    # Initialize the questions database
    questions_db = {
        "concepts": {}
    }
    
    print(f"Processing {len(questions)} questions...")
    
    for i, question in enumerate(questions, 1):
        print(f"\nProcessing question {i}/{len(questions)}")
        
        # Identify the concept
        concept = identify_concept(question)
        print(f"Concept identified: {concept}")
        
        # Generate MCQ
        mcq_data = generate_mcq(question)
        
        if mcq_data:
            # Initialize concept if not exists
            if concept not in questions_db["concepts"]:
                questions_db["concepts"][concept] = {
                    "name": concept,
                    "description": f"Questions related to {concept}",
                    "questions": []
                }
            
            # Add question to the concept
            questions_db["concepts"][concept]["questions"].append({
                "question": question,
                "options": mcq_data["options"],
                "correct": mcq_data["correct"],
                "explanation": mcq_data["explanation"]
            })
            
            print("Successfully generated MCQ")
        else:
            print("Failed to generate MCQ")
        
        # Add a small delay to avoid overwhelming Ollama
        time.sleep(1)
    
    # Save to JSON file
    output_file = 'data/ml_questions.json'
    os.makedirs('data', exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(questions_db, f, indent=2)
    
    print(f"\nQuestions database saved to {output_file}")
    print("Summary:")
    for concept, data in questions_db["concepts"].items():
        print(f"- {concept}: {len(data['questions'])} questions")

if __name__ == "__main__":
    import os
    main()
