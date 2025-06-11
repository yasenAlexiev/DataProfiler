-- Create the database if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dataprofiler') THEN
        CREATE DATABASE dataprofiler;
    END IF;
END $$;

-- Connect to the database
\c dataprofiler;

-- Create extension for UUID if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a dedicated user for the application (optional but recommended for security)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'dataprofiler_user') THEN
        CREATE USER dataprofiler_user WITH PASSWORD 'dataprofiler_password';
    END IF;
END $$;

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE dataprofiler TO dataprofiler_user;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO dataprofiler_user;

-- Set search path
SET search_path TO public;

-- Create tables (these will be managed by Alembic, but here for reference)
/*
CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL,
    original_filename VARCHAR NOT NULL,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR DEFAULT 'pending',
    error_message VARCHAR,
    file_size INTEGER,
    row_count INTEGER,
    column_count INTEGER,
    analysis_completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS file_reports (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES uploaded_files(id) ON DELETE CASCADE,
    column VARCHAR NOT NULL,
    mean FLOAT,
    stddev FLOAT,
    min_value FLOAT,
    max_value FLOAT,
    median FLOAT,
    q1 FLOAT,
    q3 FLOAT,
    skew FLOAT,
    kurtosis FLOAT,
    missing_count INTEGER DEFAULT 0,
    missing_percentage FLOAT,
    data_type VARCHAR
);

CREATE TABLE IF NOT EXISTS correlations (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES uploaded_files(id) ON DELETE CASCADE,
    column1 VARCHAR NOT NULL,
    column2 VARCHAR NOT NULL,
    correlation FLOAT NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES uploaded_files(id) ON DELETE CASCADE,
    column VARCHAR NOT NULL,
    method VARCHAR NOT NULL,
    anomaly_indices JSONB NOT NULL,
    threshold FLOAT,
    count INTEGER NOT NULL
);
*/

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_uploaded_files_status ON uploaded_files(status);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_upload_time ON uploaded_files(upload_time);
CREATE INDEX IF NOT EXISTS idx_file_reports_file_id ON file_reports(file_id);
CREATE INDEX IF NOT EXISTS idx_correlations_file_id ON correlations(file_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_file_id ON anomalies(file_id);

-- Add helpful comments
COMMENT ON DATABASE dataprofiler IS 'Database for DataProfiler application - stores file uploads and analysis results';
COMMENT ON TABLE uploaded_files IS 'Stores information about uploaded CSV files and their processing status';
COMMENT ON TABLE file_reports IS 'Contains statistical analysis results for each column in uploaded files';
COMMENT ON TABLE correlations IS 'Stores correlation data between columns in uploaded files';
COMMENT ON TABLE anomalies IS 'Contains anomaly detection results for uploaded files'; 