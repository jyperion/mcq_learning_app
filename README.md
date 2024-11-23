# ML Interview Preparation Assistant

An interactive web application to help you prepare for machine learning interviews by providing adaptive questions and tracking your performance across different ML domains.

## Features

- Initial set of questions across various ML domains
- Dynamic question generation based on performance
- Interactive confidence tracking
- Visual performance dashboard
- Identification of strong and weak areas
- Integration with Ollama for AI-powered question generation

## Prerequisites

- Python 3.7+
- Ollama running locally
- Virtual environment (recommended)

## Installation

1. Clone the repository
2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Make sure Ollama is running locally
2. Start the Flask application:
```bash
python app.py
```
3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Select a domain from the dropdown menu
2. Answer the question in the text area
3. Rate your confidence level (1-10)
4. Submit your answer
5. View your performance in the dashboard
6. The application will automatically focus on your weak areas

## Domains Covered

- Machine Learning Basics
- Deep Learning
- Natural Language Processing
- Computer Vision

## Contributing

Feel free to open issues or submit pull requests for improvements.
