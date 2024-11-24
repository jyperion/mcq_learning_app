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

- AI-powered question generation using Ollama
- Multiple choice question format
- Question quality management (flag, update, delete)
- Concept-based categorization
- Progress tracking
- Async processing for better performance

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

5. Run the application:
   ```bash
   flask run
   ```

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
