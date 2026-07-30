"""
Database engine, session factory, and declarative base for MyGlowTheory.
Uses DATABASE_URL from environment (defaults to SQLite for local dev).
Swap to PostgreSQL by setting DATABASE_URL=postgresql://user:pass@host/db.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./myglowtheory.db")

# For SQLite, we need check_same_thread=False for FastAPI's threaded request handling
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,  # Set True for SQL debug logging
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Creates all tables. Called on app startup."""
    Base.metadata.create_all(bind=engine)
    
    # Check and alter table for new columns dynamically
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            cursor = conn.execute(text("PRAGMA table_info(appointments)"))
            columns = [row[1] for row in cursor.fetchall()]
            if columns:  # Only run if table exists
                if "workflow_stage" not in columns:
                    conn.execute(text("ALTER TABLE appointments ADD COLUMN workflow_stage TEXT DEFAULT 'operator_review'"))
                if "override_notes" not in columns:
                    conn.execute(text("ALTER TABLE appointments ADD COLUMN override_notes TEXT"))
                if "updated_at" not in columns:
                    conn.execute(text("ALTER TABLE appointments ADD COLUMN updated_at DATETIME"))
    except Exception as e:
        print(f"[DB_MIGRATE] Warning: Alter table skipped: {e}")

# Run schema migrations automatically on import
init_db()
