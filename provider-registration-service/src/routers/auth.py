"""Authentication endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ..auth.jwt_handler import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])

# TEMPORARY: Hardcoded admin for testing
# TODO: Replace with database user lookup
ADMIN_USER = {
    "username": "admin@example.com",
    "password_hash": "$2b$12$JTTl35DfwYumO8YwOpKuMum89zzbynJamgwg//U7jaFfEGZM9u1ly",  # "admin123"
    "role": "admin"
}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint - returns JWT token"""
    # Validate credentials
    if form_data.username != ADMIN_USER["username"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not verify_password(form_data.password, ADMIN_USER["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Create token
    access_token = create_access_token(data={
        "sub": ADMIN_USER["username"],
        "role": ADMIN_USER["role"]
    })

    return {"access_token": access_token, "token_type": "bearer"}
