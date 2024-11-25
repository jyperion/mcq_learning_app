-- Initialize the database
DROP TABLE IF EXISTS question_feedback;
DROP TABLE IF EXISTS user_answers;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS sessions;

-- Create concepts table
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

-- Create questions table
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    options TEXT NOT NULL,  -- JSON array of options
    correct_answer INTEGER NOT NULL,  -- Index of correct option (0-3)
    explanation TEXT,
    hint TEXT,
    difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')) NOT NULL,
    concept_id INTEGER,
    FOREIGN KEY (concept_id) REFERENCES concepts (id)
);

-- Create sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP
);

-- Create user_answers table
CREATE TABLE user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    answer INTEGER NOT NULL,  -- Index of selected option (0-3)
    is_correct BOOLEAN NOT NULL,
    time_taken INTEGER NOT NULL,  -- in seconds
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions (id),
    FOREIGN KEY (question_id) REFERENCES questions (id)
);

-- Create question_feedback table
CREATE TABLE question_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    feedback TEXT NOT NULL,
    type TEXT DEFAULT 'general' CHECK(type IN ('general', 'error', 'improvement', 'flag')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions (id)
);

-- Create indexes
CREATE INDEX idx_user_answers_session ON user_answers(session_id);
CREATE INDEX idx_user_answers_question ON user_answers(question_id);
CREATE INDEX idx_questions_concept ON questions(concept_id);
CREATE INDEX idx_feedback_question ON question_feedback(question_id);
