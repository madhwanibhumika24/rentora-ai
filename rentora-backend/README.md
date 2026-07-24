# Rentora backend

AI-powered multi-city PG and hostel management platform.
FastAPI + MySQL backend.

## Setup

1. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your MySQL connection details
4. Run the server: `uvicorn app.main:app --reload`

## Project structure

- `app/main.py` - FastAPI app entrypoint
- `app/config.py` - environment/settings
- `app/database.py` - SQLAlchemy engine and session
- `app/models/` - database models (tables)
- `app/schemas/` - Pydantic request/response schemas
- `app/routers/` - API route handlers