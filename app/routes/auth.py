from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.schemas.schemas import UserRegisterRequest, UserRegisterResponse, UserRegisterResponseUser, Token, UserLoginRequest
from app.services.auth import create_user_account, authenticate_user, create_access_token
from app.core.database import get_db # Assuming get_db is in app.core.database
from app.config.settings import settings


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
            id_users=created_user.id,
            email=created_user.email,
            name=created_user.name,
            created=created_user.created
        )
    )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    login_data: UserLoginRequest, # Changed from OAuth2PasswordRequestForm
    db: Session = Depends(get_db)
):
    """
    Logs in a user and returns an access token.
    Expects a JSON body with email and password.
    """
    user = authenticate_user(db, email=login_data.email, password=login_data.password) # Changed from form_data
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nesprávné přihlašovací údaje.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}