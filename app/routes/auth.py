from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.schemas import UserRegisterRequest, UserRegisterResponse, UserRegisterResponseUser
from app.services.auth import create_user_account
from app.core.database import get_db # Assuming get_db is in app.core.database

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

@router.post("/register", response_model=UserRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registers a new user.
    - Hashes the password.
    - Creates a user record.
    - Assigns a default role.
    """
    created_user = await create_user_account(db=db, user_data=user_data)

    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or other registration error.",
        )

    return UserRegisterResponse(
        message="Registrace úspěšná.",
        user=UserRegisterResponseUser(
            id_users=created_user.id_users,
            email=created_user.email,
            name=created_user.name,
            created=created_user.created
        )
    )