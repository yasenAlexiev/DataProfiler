#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Initializing DataProfiler database..."

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed. Please install PostgreSQL first.${NC}"
    exit 1
fi

# Check if we can connect to PostgreSQL
if ! psql -U postgres -c "SELECT 1" &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to PostgreSQL. Please check your installation and credentials.${NC}"
    echo "Make sure PostgreSQL is running and you have the correct permissions."
    exit 1
fi

# Run the initialization script
echo "Running database initialization script..."
psql -U postgres -f init.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database initialization completed successfully!${NC}"
    echo "You can now update your .env file with these credentials:"
    echo "DATABASE_URL=postgresql://dataprofiler_user:dataprofiler_password@localhost:5432/dataprofiler"
else
    echo -e "${RED}Error: Database initialization failed.${NC}"
    exit 1
fi

# Update .env file if it exists
if [ -f "../.env" ]; then
    echo "Updating .env file with new database credentials..."
    sed -i 's|^DATABASE_URL=.*|DATABASE_URL=postgresql://dataprofiler_user:dataprofiler_password@localhost:5432/dataprofiler|' ../.env
    echo -e "${GREEN}.env file updated successfully!${NC}"
fi

echo "Next steps:"
echo "1. Run database migrations: alembic upgrade head"
echo "2. Start your application: python -m uvicorn app.main:app --reload" 