-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS user_answers;
DROP TABLE IF EXISTS practice_sessions;
DROP TABLE IF EXISTS concept_questions;
DROP TABLE IF EXISTS concept_prerequisites;
DROP TABLE IF EXISTS concept_topics;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS concepts;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS user_progress;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS users;

-- Create tables in dependency order
-- Create topics table
CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create concepts table
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    difficulty TEXT CHECK(difficulty IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create concept_topics table
CREATE TABLE concept_topics (
    concept_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (concept_id, topic_id),
    FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
);

-- Create concept prerequisites table
CREATE TABLE concept_prerequisites (
    concept_id INTEGER,
    prerequisite_id INTEGER,
    PRIMARY KEY (concept_id, prerequisite_id),
    FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE,
    FOREIGN KEY (prerequisite_id) REFERENCES concepts (id) ON DELETE CASCADE
);

-- Create questions table
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    options TEXT NOT NULL, -- JSON array of options
    correct_option TEXT NOT NULL,
    explanation TEXT,
    difficulty TEXT CHECK(difficulty IN ('beginner', 'intermediate', 'advanced')),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'flagged', 'deleted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create concept_questions table
CREATE TABLE concept_questions (
    concept_id INTEGER,
    question_id INTEGER,
    PRIMARY KEY (concept_id, question_id),
    FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
);

-- Create practice_sessions table
CREATE TABLE practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER,
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    questions_answered INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    total_time INTEGER DEFAULT 0, -- in seconds
    FOREIGN KEY (concept_id) REFERENCES concepts (id) ON DELETE SET NULL
);

-- Create user_answers table
CREATE TABLE user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_spent INTEGER NOT NULL, -- in seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES practice_sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
);

-- Create indices for better query performance
CREATE INDEX idx_concept_topics_concept ON concept_topics(concept_id);
CREATE INDEX idx_concept_topics_topic ON concept_topics(topic_id);
CREATE INDEX idx_concept_prerequisites_concept ON concept_prerequisites(concept_id);
CREATE INDEX idx_concept_prerequisites_prereq ON concept_prerequisites(prerequisite_id);
CREATE INDEX idx_concept_questions_concept ON concept_questions(concept_id);
CREATE INDEX idx_concept_questions_question ON concept_questions(question_id);
CREATE INDEX idx_user_answers_session ON user_answers(session_id);
CREATE INDEX idx_user_answers_question ON user_answers(question_id);
