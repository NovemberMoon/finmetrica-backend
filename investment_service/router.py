import redis.asyncio as redis
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from sqlalchemy import func
from pydantic import BaseModel
import json

from dal.database import get_session
from dal.models.users import User, RiskAssessmentTest, RiskLevel
from dal.models.budget import Transaction, Account, TransactionType
from dal.models.invest import InvestmentRecommendation
from auth_service.security import get_current_user
from core.config import settings

from datetime import date, datetime, time
from dal.models.budget import BudgetLimit, FinancialGoal, Category
from investment_service.ollama_client import ask_ollama
from investment_service.prompt_builder import build_financial_prompt
from investment_service.financial_analyzer import analyze_finances

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
    history = (await session.exec(statement)).all()
    return history

@router.get("/recommendation/generate")
async def generate_ai_recommendation(
    force: bool = False,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    redis_client = redis.from_url(settings.REDIS_URL)
    cache_key = f"ai_rec_user_{current_user.id}"

    cached_rec = await redis_client.get(cache_key)

    if cached_rec and not force:
        await redis_client.aclose()
        return json.loads(cached_rec)

    today = date.today()
    month_start = date(today.year, today.month, 1)

    account_ids = (await session.exec(
        select(Account.id).where(Account.client_id == current_user.id)
    )).all()

    if not account_ids:
        await redis_client.aclose()
        raise HTTPException(status_code=400, detail="Нет счетов для анализа")

    total_balance = (await session.exec(
        select(func.coalesce(func.sum(Account.balance), 0)).where(
            Account.client_id == current_user.id
        )
    )).one()

    month_filter = [
        Transaction.account_id.in_(account_ids),
        Transaction.date >= datetime.combine(month_start, time.min),
        Transaction.date <= datetime.combine(today, time.max),
    ]

    income = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *month_filter,
            Transaction.type == TransactionType.INCOME,
        )
    )).one()

    expense = (await session.exec(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            *month_filter,
            Transaction.type == TransactionType.EXPENSE,
        )
    )).one()

    surplus = income - expense

    goals_raw = (await session.exec(
        select(FinancialGoal).where(FinancialGoal.client_id == current_user.id)
    )).all()

    goals = [
        {
            "title": goal.title,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "progress_percent": round((goal.current_amount / goal.target_amount) * 100, 2)
            if goal.target_amount else 0,
        }
        for goal in goals_raw
    ]

    limits_raw = (await session.exec(
        select(BudgetLimit).where(BudgetLimit.client_id == current_user.id)
    )).all()

    limits = []

    for limit in limits_raw:
        spent = (await session.exec(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.account_id.in_(account_ids),
                Transaction.category_id == limit.category_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= datetime.combine(limit.start_date, time.min),
                Transaction.date <= datetime.combine(limit.end_date, time.max),
            )
        )).one()

        category = await session.get(Category, limit.category_id)

        limits.append({
            "category_name": category.name if category else "Без категории",
            "amount_limit": limit.amount_limit,
            "amount_spent": spent,
        })

    expenses_raw = (await session.exec(
        select(Category.name, func.coalesce(func.sum(Transaction.amount), 0)).join(
            Category,
            Category.id == Transaction.category_id,
            isouter=True,
        ).where(
            *month_filter,
            Transaction.type == TransactionType.EXPENSE,
        ).group_by(Category.name)
    )).all()

    expenses_by_category = [
        {"category": row[0] or "Без категории", "total": row[1]}
        for row in expenses_raw
    ]

    analysis = analyze_finances(
        total_balance=total_balance,
        income=income,
        expense=expense,
        surplus=surplus,
        goals=goals,
        limits=limits,
        expenses_by_category=expenses_by_category,
        risk_profile=current_user.risk_profile.value,
        age=current_user.age,
        employment_confidence=current_user.employment_confidence,
        risk_tolerance=current_user.risk_tolerance,
        investment_horizon=current_user.investment_horizon,
        investment_experience=current_user.investment_experience,
        income_stability=current_user.income_stability,
        dependents_count=current_user.dependents_count,
        has_emergency_fund=current_user.has_emergency_fund,
        preferred_assets=current_user.preferred_assets,
    )

    prompt = build_financial_prompt(analysis)

    try:
        ai_text = await ask_ollama(prompt)
    except Exception as e:
        ai_text = (
            "ИИ временно недоступен. "
            "Проверь, что Ollama запущена и модель llama3.2:3b установлена. "
            f"Техническая ошибка: {str(e)}"
        )

    recommendation = InvestmentRecommendation(
        client_id=current_user.id,
        surplus_amount=surplus,
        prompt_context=prompt,
        generated_text=ai_text,
    )

    session.add(recommendation)
    await session.commit()
    await session.refresh(recommendation)

    result_data = {
        "id": str(recommendation.id),
        "ai_text": ai_text,
        "surplus": surplus,
        "model": settings.OLLAMA_MODEL,
        "analysis": analysis,
    }

    await redis_client.setex(cache_key, 3600, json.dumps(result_data, ensure_ascii=False))
    await redis_client.aclose()

    return result_data