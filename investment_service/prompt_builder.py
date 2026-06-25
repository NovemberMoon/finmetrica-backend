def _money(value) -> str:
    if value is None:
        return "не указано"

    try:
        return f"{int(value):,}".replace(",", " ") + " ₽"
    except (TypeError, ValueError):
        return str(value)


def _percent(value) -> str:
    if value is None:
        return "не указано"

    return f"{value}%"


def _rating(value, labels: dict[int, str]) -> str:
    if value is None:
        return "не указано"

    return labels.get(value, f"{value} из 5")


def _translate_horizon(value: str | None) -> str:
    return {
        "SHORT": "короткий — до 1 года",
        "MEDIUM": "средний — от 1 до 3 лет",
        "LONG": "долгий — больше 3 лет",
    }.get(value, "не указано")


def _translate_experience(value: str | None) -> str:
    return {
        "NONE": "нет опыта",
        "BEGINNER": "начинающий инвестор",
        "INTERMEDIATE": "средний опыт",
        "ADVANCED": "продвинутый инвестор",
    }.get(value, "не указано")


def _translate_risk_profile(value: str | None) -> str:
    return {
        "UNASSIGNED": "не определён",
        "CONSERVATIVE": "консервативный",
        "MODERATE": "умеренный",
        "AGGRESSIVE": "агрессивный",
    }.get(value, value or "не указано")


def _translate_capacity(value: str | None) -> str:
    return {
        "NONE": "инвестировать пока рано",
        "LOW": "низкая",
        "MEDIUM": "средняя",
        "HIGH": "высокая",
    }.get(value, value or "не указано")


def _bool_text(value) -> str:
    if value is True:
        return "есть"
    if value is False:
        return "нет"
    return "не указано"


def _list_lines(items: list[str], empty_text: str) -> str:
    if not items:
        return empty_text
    return "\n".join([f"- {item}" for item in items])


def _top_categories_text(categories: list[dict]) -> str:
    if not categories:
        return "Нет данных о расходах."

    return "\n".join(
        [
            f"- {item['category']}: {_money(item['total'])} ({_percent(item['share_percent'])})"
            for item in categories
        ]
    )


def _exceeded_limits_text(limits: list[dict]) -> str:
    if not limits:
        return "Превышенных лимитов нет."

    return "\n".join(
        [
            f"- {item['category']}: лимит {_money(item['amount_limit'])}, "
            f"потрачено {_money(item['amount_spent'])}, "
            f"превышение {_money(item['over_by'])}"
            for item in limits
        ]
    )


def _goals_text(goals: list[dict]) -> str:
    if not goals:
        return "Финансовые цели не заданы."

    return "\n".join(
        [
            f"- {goal['title']}: накоплено {_money(goal['current_amount'])} "
            f"из {_money(goal['target_amount'])}, осталось {_money(goal['left_amount'])}, "
            f"прогресс {_percent(goal['progress_percent'])}"
            for goal in goals
        ]
    )


def _preferred_assets_text(value: str | None) -> str:
    if not value:
        return "не указано"

    mapping = {
        "bonds": "облигации",
        "stocks": "акции",
        "index_funds": "индексные фонды",
        "cash": "ликвидная часть",
        "money_market": "фонды денежного рынка",
    }

    parts = [item.strip() for item in value.split(",") if item.strip()]
    translated = [mapping.get(item, item) for item in parts]

    return ", ".join(translated) if translated else "не указано"


def build_financial_prompt(analysis: dict) -> str:
    profile = analysis.get("user_profile", {})

    employment_confidence = _rating(
        profile.get("employment_confidence"),
        {
            1: "очень низкая",
            2: "низкая",
            3: "средняя",
            4: "высокая",
            5: "очень высокая",
        },
    )

    income_stability = _rating(
        profile.get("income_stability"),
        {
            1: "очень нестабильный доход",
            2: "нестабильный доход",
            3: "средняя стабильность дохода",
            4: "стабильный доход",
            5: "очень стабильный доход",
        },
    )

    risk_tolerance = _rating(
        profile.get("risk_tolerance"),
        {
            1: "очень низкая",
            2: "низкая",
            3: "умеренная",
            4: "высокая",
            5: "очень высокая",
        },
    )

    return f"""
Ты — финансовый помощник приложения «ФинМетрика».

Твоя задача — объяснить пользователю результаты анализа и дать осторожный инвестиционный план.
Все расчёты уже выполнены backend. Не пересчитывай показатели и не придумывай новые суммы.
Используй только данные ниже.
Пиши только на русском языке.
Не используй английские слова.
Не называй конкретные компании, тикеры, криптовалюты, брокеров или отдельные ценные бумаги.
Не обещай доходность и не представляй рекомендацию как гарантированный результат.

ДАННЫЕ ПОЛЬЗОВАТЕЛЯ

Финансовое состояние:
- Индекс финансового здоровья: {analysis["financial_score"]} из 100.
- Общий баланс: {_money(analysis["total_balance"])}.
- Доход за месяц: {_money(analysis["income"])}.
- Расход за месяц: {_money(analysis["expense"])}.
- Свободный профицит за месяц: {_money(analysis["surplus"])}.
- Доля накоплений: {_percent(analysis["saving_rate_percent"])}.
- Инвестиционная готовность: {_translate_capacity(analysis["investment_capacity"])}.
- Сумма, которую можно распределить: {_money(analysis["recommended_monthly_investment"])} в месяц.
- Допустимые диапазоны распределения:
  • Ликвидная часть: от {analysis["allocation_ranges"]["cash"]["min"]}% до {analysis["allocation_ranges"]["cash"]["max"]}%.
  • Облигации: от {analysis["allocation_ranges"]["bonds"]["min"]}% до {analysis["allocation_ranges"]["bonds"]["max"]}%.
  • Акции и индексные фонды: от {analysis["allocation_ranges"]["stocks_or_index_funds"]["min"]}% до {analysis["allocation_ranges"]["stocks_or_index_funds"]["max"]}%.

Профиль инвестора:
- Возраст: {profile.get("age") or "не указано"}.
- Риск-профиль: {_translate_risk_profile(analysis["risk_profile"])}.
- Уверенность в рабочем месте: {employment_confidence}.
- Стабильность дохода: {income_stability}.
- Терпимость к риску: {risk_tolerance}.
- Горизонт инвестирования: {_translate_horizon(profile.get("investment_horizon"))}.
- Опыт инвестирования: {_translate_experience(profile.get("investment_experience"))}.
- Финансовая подушка: {_bool_text(profile.get("has_emergency_fund"))}.
- Иждивенцы: {profile.get("dependents_count") if profile.get("dependents_count") is not None else "не указано"}.
- Предпочитаемые активы: {_preferred_assets_text(profile.get("preferred_assets"))}.

Сильные стороны:
{_list_lines(analysis["score_reasons_positive"], "Нет выраженных сильных сторон.")}

Проблемные зоны:
{_list_lines(analysis["score_reasons_negative"], "Критичных проблем не найдено.")}

Топ расходов:
{_top_categories_text(analysis["top_expense_categories"])}

Превышенные лимиты:
{_exceeded_limits_text(analysis["exceeded_limits"])}

Финансовые цели:
{_goals_text(analysis["goals"])}

КАК ДАТЬ ИНВЕСТИЦИОННУЮ РЕКОМЕНДАЦИЮ

Считай, что сумма для распределения — это весь свободный профицит месяца.
Эту сумму нужно распределить полностью.

Используй только три группы:
- ликвидная часть: накопительный счёт или фонд денежного рынка;
- облигации;
- акции и индексные фонды.

Выбери конкретное распределение внутри допустимых диапазонов, указанных выше.
Нельзя выходить за эти диапазоны.
Сумма долей должна быть ровно 100%.

Если не уверен, выбери середину диапазонов и скорректируй так, чтобы сумма была 100%.

В инвестиционном плане обязательно укажи:
- сумму в рублях в месяц;
- процент для каждой группы;
- сумму в рублях для каждой группы;
- короткое объяснение, почему распределение подходит профилю пользователя.

ФОРМАТ ОТВЕТА

Ответ должен быть коротким и состоять из пяти разделов:

1. Общая оценка
2–3 предложения.

2. Что получается хорошо
2–4 пункта.

3. Что стоит улучшить
2–4 пункта.

4. Инвестиционный план
Укажи сумму, проценты и рубли по каждому классу активов.

5. Следующий шаг
Одно конкретное действие на ближайший месяц.
""".strip()