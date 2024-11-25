# ML Interview Question Generator

A Flask-based web application for generating and managing machine learning interview questions using AI.

## Project Structure

```
ml-app/
├── ml_app/                      # Main application package
│   ├── __init__.py             # App factory and configuration
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── questions.py        # Question-related endpoints
│   │   └── feedback.py         # Feedback-related endpoints
│   ├── config/                 # Configuration files
│   │   ├── ml_interview_config.json    # ML interview configuration
│   │   └── uk_hr_config.json          # HR interview configuration
│   ├── database/               # Database management
│   │   ├── __init__.py
│   │   ├── db.py              # Database operations
│   │   └── schema.sql         # Database schema
│   ├── question_generation/    # Question generation logic
│   │   ├── __init__.py
│   │   ├── generator.py       # Core generation logic
│   │   ├── concepts.py        # ML concepts management
│   │   └── ollama.py         # Ollama API integration
│   ├── static/                # Static files
│   │   ├── css/
│   │   └── js/
│   └── templates/             # HTML templates
├── tests/                     # Test suite
│   ├── conftest.py           # Test configuration
│   ├── test_api/            
│   ├── test_database/
│   └── test_generator/
├── data/                      # Data files
│   └── ml_questions.json     # Seed questions
├── instance/                  # Instance-specific files
├── requirements/              # Dependencies
│   ├── base.txt              # Base requirements
│   ├── dev.txt               # Development requirements
│   └── prod.txt             # Production requirements
├── scripts/                   # Utility scripts
│   ├── setup_db.py          # Database setup
│   └── seed_data.py         # Data seeding
├── .env.example              # Environment variables example
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt          # Main requirements file
├── setup.py                 # Package setup
└── wsgi.py                  # WSGI entry point
```

## Features

- AI-powered question generation using Ollama (Qwen2.5 model)
- Multiple choice questions with detailed explanations
- Configurable question generation parameters
- Support for multiple domains (ML and HR interviews)
- Question quality validation and duplicate detection
- Concept-based categorization with 16 ML topics
- Progress tracking
- Async processing for better performance
- Comprehensive error handling and logging

## Configuration

The application uses JSON configuration files for different question domains:

1. ML Interview Configuration (`ml_app/config/ml_interview_config.json`):
   - 16 machine learning concept categories
   - Ollama model parameters
   - Question generation settings
   - Validation rules

2. HR Interview Configuration (`ml_app/config/uk_hr_config.json`):
   - HR-specific question categories
   - Custom generation parameters
   - Domain-specific validation

## Question Generation

Questions are generated with the following specifications:
- Format: Multiple Choice Questions (MCQ)
- Options: 4 choices (A, B, C, D)
- Components: Question, Options, Correct Answer, Detailed Explanation
- Batch Size: 5 questions per generation
- Context Window: 8192 tokens
- Generation Length: 4096 tokens

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```bash
   flask init-db
   ```

4. Start Ollama server:
   ```bash
   ollama serve
   ```

5. Pull the Qwen2.5 model:
   ```bash
   ollama pull qwen2.5
   ```

6. Run the application:
   ```bash
   flask run
   ```

## Question Generation Script

To generate questions:
```bash
python ml_app/question_generation/generate_questions.py --config ml_app/config/ml_interview_config.json --output data/ml_questions.json
```

Options:
- `--config`: Path to configuration file
- `--output`: Output JSON file
- `--test`: Run in test mode (generates fewer questions)
- `--concept`: Generate for specific concept only

## Development

1. Install development dependencies:
   ```bash
   pip install -r requirements/dev.txt
   ```

2. Run tests:
   ```bash
   pytest
   ```

3. Code formatting:
   ```bash
   black ml_app tests
   ```

## API Endpoints

- `GET /api/questions`: Get questions
- `POST /api/questions/recheck/<id>`: Recheck a question
- `POST /api/questions/<id>/feedback`: Submit feedback
- `DELETE /api/questions/<id>`: Delete a question

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
