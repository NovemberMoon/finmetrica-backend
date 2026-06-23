import redis.asyncio as redis
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import func
from pydantic import BaseModel
import json
from typing import List

from dal.database import get_session
from dal.models.users import User, RiskAssessmentTest, RiskLevel
from dal.models.budget import Transaction, Account, TransactionType
from dal.models.invest import InvestmentRecommendation
from auth_service.security import get_current_user
from core.config import settings

router = APIRouter()

class RiskTestSubmit(BaseModel):
    answers_json: str
    score: int
    determined_profile: RiskLevel

@router.post("/risk-test")
async def submit_risk_test(test_in: RiskTestSubmit, current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    current_user.risk_profile = test_in.determined_profile
    session.add(current_user)
    
    new_test = RiskAssessmentTest(client_id=current_user.id, questions=test_in.answers_json, result_score=test_in.score)
    session.add(new_test)
    await session.commit()
    return {"status": "success", "new_profile": current_user.risk_profile}

@router.get("/recommendation/history")
async def get_recommendation_history(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    statement = select(InvestmentRecommendation).where(InvestmentRecommendation.client_id == current_user.id).order_by(InvestmentRecommendation.generated_at.desc())
    history = (await session.exec(statement)).scalars().all()
    return history

@router.get("/recommendation/generate")
async def generate_ai_recommendation(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    redis_client = redis.from_url(settings.REDIS_URL)
    cache_key = f"ai_rec_user_{current_user.id}"
    cached_rec = await redis_client.get(cache_key)
    
    if cached_rec:
        await redis_client.aclose()
        return json.loads(cached_rec)
    
    acc_ids = (await session.exec(select(Account.id).where(Account.client_id == current_user.id))).scalars().all()
    if not acc_ids:
        await redis_client.aclose()
        raise HTTPException(status_code=400, detail="Нет счетов для анализа")

    income = (await session.exec(select(func.sum(Transaction.amount)).where(Transaction.account_id.in_(acc_ids), Transaction.type == TransactionType.INCOME))).scalar() or 0
    expense = (await session.exec(select(func.sum(Transaction.amount)).where(Transaction.account_id.in_(acc_ids), Transaction.type == TransactionType.EXPENSE))).scalar() or 0
    
    surplus = (income - expense) / 100
    prompt = f"У пользователя профицит: {surplus} руб. Риск-профиль: {current_user.risk_profile.value}. Дай инвест-совет."
    
    ai_text = ""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.OLLAMA_URL, json={"model": "llama3", "prompt": prompt, "stream": False}, timeout=30.0)
            response.raise_for_status()
            ai_text = response.json().get("response", "Нет ответа от модели.")
    except Exception as e:
        ai_text = f"ИИ временно недоступен. {str(e)}"
        
    recommendation = InvestmentRecommendation(client_id=current_user.id, surplus_amount=int(surplus*100), prompt_context=prompt, generated_text=ai_text)
    session.add(recommendation)
    await session.commit()
    await session.refresh(recommendation)
    
    result_data = {"id": str(recommendation.id), "ai_text": ai_text, "surplus": surplus}
    await redis_client.setex(cache_key, 3600, json.dumps(result_data))
    await redis_client.aclose()
    
    return result_data