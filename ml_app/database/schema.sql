-- Initialize the database
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS question_concepts;
DROP TABLE IF EXISTS user_answers;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS question_feedback;

-- Create concepts table
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create questions table
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    options TEXT NOT NULL,  -- Pipe-separated options
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
    hint TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create question_concepts junction table
CREATE TABLE question_concepts (
    question_id INTEGER,
    concept_id INTEGER,
    PRIMARY KEY (question_id, concept_id),
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE
);

-- Create sessions table
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'abandoned'))
);

-- Create user_answers table
CREATE TABLE user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_taken INTEGER NOT NULL,  -- in seconds
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
);

-- Create question_feedback table
CREATE TABLE question_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    feedback TEXT NOT NULL,
    type TEXT DEFAULT 'general' CHECK(type IN ('general', 'error', 'improvement', 'flag')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_question_concepts_concept ON question_concepts(concept_id);
CREATE INDEX idx_question_concepts_question ON question_concepts(question_id);
CREATE INDEX idx_user_answers_session ON user_answers(session_id);
CREATE INDEX idx_user_answers_question ON user_answers(question_id);
CREATE INDEX idx_question_feedback_question ON question_feedback(question_id);

-- Insert some initial concepts
INSERT INTO concepts (name, description) VALUES
    ('Machine Learning Basics', 'Fundamental concepts of machine learning'),
    ('Deep Learning', 'Neural networks and deep learning architectures'),
    ('Natural Language Processing', 'Text processing and language models'),
    ('Computer Vision', 'Image processing and visual recognition'),
    ('Model Evaluation', 'Metrics and validation techniques'),
    ('Feature Engineering', 'Data preprocessing and feature creation'),
    ('Model Deployment', 'Production deployment and MLOps'),
    ('Time Series', 'Time series analysis and forecasting'),
    ('Reinforcement Learning', 'Agent-based learning and optimization'),
    ('Statistical Learning', 'Statistical methods in machine learning');
