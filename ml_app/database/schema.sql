-- Initialize the database
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS concept_questions;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS user_progress;
DROP TABLE IF EXISTS user_sessions;

CREATE TABLE concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    options JSON NOT NULL,
    correct TEXT NOT NULL,
    explanation TEXT NOT NULL,
    difficulty INTEGER DEFAULT 1,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Junction table for questions and concepts
CREATE TABLE concept_questions (
    concept_id INTEGER,
    question_id INTEGER,
    FOREIGN KEY (concept_id) REFERENCES concepts (id),
    FOREIGN KEY (question_id) REFERENCES questions (id),
    PRIMARY KEY (concept_id, question_id)
);

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Track user progress
CREATE TABLE user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_taken INTEGER NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (question_id) REFERENCES questions (id)
);

-- Track user sessions
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    started_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at timestamp,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Create indices for better query performance
CREATE INDEX idx_concept_questions_concept ON concept_questions(concept_id);
CREATE INDEX idx_concept_questions_question ON concept_questions(question_id);
CREATE INDEX idx_user_progress_user ON user_progress(user_id);
CREATE INDEX idx_user_progress_question ON user_progress(question_id);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
