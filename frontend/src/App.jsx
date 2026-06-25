import { useEffect, useState } from "react";
import { api } from "./api";
import "./App.css";

function formatMoney(value) {
  return `${Number(value || 0).toLocaleString("ru-RU")} ₽`;
}

function ProgressBar({ value }) {
  const width = Math.min(Math.max(Number(value || 0), 0), 100);

  return (
    <div className="progress">
      <div className="progressFill" style={{ width: `${width}%` }} />
    </div>
  );
}

function PieChart({ data }) {
  const total = data.reduce((sum, item) => sum + Number(item.total || 0), 0);

  if (!data.length || total === 0) {
    return <p className="muted">Нет данных для диаграммы</p>;
  }

  let currentPercent = 0;
  const colors = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#6b7280", "#db2777"];

  const gradient = data
    .map((item, index) => {
      const percent = (Number(item.total || 0) / total) * 100;
      const start = currentPercent;
      const end = currentPercent + percent;
      currentPercent = end;
      return `${colors[index % colors.length]} ${start}% ${end}%`;
    })
    .join(", ");

  return (
    <div className="pieWrapper">
      <div className="pie" style={{ background: `conic-gradient(${gradient})` }}>
        <div className="pieCenter">
          <span>Всего</span>
          <strong>{formatMoney(total)}</strong>
        </div>
      </div>

      <div className="pieLegend">
        {data.map((item, index) => {
          const percent = ((Number(item.total || 0) / total) * 100).toFixed(1);
          return (
            <div className="pieLegendItem" key={item.category}>
              <span className="legendDot" style={{ background: colors[index % colors.length] }} />
              <span>{item.category}</span>
              <b>{percent}%</b>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatCard({ label, value, tone = "blue" }) {
  return (
    <div className={`card statCard ${tone}`}>
      <span>{label}</span>
      <strong>{formatMoney(value)}</strong>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [dashboard, setDashboard] = useState(null);
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [profile, setProfile] = useState(null);

  const [login, setLogin] = useState({ username: "testuser2", password: "12345678" });
  const [account, setAccount] = useState({ name: "Основная карта", type: "DEBIT_CARD", currency: "RUB", balance: 100000 });
  const [transaction, setTransaction] = useState({ amount: 1200, type: "EXPENSE", note: "Покупка продуктов", account_id: "", category_id: "" });
  const [limit, setLimit] = useState({ amount_limit: 10000, category_id: "", start_date: "2026-06-01", end_date: "2026-06-30" });
  const [goal, setGoal] = useState({ title: "Накопить на ноутбук", target_amount: 150000, current_amount: 30000, target_date: "2026-12-31" });

  const [aiRecommendation, setAiRecommendation] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [period, setPeriod] = useState("month");
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [profileSaved, setProfileSaved] = useState(false);
  const [tab, setTab] = useState("dashboard");

  async function doLogin(e) {
    e.preventDefault();

    const formData = new URLSearchParams();
    formData.append("username", login.username);
    formData.append("password", login.password);

    const res = await api.post("/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    localStorage.setItem("token", res.data.access_token);
    setToken(res.data.access_token);
  }

  async function loadTransactionsByPeriod(selectedPeriod = period) {
    const today = new Date();
    let dateFrom = null;

    if (selectedPeriod === "today") dateFrom = today;
    if (selectedPeriod === "week") {
      dateFrom = new Date();
      dateFrom.setDate(today.getDate() - 7);
    }
    if (selectedPeriod === "month") dateFrom = new Date(today.getFullYear(), today.getMonth(), 1);

    const params = {};
    if (dateFrom) params.date_from = dateFrom.toISOString().slice(0, 10);
    if (selectedPeriod !== "all") params.date_to = today.toISOString().slice(0, 10);

    const res = await api.get("/budget/transactions", { params });
    setFilteredTransactions(res.data);
  }

  async function loadData() {
    const [dashRes, catRes, accRes, profileRes] = await Promise.all([
      api.get("/budget/dashboard"),
      api.get("/budget/categories"),
      api.get("/budget/accounts"),
      api.get("/auth/profile"),
    ]);

    setDashboard(dashRes.data);
    setCategories(catRes.data);
    setAccounts(accRes.data);
    setProfile(profileRes.data);
    await loadTransactionsByPeriod();
  }

  async function createAccount(e) {
    e.preventDefault();
    await api.post("/budget/accounts", { ...account, balance: Number(account.balance) });
    await loadData();
  }

  async function createTransaction(e) {
    e.preventDefault();
    await api.post("/budget/transactions", { ...transaction, amount: Number(transaction.amount) });
    await loadData();
  }

  async function createLimit(e) {
    e.preventDefault();
    await api.post("/budget/limits", { ...limit, amount_limit: Number(limit.amount_limit) });
    await loadData();
  }

  async function createGoal(e) {
    e.preventDefault();
    await api.post("/budget/goals", {
      ...goal,
      target_amount: Number(goal.target_amount),
      current_amount: Number(goal.current_amount),
    });
    await loadData();
  }

  async function generateAiRecommendation() {
    setAiLoading(true);
    try {
      const res = await api.get("/invest/recommendation/generate", {
        params: { force: true },
      });
      setAiRecommendation(res.data);
    } catch (error) {
      console.error(error);
      alert("Не удалось получить AI-рекомендацию");
    } finally {
      setAiLoading(false);
    }
  }

  async function saveProfile(e) {
    e.preventDefault();

    await api.put("/auth/profile", {
      first_name: profile.first_name || null,
      last_name: profile.last_name || null,
      age: profile.age ? Number(profile.age) : null,
      employment_confidence: profile.employment_confidence ? Number(profile.employment_confidence) : null,
      risk_tolerance: profile.risk_tolerance ? Number(profile.risk_tolerance) : null,
      investment_horizon: profile.investment_horizon || null,
      investment_experience: profile.investment_experience || null,
      income_stability: profile.income_stability ? Number(profile.income_stability) : null,
      dependents_count: profile.dependents_count !== null && profile.dependents_count !== "" ? Number(profile.dependents_count) : null,
      has_emergency_fund: profile.has_emergency_fund === true || profile.has_emergency_fund === "true",
      preferred_assets: profile.preferred_assets || null,
    });

    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2000);
    await loadData();
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    setDashboard(null);
    setProfile(null);
    setAiRecommendation(null);
  }

  useEffect(() => {
    if (token) loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) {
    return (
      <main className="loginPage">
        <section className="authCard">
          <div className="brandMark">₽</div>
          <h1>ФинМетрика</h1>
          <p>Персональный кабинет для управления финансами</p>

          <form onSubmit={doLogin}>
            <input placeholder="username или email" value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })} />
            <input placeholder="password" type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })} />
            <button>Войти</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <header className="top">
        <div>
          <h1>ФинМетрика</h1>
          <p>Дашборд личных финансов</p>
        </div>
        <button className="logoutButton" onClick={logout}>Выйти</button>
      </header>

      <nav className="tabs">
        <button className={tab === "dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>Dashboard</button>
        <button className={tab === "budget" ? "active" : ""} onClick={() => setTab("budget")}>Бюджет</button>
        <button className={tab === "ai" ? "active" : ""} onClick={() => setTab("ai")}>AI-помощник</button>
        <button className={tab === "profile" ? "active" : ""} onClick={() => setTab("profile")}>Профиль</button>
      </nav>

      {tab === "dashboard" && dashboard && (
        <>
          <section className="grid statsGrid">
            <StatCard label="Баланс" value={dashboard.total_balance} tone="blue" />
            <StatCard label="Доход за месяц" value={dashboard.month_income} tone="green" />
            <StatCard label="Расход за месяц" value={dashboard.month_expense} tone="red" />
            <StatCard label="Профицит" value={dashboard.month_surplus} tone="violet" />
          </section>

          <section className="card healthCard">
            <div className="healthHeader">
              <div>
                <h2>Финансовое состояние</h2>
                <p className="muted">Оценка рассчитывается backend на основе профицита, накоплений, лимитов и риск-профиля.</p>
              </div>
              <div className="scoreCircle">
                <strong>{aiRecommendation?.analysis?.financial_score ?? "—"}</strong>
                <span>/100</span>
              </div>
            </div>

            {aiRecommendation?.analysis ? (
              <div className="healthGrid">
                <div>
                  <h3>Сильные стороны</h3>
                  {aiRecommendation.analysis.score_reasons_positive.map((item) => <p className="good" key={item}>✓ {item}</p>)}
                </div>
                <div>
                  <h3>Что улучшить</h3>
                  {aiRecommendation.analysis.score_reasons_negative.map((item) => <p className="bad" key={item}>! {item}</p>)}
                </div>
              </div>
            ) : (
              <p className="muted">Сгенерируй AI-рекомендацию, чтобы увидеть оценку финансового состояния.</p>
            )}
          </section>

          <section className="columns dashboardColumns">
            <div className="card">
              <h2>Расходы по категориям</h2>
              <PieChart data={dashboard.expenses_by_category} />
              <div className="categoryBars">
                {dashboard.expenses_by_category.map((item) => {
                  const max = Math.max(...dashboard.expenses_by_category.map((x) => x.total), 1);
                  return (
                    <div className="chartItem" key={item.category}>
                      <div className="chartHeader"><span>{item.category}</span><b>{formatMoney(item.total)}</b></div>
                      <ProgressBar value={(item.total / max) * 100} />
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="card">
              <h2>Лимиты бюджета</h2>
              {dashboard.limits_progress.length === 0 ? (
                <p className="muted">Лимиты не созданы</p>
              ) : (
                dashboard.limits_progress.map((limit) => (
                  <div key={limit.limit_id} className="chartItem">
                    <div className="chartHeader"><span>{limit.category_name}</span><b>{formatMoney(limit.amount_spent)} / {formatMoney(limit.amount_limit)}</b></div>
                    <ProgressBar value={limit.progress_percent} />
                    {limit.is_exceeded && <p className="danger">Лимит превышен</p>}
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="columns">
            <div className="card">
              <div className="sectionHeader">
                <h2>Операции</h2>
                <select value={period} onChange={(e) => { setPeriod(e.target.value); loadTransactionsByPeriod(e.target.value); }}>
                  <option value="today">Сегодня</option>
                  <option value="week">Неделя</option>
                  <option value="month">Месяц</option>
                  <option value="all">Все</option>
                </select>
              </div>

              {filteredTransactions.length === 0 ? <p className="muted">Операций за выбранный период нет</p> : filteredTransactions.map((t) => (
                <div className="row" key={t.id}>
                  <span>{t.note || t.type}</span>
                  <b className={t.type === "EXPENSE" ? "moneyNegative" : "moneyPositive"}>{t.type === "EXPENSE" ? "-" : "+"}{formatMoney(t.amount)}</b>
                </div>
              ))}
            </div>

            <div className="card">
              <h2>Цели</h2>
              {dashboard.goals.map((g) => (
                <div className="goalRow" key={g.id}>
                  <div><strong>{g.title}</strong><span>{formatMoney(g.current_amount)} / {formatMoney(g.target_amount)}</span></div>
                  <b>{g.progress_percent}%</b>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {tab === "budget" && dashboard && (
        <>
          <section className="columns">
            <div className="card">
              <h2>Создать счёт</h2>
              <form onSubmit={createAccount}>
                <input value={account.name} onChange={(e) => setAccount({ ...account, name: e.target.value })} />
                <select value={account.type} onChange={(e) => setAccount({ ...account, type: e.target.value })}>
                  <option value="CASH">Наличные</option>
                  <option value="DEBIT_CARD">Дебетовая карта</option>
                  <option value="CREDIT_CARD">Кредитная карта</option>
                  <option value="DEPOSIT">Вклад</option>
                </select>
                <input type="number" value={account.balance} onChange={(e) => setAccount({ ...account, balance: e.target.value })} />
                <button>Создать</button>
              </form>
            </div>

            <div className="card">
              <h2>Добавить операцию</h2>
              <form onSubmit={createTransaction}>
                <input type="number" value={transaction.amount} onChange={(e) => setTransaction({ ...transaction, amount: e.target.value })} />
                <select value={transaction.type} onChange={(e) => setTransaction({ ...transaction, type: e.target.value })}>
                  <option value="EXPENSE">Расход</option>
                  <option value="INCOME">Доход</option>
                </select>
                <input value={transaction.note} onChange={(e) => setTransaction({ ...transaction, note: e.target.value })} />
                <select value={transaction.account_id} onChange={(e) => setTransaction({ ...transaction, account_id: e.target.value })}>
                  <option value="">Выбери счёт</option>
                  {accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
                <select value={transaction.category_id} onChange={(e) => setTransaction({ ...transaction, category_id: e.target.value })}>
                  <option value="">Выбери категорию</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <button>Добавить</button>
              </form>
            </div>
          </section>

          <section className="columns">
            <div className="card">
              <h2>Создать лимит</h2>
              <form onSubmit={createLimit}>
                <input type="number" placeholder="Сумма лимита" value={limit.amount_limit} onChange={(e) => setLimit({ ...limit, amount_limit: e.target.value })} />
                <select value={limit.category_id} onChange={(e) => setLimit({ ...limit, category_id: e.target.value })}>
                  <option value="">Выбери категорию</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <input type="date" value={limit.start_date} onChange={(e) => setLimit({ ...limit, start_date: e.target.value })} />
                <input type="date" value={limit.end_date} onChange={(e) => setLimit({ ...limit, end_date: e.target.value })} />
                <button>Создать лимит</button>
              </form>
            </div>

            <div className="card">
              <h2>Создать цель</h2>
              <form onSubmit={createGoal}>
                <input placeholder="Название цели" value={goal.title} onChange={(e) => setGoal({ ...goal, title: e.target.value })} />
                <input type="number" placeholder="Целевая сумма" value={goal.target_amount} onChange={(e) => setGoal({ ...goal, target_amount: e.target.value })} />
                <input type="number" placeholder="Уже накоплено" value={goal.current_amount} onChange={(e) => setGoal({ ...goal, current_amount: e.target.value })} />
                <input type="date" value={goal.target_date} onChange={(e) => setGoal({ ...goal, target_date: e.target.value })} />
                <button>Создать цель</button>
              </form>
            </div>
          </section>
        </>
      )}

      {tab === "ai" && dashboard && (
        <section className="card aiCard">
          <div className="aiHeader">
            <div>
              <h2>AI-финансовый помощник</h2>
              <p className="muted">Рекомендация формируется на основе баланса, расходов, целей, лимитов, риск-профиля и профиля инвестора.</p>
            </div>
            <button onClick={generateAiRecommendation} disabled={aiLoading}>{aiLoading ? "Генерация..." : "Сгенерировать рекомендацию"}</button>
          </div>

          {aiRecommendation ? (
            <div className="aiBox">
              <p className="muted">Модель: {aiRecommendation.model} · Профицит: {formatMoney(aiRecommendation.surplus)}</p>
              <div className="aiText">{aiRecommendation.ai_text}</div>
            </div>
          ) : (
            <div className="emptyState">Нажми кнопку, чтобы получить рекомендацию от Ollama.</div>
          )}
        </section>
      )}

      {tab === "profile" && profile && (
        <section className="card profileCard">
          <div className="sectionHeader">
            <div>
              <h2>Профиль инвестора</h2>
              <p className="muted">Эти данные используются для более точных инвестиционных рекомендаций.</p>
            </div>
            {profileSaved && <span className="savedBadge">Сохранено</span>}
          </div>

          <form className="profileForm" onSubmit={saveProfile}>
            <div className="formGrid">
              <label>Имя<input value={profile.first_name || ""} onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} /></label>
              <label>Фамилия<input value={profile.last_name || ""} onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} /></label>
              <label>Возраст<input type="number" value={profile.age || ""} onChange={(e) => setProfile({ ...profile, age: e.target.value })} /></label>
              <label>Уверенность в работе, 1–5<input type="number" min="1" max="5" value={profile.employment_confidence || ""} onChange={(e) => setProfile({ ...profile, employment_confidence: e.target.value })} /></label>
              <label>Стабильность дохода, 1–5<input type="number" min="1" max="5" value={profile.income_stability || ""} onChange={(e) => setProfile({ ...profile, income_stability: e.target.value })} /></label>
              <label>Терпимость к риску, 1–5<input type="number" min="1" max="5" value={profile.risk_tolerance || ""} onChange={(e) => setProfile({ ...profile, risk_tolerance: e.target.value })} /></label>
              <label>Горизонт инвестирования<select value={profile.investment_horizon || ""} onChange={(e) => setProfile({ ...profile, investment_horizon: e.target.value })}><option value="">Не указано</option><option value="SHORT">Короткий — до 1 года</option><option value="MEDIUM">Средний — 1–3 года</option><option value="LONG">Долгий — 3+ года</option></select></label>
              <label>Опыт инвестирования<select value={profile.investment_experience || ""} onChange={(e) => setProfile({ ...profile, investment_experience: e.target.value })}><option value="">Не указано</option><option value="NONE">Нет опыта</option><option value="BEGINNER">Начинающий</option><option value="INTERMEDIATE">Средний</option><option value="ADVANCED">Продвинутый</option></select></label>
              <label>Иждивенцы<input type="number" min="0" value={profile.dependents_count ?? ""} onChange={(e) => setProfile({ ...profile, dependents_count: e.target.value })} /></label>
              <label>Финансовая подушка<select value={String(profile.has_emergency_fund ?? false)} onChange={(e) => setProfile({ ...profile, has_emergency_fund: e.target.value === "true" })}><option value="false">Нет</option><option value="true">Да</option></select></label>
              <label>Предпочитаемые активы<input placeholder="bonds,index_funds,stocks" value={profile.preferred_assets || ""} onChange={(e) => setProfile({ ...profile, preferred_assets: e.target.value })} /></label>
            </div>
            <button type="submit">Сохранить профиль</button>
          </form>
        </section>
      )}
    </main>
  );
}

export default App;
