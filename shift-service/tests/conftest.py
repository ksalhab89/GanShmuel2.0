"""Test fixtures and configuration for shift service tests."""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.main import app
from src.database import get_db


def sqlite_compatible_query(query_str: str) -> str:
    """Convert MySQL-specific SQL to SQLite-compatible SQL."""
    # Replace NOW() with CURRENT_TIMESTAMP
    query_str = query_str.replace("NOW()", "CURRENT_TIMESTAMP")
    # Replace TIMESTAMPDIFF(MINUTE, a, b) with (julianday(b) - julianday(a)) * 1440
    if "TIMESTAMPDIFF(MINUTE" in query_str:
        # This is a simplified replacement - may need adjustment for complex queries
        import re
        query_str = re.sub(
            r'TIMESTAMPDIFF\(MINUTE,\s*(\w+),\s*(\w+)\)',
            r'CAST((julianday(\2) - julianday(\1)) * 1440 AS INTEGER)',
            query_str
        )
    return query_str

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine with StaticPool for in-memory SQLite
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create a fresh database session for each test."""
    # Create tables
    with test_engine.connect() as connection:
        # Create operators table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS operators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                employee_id VARCHAR(50) UNIQUE NOT NULL,
                role VARCHAR(20) DEFAULT 'weigher',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # Create shifts table
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_id INTEGER NOT NULL,
                shift_type VARCHAR(20) NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                duration_minutes INTEGER NULL,
                transactions_processed INTEGER DEFAULT 0,
                notes TEXT NULL,
                FOREIGN KEY (operator_id) REFERENCES operators(id)
            )
        """))
        connection.commit()

    # Create session
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        with test_engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS shifts"))
            connection.execute(text("DROP TABLE IF EXISTS operators"))
            connection.commit()


@pytest.fixture(scope="function")
def client(db_session: Session):
    """Create a test client with overridden database dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Patch the text() function to convert MySQL queries to SQLite
    original_text = text

    def patched_text(query_str):
        converted = sqlite_compatible_query(query_str)
        return original_text(converted)

    with patch('src.routers.shifts.text', patched_text):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_operator(db_session: Session) -> dict:
    """Create a sample operator for testing."""
    query = text("""
        INSERT INTO operators (name, employee_id, role, is_active, created_at)
        VALUES (:name, :employee_id, :role, TRUE, CURRENT_TIMESTAMP)
    """)
    result = db_session.execute(
        query,
        {
            "name": "John Doe",
            "employee_id": "EMP001",
            "role": "weigher",
        }
    )
    db_session.commit()

    operator_id = result.lastrowid

    # Fetch the created operator
    select_query = text("SELECT * FROM operators WHERE id = :id")
    row = db_session.execute(select_query, {"id": operator_id}).fetchone()

    return {
        "id": row.id,
        "name": row.name,
        "employee_id": row.employee_id,
        "role": row.role,
        "is_active": row.is_active,
        "created_at": row.created_at,
    }


@pytest.fixture
def inactive_operator(db_session: Session) -> dict:
    """Create an inactive operator for testing."""
    query = text("""
        INSERT INTO operators (name, employee_id, role, is_active, created_at)
        VALUES (:name, :employee_id, :role, FALSE, CURRENT_TIMESTAMP)
    """)
    result = db_session.execute(
        query,
        {
            "name": "Inactive User",
            "employee_id": "EMP999",
            "role": "weigher",
        }
    )
    db_session.commit()

    operator_id = result.lastrowid

    # Fetch the created operator
    select_query = text("SELECT * FROM operators WHERE id = :id")
    row = db_session.execute(select_query, {"id": operator_id}).fetchone()

    return {
        "id": row.id,
        "name": row.name,
        "employee_id": row.employee_id,
        "role": row.role,
        "is_active": row.is_active,
        "created_at": row.created_at,
    }


@pytest.fixture
def active_shift(db_session: Session, sample_operator: dict) -> dict:
    """Create an active shift for testing."""
    query = text("""
        INSERT INTO shifts (operator_id, shift_type, start_time, transactions_processed)
        VALUES (:operator_id, :shift_type, CURRENT_TIMESTAMP, 0)
    """)
    result = db_session.execute(
        query,
        {
            "operator_id": sample_operator["id"],
            "shift_type": "morning",
        }
    )
    db_session.commit()

    shift_id = result.lastrowid

    # Fetch the created shift
    select_query = text("SELECT * FROM shifts WHERE id = :id")
    row = db_session.execute(select_query, {"id": shift_id}).fetchone()

    return {
        "id": row.id,
        "operator_id": row.operator_id,
        "shift_type": row.shift_type,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "duration_minutes": row.duration_minutes,
        "transactions_processed": row.transactions_processed,
        "notes": row.notes,
    }


@pytest.fixture
def completed_shift(db_session: Session, sample_operator: dict) -> dict:
    """Create a completed shift for testing."""
    # Insert shift with end_time
    query = text("""
        INSERT INTO shifts (operator_id, shift_type, start_time, end_time, duration_minutes, transactions_processed, notes)
        VALUES (:operator_id, :shift_type, datetime('now', '-8 hours'), datetime('now'), 480, 25, 'Completed shift')
    """)
    result = db_session.execute(
        query,
        {
            "operator_id": sample_operator["id"],
            "shift_type": "morning",
        }
    )
    db_session.commit()

    shift_id = result.lastrowid

    # Fetch the created shift
    select_query = text("SELECT * FROM shifts WHERE id = :id")
    row = db_session.execute(select_query, {"id": shift_id}).fetchone()

    return {
        "id": row.id,
        "operator_id": row.operator_id,
        "shift_type": row.shift_type,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "duration_minutes": row.duration_minutes,
        "transactions_processed": row.transactions_processed,
        "notes": row.notes,
    }


@pytest.fixture
def multiple_operators(db_session: Session) -> list[dict]:
    """Create multiple operators for testing."""
    operators = []

    for i in range(5):
        query = text("""
            INSERT INTO operators (name, employee_id, role, is_active, created_at)
            VALUES (:name, :employee_id, :role, TRUE, CURRENT_TIMESTAMP)
        """)
        result = db_session.execute(
            query,
            {
                "name": f"Operator {i+1}",
                "employee_id": f"EMP{str(i+1).zfill(3)}",
                "role": "weigher" if i < 3 else "supervisor",
            }
        )
        operator_id = result.lastrowid

        # Fetch the created operator
        select_query = text("SELECT * FROM operators WHERE id = :id")
        row = db_session.execute(select_query, {"id": operator_id}).fetchone()

        operators.append({
            "id": row.id,
            "name": row.name,
            "employee_id": row.employee_id,
            "role": row.role,
            "is_active": row.is_active,
            "created_at": row.created_at,
        })

    db_session.commit()
    return operators


@pytest.fixture
def multiple_shifts(db_session: Session, sample_operator: dict) -> list[dict]:
    """Create multiple shifts for testing."""
    shifts = []
    shift_types = ["morning", "afternoon", "night"]

    for i in range(10):
        has_end = i < 7  # First 7 shifts are completed

        if has_end:
            query = text("""
                INSERT INTO shifts (operator_id, shift_type, start_time, end_time, duration_minutes, transactions_processed)
                VALUES (:operator_id, :shift_type, datetime('now', :offset),
                        datetime('now', :end_offset), :duration, :transactions)
            """)
            result = db_session.execute(
                query,
                {
                    "operator_id": sample_operator["id"],
                    "shift_type": shift_types[i % 3],
                    "offset": f"-{i*2} hours",
                    "end_offset": f"-{i*2-8} hours",
                    "duration": 480,
                    "transactions": i * 3,
                }
            )
        else:
            query = text("""
                INSERT INTO shifts (operator_id, shift_type, start_time, end_time, duration_minutes, transactions_processed)
                VALUES (:operator_id, :shift_type, datetime('now', :offset), NULL, NULL, 0)
            """)
            result = db_session.execute(
                query,
                {
                    "operator_id": sample_operator["id"],
                    "shift_type": shift_types[i % 3],
                    "offset": f"-{i*2} hours",
                }
            )

        shift_id = result.lastrowid

        # Fetch the created shift
        select_query = text("SELECT * FROM shifts WHERE id = :id")
        row = db_session.execute(select_query, {"id": shift_id}).fetchone()

        shifts.append({
            "id": row.id,
            "operator_id": row.operator_id,
            "shift_type": row.shift_type,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "duration_minutes": row.duration_minutes,
            "transactions_processed": row.transactions_processed,
            "notes": row.notes,
        })

    db_session.commit()
    return shifts
