from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import timedelta

from dal.database import get_session
from dal.models.users import User, UserCreate, UserPublic
from core.config import settings
from dal.models.users import UserProfileRead, UserProfileUpdate
from auth_service.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter()

@router.post("/register", response_model=UserPublic)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    statement = select(User).where(
        or_(User.email == user_in.email, User.username == user_in.username)
    )
    existing_user = (await session.exec(statement)).first()
    
    if existing_user:
        if existing_user.email == user_in.email:
            raise HTTPException(status_code=400, detail="Email уже зарегистрирован")
        if existing_user.username == user_in.username:
            raise HTTPException(status_code=400, detail="Никнейм уже занят")
        
    hashed_password = get_password_hash(user_in.password)
    
    user_data = user_in.model_dump(exclude={"password"})
    new_user = User(**user_data, password_hash=hashed_password)
    
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    print(f"[DEBUG] Попытка логина: username={form_data.username}")
    print(f"[DEBUG] Фактическая длина пароля, пришедшего на сервер: {len(form_data.password)}")
    
    statement = select(User).where(
        or_(User.email == form_data.username, User.username == form_data.username)
    )
    user = (await session.exec(statement)).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile", response_model=UserProfileRead)
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put("/profile", response_model=UserProfileRead)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    for key, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user