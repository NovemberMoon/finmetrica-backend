def analyze_finances(
    *,
    total_balance: int,
    income: int,
    expense: int,
    surplus: int,
    goals: list,
    limits: list,
    expenses_by_category: list,
    risk_profile: str,
    age: int | None = None,
    employment_confidence: int | None = None,
    risk_tolerance: int | None = None,
    investment_horizon: str | None = None,
    investment_experience: str | None = None,
    income_stability: int | None = None,
    dependents_count: int | None = None,
    has_emergency_fund: bool | None = None,
    preferred_assets: str | None = None,
) -> dict:
    saving_rate = round((surplus / income) * 100, 2) if income > 0 else 0

    total_expenses = sum(item["total"] for item in expenses_by_category) or 1

    top_categories = sorted(
        [
            {
                "category": item["category"],
                "total": item["total"],
                "share_percent": round((item["total"] / total_expenses) * 100, 2),
            }
            for item in expenses_by_category
        ],
        key=lambda x: x["total"],
        reverse=True,
    )[:3]

    exceeded_limits = [
        {
            "category": limit["category_name"],
            "amount_limit": limit["amount_limit"],
            "amount_spent": limit["amount_spent"],
            "over_by": limit["amount_spent"] - limit["amount_limit"],
        }
        for limit in limits
        if limit["amount_limit"] > 0 and limit["amount_spent"] > limit["amount_limit"]
    ]

    goals_analysis = [
        {
            "title": goal["title"],
            "target_amount": goal["target_amount"],
            "current_amount": goal["current_amount"],
            "left_amount": goal["target_amount"] - goal["current_amount"],
            "progress_percent": goal["progress_percent"],
        }
        for goal in goals
    ]

    if surplus <= 0:
        investment_capacity = "NONE"
        recommended_investment = 0
    elif saving_rate < 10:
        investment_capacity = "LOW"
        recommended_investment = round(surplus)
    elif saving_rate < 25:
        investment_capacity = "MEDIUM"
        recommended_investment = round(surplus)
    else:
        investment_capacity = "HIGH"
        recommended_investment = round(surplus)

    # Живая оценка финансового состояния: 0–100
    score = 50

    # 1. Доля накоплений / дефицита: от -20 до +25
    # +30% и выше — отлично, 0% — нейтрально, небольшой минус не убивает оценку сразу.
    score += max(-20, min(25, saving_rate * 0.8))

    # 2. Наличие положительного баланса: плавно, максимум +10
    # 100 000 ₽ и выше дают полный бонус.
    balance_bonus = min(10, max(0, total_balance / 10000))
    score += balance_bonus

    # 3. Лимиты: штрафуем за каждое превышение пропорционально силе превышения
    # Небольшое превышение = небольшой штраф.
    for limit in exceeded_limits:
        if limit["amount_limit"] > 0:
            over_ratio = limit["over_by"] / limit["amount_limit"]
            score -= min(10, over_ratio * 20)

    # 4. Прогресс целей: максимум +10
    if goals_analysis:
        avg_goal_progress = sum(goal["progress_percent"] for goal in goals_analysis) / len(goals_analysis)
        score += min(10, avg_goal_progress / 10)

    # 5. Риск-профиль
    if risk_profile == "UNASSIGNED":
        score -= 7
    else:
        score += 3

    score = round(max(0, min(score, 100)))

    score_reasons_positive = []
    score_reasons_negative = []

    if surplus > 0:
        score_reasons_positive.append("Есть положительный профицит за месяц")
    if saving_rate >= 20:
        score_reasons_positive.append("Высокая доля накоплений")
    if total_balance > 0:
        score_reasons_positive.append("Есть положительный общий баланс")
    if not exceeded_limits:
        score_reasons_positive.append("Лимиты не превышены")

    if exceeded_limits:
        score_reasons_negative.append("Есть превышенные лимиты")
    if risk_profile == "UNASSIGNED":
        score_reasons_negative.append("Не пройден риск-тест")
    if surplus <= 0:
        score_reasons_negative.append("Нет свободного денежного потока")

    allocation_ranges = build_allocation_ranges(
        risk_tolerance=risk_tolerance,
        income_stability=income_stability,
        employment_confidence=employment_confidence,
        investment_horizon=investment_horizon,
        investment_experience=investment_experience,
        has_emergency_fund=has_emergency_fund,
    )

    return {
        "total_balance": total_balance,
        "income": income,
        "expense": expense,
        "surplus": surplus,
        "saving_rate_percent": saving_rate,
        "risk_profile": risk_profile,
        "financial_score": score,
        "top_expense_categories": top_categories,
        "exceeded_limits": exceeded_limits,
        "goals": goals_analysis,
        "allocation_ranges": allocation_ranges,
        "investment_capacity": investment_capacity,
        "recommended_monthly_investment": recommended_investment,
        "score_reasons_positive": score_reasons_positive,
        "score_reasons_negative": score_reasons_negative,
        "user_profile": {
            "age": age,
            "employment_confidence": employment_confidence,
            "risk_tolerance": risk_tolerance,
            "investment_horizon": investment_horizon,
            "investment_experience": investment_experience,
            "income_stability": income_stability,
            "dependents_count": dependents_count,
            "has_emergency_fund": has_emergency_fund,
            "preferred_assets": preferred_assets,
        },
    }

def build_allocation_ranges(
    *,
    risk_tolerance: int | None,
    income_stability: int | None,
    employment_confidence: int | None,
    investment_horizon: str | None,
    investment_experience: str | None,
    has_emergency_fund: bool | None,
) -> dict:
    # Базовый умеренный профиль
    cash_min, cash_max = 10, 25
    bonds_min, bonds_max = 30, 55
    stocks_min, stocks_max = 25, 55

    # Терпимость к риску
    if risk_tolerance is not None:
        if risk_tolerance <= 2:
            cash_min, cash_max = 25, 45
            bonds_min, bonds_max = 40, 65
            stocks_min, stocks_max = 5, 25
        elif risk_tolerance >= 4:
            cash_min, cash_max = 5, 20
            bonds_min, bonds_max = 20, 45
            stocks_min, stocks_max = 40, 70

    # Нестабильная работа/доход → больше ликвидности и облигаций
    if income_stability is not None and income_stability <= 2:
        cash_min += 10
        cash_max += 10
        stocks_max -= 10

    if employment_confidence is not None and employment_confidence <= 2:
        cash_min += 10
        cash_max += 10
        stocks_max -= 10

    # Нет подушки → обязательно больше ликвидной части
    if has_emergency_fund is False:
        cash_min = max(cash_min, 30)
        cash_max = max(cash_max, 50)
        stocks_max = min(stocks_max, 35)

    # Новичок → не слишком агрессивно
    if investment_experience in ("NONE", "BEGINNER"):
        stocks_max = min(stocks_max, 45)

    # Длинный горизонт позволяет больше акций
    if investment_horizon == "LONG" and risk_tolerance is not None and risk_tolerance >= 4:
        stocks_max = min(75, stocks_max + 5)
        cash_max = max(cash_min, cash_max - 5)

    # Нормализация диапазонов
    cash_min = max(0, min(cash_min, 80))
    cash_max = max(cash_min, min(cash_max, 80))

    bonds_min = max(0, min(bonds_min, 80))
    bonds_max = max(bonds_min, min(bonds_max, 80))

    stocks_min = max(0, min(stocks_min, 80))
    stocks_max = max(stocks_min, min(stocks_max, 80))

    return {
        "cash": {
            "label": "ликвидная часть",
            "min": cash_min,
            "max": cash_max,
        },
        "bonds": {
            "label": "облигации",
            "min": bonds_min,
            "max": bonds_max,
        },
        "stocks_or_index_funds": {
            "label": "акции и индексные фонды",
            "min": stocks_min,
            "max": stocks_max,
        },
    }