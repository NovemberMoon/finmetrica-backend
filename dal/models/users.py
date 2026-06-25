import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class UserRole(str, enum.Enum):
    CLIENT = "client"
    ADMIN = "admin"

class RiskLevel(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    password_hash: str

    role: UserRole = Field(default=UserRole.CLIENT)
    risk_profile: RiskLevel = Field(default=RiskLevel.UNASSIGNED)
    access_level: Optional[int] = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Профиль пользователя
    age: int | None = None

    employment_confidence: int | None = None      # 1–5
    income_stability: int | None = None           # 1–5
    risk_tolerance: int | None = None             # 1–5

    investment_horizon: str | None = None         # SHORT / MEDIUM / LONG
    investment_experience: str | None = None      # NONE / BEGINNER / INTERMEDIATE / ADVANCED

    dependents_count: int | None = None

    has_emergency_fund: bool | None = None

    preferred_assets: str | None = None           # bonds,index_funds,stocks

class UserProfileUpdate(SQLModel):
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    employment_confidence: int | None = None
    risk_tolerance: int | None = None
    investment_horizon: str | None = None
    investment_experience: str | None = None
    income_stability: int | None = None
    dependents_count: int | None = None
    has_emergency_fund: bool | None = None
    preferred_assets: str | None = None


class UserProfileRead(SQLModel):
    id: uuid.UUID
    email: str
    username: str
    first_name: str | None = None
    last_name: str | None = None
    risk_profile: RiskLevel
    age: int | None = None
    employment_confidence: int | None = None
    risk_tolerance: int | None = None
    investment_horizon: str | None = None
    investment_experience: str | None = None
    income_stability: int | None = None
    dependents_count: int | None = None
    has_emergency_fund: bool | None = None
    preferred_assets: str | None = None

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: uuid.UUID
    role: UserRole
    risk_profile: RiskLevel
    access_level: Optional[int]
    created_at: datetime

class RiskAssessmentTest(SQLModel, table=True):
    __tablename__ = "risk_assessment_tests"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="users.id")
    questions: str 
    result_score: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))