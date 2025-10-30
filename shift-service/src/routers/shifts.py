"""Shift management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from ..database import get_db
from ..models.schemas import (
    ShiftStart,
    ShiftEnd,
    ShiftResponse,
    ShiftListResponse,
    OperatorCreate,
    OperatorResponse,
    OperatorListResponse,
)

router = APIRouter(prefix="/shifts", tags=["Shifts"])


@router.post("/operators", response_model=OperatorResponse, status_code=201)
async def create_operator(operator: OperatorCreate, db: Session = Depends(get_db)):
    """Create a new operator."""
    query = text("""
        INSERT INTO operators (name, employee_id, role, is_active, created_at)
        VALUES (:name, :employee_id, :role, TRUE, NOW())
    """)
    try:
        result = db.execute(
            query,
            {
                "name": operator.name,
                "employee_id": operator.employee_id,
                "role": operator.role,
            },
        )
        db.commit()
        operator_id = result.lastrowid

        # Fetch the created operator
        select_query = text("SELECT * FROM operators WHERE id = :id")
        row = db.execute(select_query, {"id": operator_id}).fetchone()

        return OperatorResponse(
            id=row.id,
            name=row.name,
            employee_id=row.employee_id,
            role=row.role,
            is_active=row.is_active,
            created_at=row.created_at,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create operator: {str(e)}")


@router.get("/operators", response_model=OperatorListResponse)
async def list_operators(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all operators."""
    where_clause = "WHERE is_active = TRUE" if active_only else ""
    query = text(f"""
        SELECT * FROM operators
        {where_clause}
        ORDER BY name
    """)
    rows = db.execute(query).fetchall()

    operators = [
        OperatorResponse(
            id=row.id,
            name=row.name,
            employee_id=row.employee_id,
            role=row.role,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return OperatorListResponse(operators=operators, total=len(operators))


@router.post("/start", response_model=ShiftResponse, status_code=201)
async def start_shift(shift: ShiftStart, db: Session = Depends(get_db)):
    """Start a new shift for an operator."""
    # Check if operator exists
    check_query = text("SELECT id FROM operators WHERE id = :id AND is_active = TRUE")
    operator = db.execute(check_query, {"id": shift.operator_id}).fetchone()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found or inactive")

    # Check if operator already has an active shift
    active_shift_query = text("""
        SELECT id FROM shifts
        WHERE operator_id = :operator_id AND end_time IS NULL
    """)
    active_shift = db.execute(
        active_shift_query, {"operator_id": shift.operator_id}
    ).fetchone()
    if active_shift:
        raise HTTPException(status_code=400, detail="Operator already has an active shift")

    # Create new shift
    insert_query = text("""
        INSERT INTO shifts (operator_id, shift_type, start_time, transactions_processed)
        VALUES (:operator_id, :shift_type, NOW(), 0)
    """)
    try:
        result = db.execute(
            insert_query,
            {"operator_id": shift.operator_id, "shift_type": shift.shift_type},
        )
        db.commit()
        shift_id = result.lastrowid

        # Fetch the created shift
        select_query = text("SELECT * FROM shifts WHERE id = :id")
        row = db.execute(select_query, {"id": shift_id}).fetchone()

        return ShiftResponse(
            id=row.id,
            operator_id=row.operator_id,
            shift_type=row.shift_type,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_minutes=row.duration_minutes,
            transactions_processed=row.transactions_processed,
            notes=row.notes,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to start shift: {str(e)}")


@router.post("/{shift_id}/end", response_model=ShiftResponse)
async def end_shift(
    shift_id: int,
    shift_end: ShiftEnd,
    db: Session = Depends(get_db),
):
    """End an active shift."""
    # Check if shift exists and is active
    check_query = text("""
        SELECT * FROM shifts
        WHERE id = :shift_id AND end_time IS NULL
    """)
    shift = db.execute(check_query, {"shift_id": shift_id}).fetchone()
    if not shift:
        raise HTTPException(status_code=404, detail="Active shift not found")

    # Update shift with end time
    update_query = text("""
        UPDATE shifts
        SET end_time = NOW(),
            duration_minutes = TIMESTAMPDIFF(MINUTE, start_time, NOW()),
            notes = :notes
        WHERE id = :shift_id
    """)
    try:
        db.execute(
            update_query,
            {"shift_id": shift_id, "notes": shift_end.notes},
        )
        db.commit()

        # Fetch updated shift
        select_query = text("SELECT * FROM shifts WHERE id = :id")
        row = db.execute(select_query, {"id": shift_id}).fetchone()

        return ShiftResponse(
            id=row.id,
            operator_id=row.operator_id,
            shift_type=row.shift_type,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_minutes=row.duration_minutes,
            transactions_processed=row.transactions_processed,
            notes=row.notes,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to end shift: {str(e)}")


@router.get("", response_model=ShiftListResponse)
async def list_shifts(
    operator_id: Optional[int] = Query(None),
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List shifts with optional filters."""
    conditions = []
    params = {"limit": limit, "offset": offset}

    if operator_id:
        conditions.append("operator_id = :operator_id")
        params["operator_id"] = operator_id

    if active_only:
        conditions.append("end_time IS NULL")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    count_query = text(f"SELECT COUNT(*) FROM shifts {where_clause}")
    total = db.execute(count_query, params).scalar()

    # Get paginated results
    query = text(f"""
        SELECT * FROM shifts
        {where_clause}
        ORDER BY start_time DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(query, params).fetchall()

    shifts = [
        ShiftResponse(
            id=row.id,
            operator_id=row.operator_id,
            shift_type=row.shift_type,
            start_time=row.start_time,
            end_time=row.end_time,
            duration_minutes=row.duration_minutes,
            transactions_processed=row.transactions_processed,
            notes=row.notes,
        )
        for row in rows
    ]

    return ShiftListResponse(shifts=shifts, total=total)


@router.get("/{shift_id}", response_model=ShiftResponse)
async def get_shift(shift_id: int, db: Session = Depends(get_db)):
    """Get details of a specific shift."""
    query = text("SELECT * FROM shifts WHERE id = :id")
    row = db.execute(query, {"id": shift_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Shift not found")

    return ShiftResponse(
        id=row.id,
        operator_id=row.operator_id,
        shift_type=row.shift_type,
        start_time=row.start_time,
        end_time=row.end_time,
        duration_minutes=row.duration_minutes,
        transactions_processed=row.transactions_processed,
        notes=row.notes,
    )
