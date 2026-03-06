"""
SentiVest Life Simulator
Compressed real-life simulation engine for demo purposes.
A full month plays out in ~30-60 seconds with realistic transactions,
proactive AI alerts, and life events.
"""

import asyncio
import random
from datetime import datetime, timedelta
from knowledge_graph import kg


# ==================== TRANSACTION POOLS ====================

SALARY_SOURCES = [
    {"source": "ACME Corp Salary", "type": "salary", "icon": "\U0001F4B0"},
    {"source": "Freelance Dev", "type": "freelance", "icon": "\U0001F4BB"},
    {"source": "FNB Interest", "type": "interest", "icon": "\U0001F3E6"},
]

DEBIT_ORDERS = [
    ("Discovery Health", 4200, "Insurance", "\U0001F3E5"),
    ("Outsurance", 1847, "Insurance", "\U0001F6E1\uFE0F"),
    ("Old Mutual", 650, "Insurance", "\U0001F6E1\uFE0F"),
    ("Home Loan", 16847, "Loan Repayment", "\U0001F3E0"),
    ("Car Finance", 6333, "Loan Repayment", "\U0001F697"),
    ("Personal Loan", 1267, "Loan Repayment", "\U0001F4B3"),
    ("Vodacom", 599, "Telecom", "\U0001F4F1"),
    ("Netflix SA", 299, "Subscription", "\U0001F4FA"),
    ("Spotify Premium", 79.99, "Subscription", "\U0001F3B5"),
    ("DSTV", 899, "Subscription", "\U0001F4FA"),
]

DAILY_POOLS = {
    "morning": [
        ("Vida e Caffe", (55, 110), "Coffee", "\u2615"),
        ("Starbucks", (75, 130), "Coffee", "\u2615"),
        ("Gautrain", (60, 120), "Transport", "\U0001F684"),
        ("Engen QuickShop", (80, 200), "Convenience", "\U0001F3EA"),
    ],
    "midday": [
        ("Woolworths Food", (450, 1200), "Groceries", "\U0001F6D2"),
        ("Checkers", (350, 900), "Groceries", "\U0001F6D2"),
        ("Pick n Pay", (400, 1000), "Groceries", "\U0001F6D2"),
        ("Spur", (180, 450), "Dining", "\U0001F37D\uFE0F"),
        ("Wimpy", (120, 280), "Dining", "\U0001F37D\uFE0F"),
        ("Dis-Chem", (150, 600), "Health", "\U0001F48A"),
    ],
    "afternoon": [
        ("Shell Garage N1", (800, 1400), "Fuel", "\u26FD"),
        ("Engen", (700, 1200), "Fuel", "\u26FD"),
        ("BP Sandton", (600, 1100), "Fuel", "\u26FD"),
        ("Takealot.com", (200, 3000), "Shopping", "\U0001F6CD\uFE0F"),
        ("Uber", (80, 250), "Transport", "\U0001F695"),
        ("Bolt", (60, 200), "Transport", "\U0001F695"),
    ],
    "evening": [
        ("Uber Eats", (150, 400), "Food Delivery", "\U0001F354"),
        ("Mr D Food", (120, 350), "Food Delivery", "\U0001F355"),
        ("KFC", (100, 250), "Food Delivery", "\U0001F357"),
        ("Nandos", (200, 450), "Food Delivery", "\U0001F357"),
        ("Debonairs", (130, 280), "Food Delivery", "\U0001F355"),
        ("Ocean Basket", (250, 500), "Dining", "\U0001F37D\uFE0F"),
    ],
    "late_night": [
        ("Uber Eats", (200, 500), "Food Delivery", "\U0001F354"),
        ("Steam Store", (150, 800), "Entertainment", "\U0001F3AE"),
    ],
}

LIFE_EVENTS = [
    {
        "id": "fraud_attempt",
        "weight": 0.08,
        "generate": lambda month: {
            "merchant": random.choice([
                "UNKNOWN_MERCH_ZW", "SUSPICIOUS_CARD_NG", "TEST_TXN_CN",
                "UNVERIFIED_SELLER_AE", "RANDOM_MERCH_XX"
            ]),
            "amount": round(random.uniform(2000, 15000), 2),
            "category": "Unknown",
            "time": f"{random.randint(0, 4):02d}:{random.randint(0, 59):02d}",
            "risk": "critical",
            "alert_type": "fraud",
        },
    },
    {
        "id": "medical_emergency",
        "weight": 0.04,
        "generate": lambda month: {
            "merchant": random.choice(["Netcare Hospital", "Life Hospital", "Mediclinic"]),
            "amount": round(random.uniform(3000, 25000), 2),
            "category": "Emergency",
            "time": f"{random.randint(6, 22):02d}:{random.randint(0, 59):02d}",
            "risk": "high",
            "alert_type": "emergency",
        },
    },
    {
        "id": "car_trouble",
        "weight": 0.05,
        "generate": lambda month: {
            "merchant": random.choice(["Midas", "Tiger Wheel & Tyre", "AutoZone"]),
            "amount": round(random.uniform(1500, 8000), 2),
            "category": "Vehicle",
            "time": "10:30",
            "risk": "medium",
            "alert_type": "unplanned",
        },
    },
    {
        "id": "utility_spike",
        "weight": 0.10,
        "generate": lambda month: {
            "merchant": random.choice(["City Power Joburg", "Eskom", "Rand Water"]),
            "amount": round(random.uniform(3000, 6000), 2),
            "category": "Utilities",
            "time": "06:00",
            "risk": "medium",
            "alert_type": "spike",
        },
    },
    {
        "id": "refund",
        "weight": 0.06,
        "generate": lambda month: {
            "merchant": random.choice(["Takealot Refund", "Amazon Refund", "Outsurance Refund"]),
            "amount": round(random.uniform(500, 5000), 2),
            "category": "Refund",
            "time": "14:00",
            "risk": "low",
            "alert_type": "refund",
        },
    },
    {
        "id": "impulse_splurge",
        "weight": 0.07,
        "generate": lambda month: {
            "merchant": random.choice([
                "Canal Walk Shopping", "Sandton City", "Apple Store",
                "Incredible Connection", "Zara"
            ]),
            "amount": round(random.uniform(2000, 15000), 2),
            "category": "Shopping",
            "time": f"{random.randint(10, 18):02d}:{random.randint(0, 59):02d}",
            "risk": "low",
            "alert_type": "splurge",
        },
    },
]


# ==================== PROACTIVE INSIGHTS ====================

def _generate_insights() -> list[dict]:
    """Generate proactive AI insights based on current KG state."""
    insights = []

    # Budget warnings
    for b in kg.get_budgets():
        pct = (b["spent"] / b["limit"] * 100) if b["limit"] > 0 else 0
        if 80 <= pct < 100:
            insights.append({
                "type": "budget_warning",
                "severity": "warning",
                "title": f"{b['category']} Budget at {pct:.0f}%",
                "body": f"You've spent R{b['spent']:,.0f} of your R{b['limit']:,.0f} {b['category']} budget. "
                        f"R{b['limit'] - b['spent']:,.0f} remaining.",
                "icon": "\u26A0\uFE0F",
            })
        elif pct >= 100:
            over = b["spent"] - b["limit"]
            insights.append({
                "type": "budget_exceeded",
                "severity": "critical",
                "title": f"{b['category']} Budget Exceeded",
                "body": f"Over by R{over:,.0f}. Consider reducing {b['category']} spending.",
                "icon": "\U0001F6A8",
            })

    # Low balance warning
    if kg.balance < 5000 and kg.salary > 0:
        days_to_salary = (kg.salary_day - datetime.now().day) % 30
        insights.append({
            "type": "low_balance",
            "severity": "warning",
            "title": "Low Balance Alert",
            "body": f"Balance R{kg.balance:,.0f} with {days_to_salary} days until payday. "
                    f"Reduce discretionary spending.",
            "icon": "\u26A0\uFE0F",
        })

    # Food delivery escalation
    food_cat = kg.nodes.get(kg._category_id("Food Delivery"))
    if food_cat:
        count = food_cat.attrs.get("txn_count", 0)
        total = food_cat.attrs.get("total_spent", 0)
        if count >= 8:
            insights.append({
                "type": "habit_alert",
                "severity": "info",
                "title": "Food Delivery Habit Detected",
                "body": f"{count} orders totalling R{total:,.0f}. That's R{total * 12 / max(kg.demo_month + 1, 1):,.0f}/year at this rate. "
                        f"Cooking at home could save 60%.",
                "icon": "\U0001F354",
            })

    # Savings opportunity
    if kg.salary > 0:
        savings_rate = ((kg.salary - kg.total_spent / max(kg.transactions_processed / 26, 1))
                        / kg.salary * 100) if kg.transactions_processed > 0 else 0
        if savings_rate < 10:
            insights.append({
                "type": "savings_low",
                "severity": "warning",
                "title": "Low Savings Rate",
                "body": f"Your savings rate is ~{max(savings_rate, 0):.0f}%. "
                        f"Aim for 20%+ of income. Review subscriptions and food delivery.",
                "icon": "\U0001F4C9",
            })

    # Spending concentration
    categories = {}
    for n in kg.nodes.values():
        if n.type == "category":
            categories[n.label] = n.attrs.get("total_spent", 0)
    total = sum(categories.values())
    if total > 0:
        for cat, spent in categories.items():
            pct = spent / total * 100
            if pct > 35:
                insights.append({
                    "type": "concentration",
                    "severity": "info",
                    "title": f"{cat} Dominates Spending",
                    "body": f"{pct:.0f}% of all spending is {cat} (R{spent:,.0f}). "
                            f"Diversifying reduces financial risk.",
                    "icon": "\U0001F4CA",
                })

    return insights


# ==================== FINANCIAL HEALTH SCORE ====================

def calculate_health_score() -> dict:
    """Calculate overall financial health score (0-100)."""
    scores = {}

    # 1. Debt-to-income ratio (25 points)
    total_income = sum(n.attrs.get("amount", 0) for n in kg.nodes.values()
                       if n.type == "income" and n.attrs.get("frequency") == "monthly")
    if total_income == 0:
        total_income = kg.salary or 1
    loan_monthly = sum(n.attrs.get("monthly_payment", 0) for n in kg.nodes.values() if n.type == "loan")
    # Add insurance & telecom debit orders (not counted as loans)
    insurance_monthly = sum(n.attrs.get("premium", 0) for n in kg.nodes.values() if n.type == "insurance")
    dti = ((loan_monthly + insurance_monthly) / total_income * 100) if total_income > 0 else 0
    if dti < 30:
        scores["dti"] = 25
    elif dti < 40:
        scores["dti"] = 20
    elif dti < 50:
        scores["dti"] = 15
    elif dti < 60:
        scores["dti"] = 10
    else:
        scores["dti"] = 5
    dti_detail = f"DTI {dti:.0f}% — {'healthy' if dti < 35 else 'stretched' if dti < 50 else 'high risk'}"

    # 2. Savings buffer (20 points)
    monthly_expenses = kg.total_spent / max(kg.demo_month + 1, 1) if kg.transactions_processed > 0 else 30000
    buffer_months = kg.balance / monthly_expenses if monthly_expenses > 0 else 0
    if buffer_months >= 6:
        scores["buffer"] = 20
    elif buffer_months >= 3:
        scores["buffer"] = 15
    elif buffer_months >= 1:
        scores["buffer"] = 10
    else:
        scores["buffer"] = 5
    buffer_detail = f"{buffer_months:.1f} months expenses covered"

    # 3. Budget adherence (20 points)
    budgets = kg.get_budgets()
    if budgets:
        within = sum(1 for b in budgets if b["status"] == "OK")
        adherence = within / len(budgets) * 100
        scores["budgets"] = int(adherence / 100 * 20)
    else:
        scores["budgets"] = 10  # neutral if no budgets
        adherence = 50
    budget_detail = f"{adherence:.0f}% budgets within limits" if budgets else "No budgets set"

    # 4. Insurance coverage (15 points)
    policies = [n for n in kg.nodes.values() if n.type == "insurance"]
    has_health = any("health" in p.label.lower() for p in policies)
    has_car = any("car" in p.label.lower() or "vehicle" in p.label.lower() for p in policies)
    has_life = any("life" in p.label.lower() for p in policies)
    coverage_count = sum([has_health, has_car, has_life])
    scores["insurance"] = min(15, coverage_count * 5)
    insurance_detail = f"{coverage_count}/3 essential policies"

    # 5. Investment diversification (10 points)
    investments = [n for n in kg.nodes.values() if n.type == "investment"]
    inv_types = set(i.attrs.get("asset_type", "") for i in investments)
    if len(inv_types) >= 3:
        scores["investments"] = 10
    elif len(inv_types) >= 2:
        scores["investments"] = 7
    elif len(inv_types) >= 1:
        scores["investments"] = 4
    else:
        scores["investments"] = 0
    inv_detail = f"{len(investments)} positions across {len(inv_types)} asset types"

    # 6. Spending habits (10 points)
    recurring = kg.get_recurring_payments()
    sub_cost = sum(r["amount"] for r in recurring if r["amount"] < 1000)  # subscriptions
    sub_pct = (sub_cost / total_income * 100) if total_income > 0 else 0
    if sub_pct < 5:
        scores["habits"] = 10
    elif sub_pct < 10:
        scores["habits"] = 7
    elif sub_pct < 15:
        scores["habits"] = 4
    else:
        scores["habits"] = 2
    habits_detail = f"R{sub_cost:,.0f}/mo subscriptions ({sub_pct:.0f}% of income)"

    total = sum(scores.values())
    grade = ("A+" if total >= 85 else "A" if total >= 75 else "B" if total >= 65 else
             "C" if total >= 50 else "D" if total >= 35 else "F")

    return {
        "score": total,
        "grade": grade,
        "max": 100,
        "breakdown": scores,
        "details": {
            "dti": dti_detail,
            "buffer": buffer_detail,
            "budgets": budget_detail,
            "insurance": insurance_detail,
            "investments": inv_detail,
            "habits": habits_detail,
        },
        "summary": f"Financial Health: {total}/100 ({grade}). {dti_detail}. {buffer_detail}. {budget_detail}.",
    }


# ==================== LOAN ELIGIBILITY ====================

def assess_loan_eligibility(requested_amount: float, term_months: int = 60,
                             loan_type: str = "personal") -> dict:
    """Assess whether the client qualifies for a loan."""
    total_income = sum(n.attrs.get("amount", 0) for n in kg.nodes.values()
                       if n.type == "income" and n.attrs.get("frequency") == "monthly")
    if total_income == 0:
        total_income = kg.salary or 0

    # Current obligations
    existing_loan_monthly = sum(n.attrs.get("monthly_payment", 0)
                                for n in kg.nodes.values() if n.type == "loan")
    recurring = kg.get_recurring_payments()
    # Exclude loans from recurring to avoid double-counting
    loan_merchants = {n.label.lower() for n in kg.nodes.values() if n.type == "loan"}
    committed = sum(r["amount"] for r in recurring
                    if r["merchant"].lower() not in loan_merchants)
    total_obligations = existing_loan_monthly + committed

    # Estimate new loan payment
    rates = {"personal": 18.0, "vehicle": 12.5, "mortgage": 11.75, "education": 14.0}
    rate = rates.get(loan_type, 15.0)
    r = rate / 100 / 12
    if r > 0 and term_months > 0:
        new_payment = requested_amount * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)
    else:
        new_payment = requested_amount / max(term_months, 1)

    # DTI calculation
    current_dti = (total_obligations / total_income * 100) if total_income > 0 else 100
    new_dti = ((total_obligations + new_payment) / total_income * 100) if total_income > 0 else 100

    # Disposable income check
    disposable_after = total_income - total_obligations - new_payment

    # Credit score factors
    factors = []
    eligible = True
    risk = "low"

    if total_income < 10000:
        factors.append({"factor": "Low income", "impact": "negative", "detail": f"R{total_income:,.0f}/mo"})
        eligible = False

    if new_dti > 75:
        factors.append({"factor": "High DTI", "impact": "negative", "detail": f"{new_dti:.0f}% exceeds 75% threshold"})
        eligible = False
        risk = "high"
    elif new_dti > 60:
        factors.append({"factor": "Elevated DTI", "impact": "caution", "detail": f"{new_dti:.0f}% — manageable but stretched"})
        risk = "medium"
    elif new_dti > 45:
        factors.append({"factor": "Moderate DTI", "impact": "caution", "detail": f"{new_dti:.0f}% — within acceptable range"})
        risk = "low"
    else:
        factors.append({"factor": "Healthy DTI", "impact": "positive", "detail": f"{new_dti:.0f}%"})

    if disposable_after < 3000:
        factors.append({"factor": "Low disposable income", "impact": "negative",
                        "detail": f"R{disposable_after:,.0f} remaining after obligations"})
        if disposable_after < 0:
            eligible = False

    # Employment stability (check salary history)
    salary_months = len(kg.salary_history)
    if salary_months >= 6:
        factors.append({"factor": "Stable employment", "impact": "positive",
                        "detail": f"{salary_months} months salary history"})
    elif salary_months >= 3:
        factors.append({"factor": "Short employment history", "impact": "caution",
                        "detail": f"{salary_months} months — 6+ preferred"})
    else:
        factors.append({"factor": "Insufficient history", "impact": "negative",
                        "detail": f"Only {salary_months} months tracked"})

    # Existing debt load
    existing_loans = [n for n in kg.nodes.values() if n.type == "loan"]
    total_debt = sum(l.attrs.get("balance", 0) for l in existing_loans)
    if total_debt > total_income * 24:
        factors.append({"factor": "High existing debt", "impact": "negative",
                        "detail": f"R{total_debt:,.0f} — {total_debt / total_income:.0f}x monthly income"})
        risk = "high"

    # Insurance (positive factor)
    policies = len([n for n in kg.nodes.values() if n.type == "insurance"])
    if policies >= 3:
        factors.append({"factor": "Good insurance coverage", "impact": "positive",
                        "detail": f"{policies} active policies"})

    # Savings
    total_balance = sum(a["balance"] for a in kg.accounts.values())
    if total_balance > requested_amount * 0.2:
        factors.append({"factor": "Adequate savings", "impact": "positive",
                        "detail": f"R{total_balance:,.0f} across accounts"})

    # Max affordable amount (allow up to 70% DTI)
    max_affordable_payment = max((total_income * 0.70) - total_obligations, 0)
    if r > 0 and term_months > 0:
        max_amount = max_affordable_payment * ((1 + r) ** term_months - 1) / (r * (1 + r) ** term_months)
    else:
        max_amount = max_affordable_payment * term_months
    max_amount = round(max_amount, -3)  # round to nearest 1000

    verdict = "APPROVED" if eligible else "DECLINED"
    if eligible and risk == "medium":
        verdict = "CONDITIONAL"

    return {
        "verdict": verdict,
        "eligible": eligible,
        "risk": risk,
        "requested_amount": requested_amount,
        "loan_type": loan_type,
        "term_months": term_months,
        "interest_rate": rate,
        "estimated_payment": round(new_payment, 2),
        "total_cost": round(new_payment * term_months, 2),
        "total_interest": round(new_payment * term_months - requested_amount, 2),
        "current_dti": round(current_dti, 1),
        "new_dti": round(new_dti, 1),
        "disposable_after": round(disposable_after, 2),
        "monthly_income": round(total_income, 2),
        "existing_obligations": round(total_obligations, 2),
        "factors": factors,
        "max_affordable": round(max_amount, 2),
        "summary": (
            f"{'Eligible' if eligible else 'Not eligible'} for R{requested_amount:,.0f} {loan_type} loan. "
            f"Payment: R{new_payment:,.0f}/mo over {term_months} months at {rate}%. "
            f"DTI would be {new_dti:.0f}% (from {current_dti:.0f}%). "
            f"{'Maximum affordable: R' + f'{max_amount:,.0f}' if not eligible else ''}"
        ).strip(),
    }


# ==================== SMART TRANSFER ====================

def execute_transfer(from_id: str, to_id: str, amount: float, reference: str = "") -> dict:
    """Transfer money between accounts."""
    if from_id not in kg.accounts:
        return {"success": False, "error": f"Source account {from_id} not found"}
    if to_id not in kg.accounts:
        return {"success": False, "error": f"Destination account {to_id} not found"}
    if kg.accounts[from_id]["balance"] < amount:
        return {"success": False, "error": f"Insufficient funds. Available: R{kg.accounts[from_id]['balance']:,.2f}"}

    # Debit source
    old_active = kg.active_account_id
    kg.switch_account(from_id)
    kg.balance -= amount
    kg.available -= amount
    from_name = kg.accounts[from_id]["name"]

    # Credit destination
    kg.switch_account(to_id)
    kg.balance += amount
    kg.available += amount
    to_name = kg.accounts[to_id]["name"]

    # Restore original active account
    kg.switch_account(old_active)

    # Record in ledger
    kg._record_transaction(
        merchant=f"Transfer to {to_name}", amount=amount, category="Transfer",
        time=datetime.now().strftime("%H:%M"), risk_level="low",
        txn_type="transfer", verdict="SAFE", icon="\U0001F4B8"
    )

    # Add transfer node to KG
    txn_id = f"transfer_{kg._next_txn_id}"
    kg._add_node(txn_id, f"Transfer R{amount:,.0f}", "transfer", {
        "from": from_id, "to": to_id, "amount": amount,
        "reference": reference or f"Transfer {datetime.now().strftime('%d %b')}",
    })
    kg._add_edge(from_id, txn_id, "SENT")
    kg._add_edge(txn_id, to_id, "RECEIVED")
    kg._notify_change()

    return {
        "success": True,
        "from": {"id": from_id, "name": from_name, "balance": round(kg.accounts[from_id]["balance"], 2)},
        "to": {"id": to_id, "name": to_name, "balance": round(kg.accounts[to_id]["balance"], 2)},
        "amount": amount,
        "message": f"Transferred R{amount:,.2f} from {from_name} to {to_name}.",
    }


# ==================== SIMULATION ENGINE ====================

class LifeSimulator:
    def __init__(self):
        self.running = False
        self.speed = 1.0  # 1.0 = normal (month in ~45s), 2.0 = double speed
        self.phase = "idle"  # idle, salary, debit_orders, daily, evening, life_events
        self.current_day = 1
        self.months_simulated = 0
        self.on_event = None  # async callback: (event_type, data) -> None
        self._task = None

    def status(self) -> dict:
        return {
            "running": self.running,
            "speed": self.speed,
            "phase": self.phase,
            "current_day": self.current_day,
            "months_simulated": self.months_simulated,
            "demo_date": kg.get_demo_date_str(),
        }

    async def start(self, speed: float = 1.0):
        if self.running:
            return {"status": "already_running"}
        self.running = True
        self.speed = speed
        self._task = asyncio.create_task(self._run_loop())
        return {"status": "started", "speed": speed}

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            self._task = None
        self.phase = "idle"
        return {"status": "stopped", "months_simulated": self.months_simulated}

    def set_speed(self, speed: float):
        self.speed = max(0.25, min(speed, 5.0))
        return {"speed": self.speed}

    async def _emit(self, event_type: str, data: dict):
        if self.on_event:
            try:
                await self.on_event(event_type, data)
            except Exception:
                pass

    async def _delay(self, seconds: float):
        """Speed-adjusted delay."""
        await asyncio.sleep(seconds / self.speed)

    async def _run_loop(self):
        """Main simulation loop — each iteration is one month."""
        try:
            while self.running:
                await self._simulate_month()
                self.months_simulated += 1
                kg.advance_month()
                # Brief pause between months
                await self._delay(3)
        except asyncio.CancelledError:
            pass

    async def _simulate_month(self):
        """Simulate one full month of financial life."""
        month = kg.demo_month

        # === Day 25: Salary ===
        self.phase = "salary"
        self.current_day = 25
        await self._emit("phase", {"phase": "salary", "day": 25, "month": kg.get_demo_date_str()})
        await self._delay(1)

        salary_amount = getattr(kg, '_salary_current', 42500)
        freelance = round(random.uniform(3000, 8000), 2)
        interest = round(285 + month * 12, 2)

        kg.add_income("ACME Corp Salary", salary_amount, "monthly", "salary")
        kg.record_income("ACME Corp Salary", salary_amount, "salary", "06:00", "\U0001F4B0")
        await self._emit("transaction", {
            "merchant": "ACME Corp Salary", "amount": -salary_amount,
            "category": "Income", "icon": "\U0001F4B0", "verdict": "SAFE",
            "toast": f"Salary received: R{salary_amount:,.0f}",
        })
        await self._delay(1.5)

        kg.record_income("Freelance Dev", freelance, "freelance", "10:00", "\U0001F4BB")
        await self._emit("transaction", {
            "merchant": "Freelance Dev", "amount": -freelance,
            "category": "Income", "icon": "\U0001F4BB", "verdict": "SAFE",
            "toast": f"Freelance payment: R{freelance:,.0f}",
        })
        kg.salary_history.append({"month": month, "source": "ACME Corp Salary", "amount": salary_amount})
        kg.salary_history.append({"month": month, "source": "Freelance Dev", "amount": freelance})
        await self._delay(1)

        kg.record_income("FNB Interest", interest, "interest", "00:01", "\U0001F3E6")
        await self._delay(0.5)

        # === Day 1: Debit Orders ===
        self.phase = "debit_orders"
        self.current_day = 1
        await self._emit("phase", {"phase": "debit_orders", "day": 1})
        await self._delay(1)

        for merchant, amount, category, icon in DEBIT_ORDERS:
            # Slight random variation for realism
            actual = round(amount * random.uniform(0.98, 1.02), 2) if category != "Subscription" else amount
            kg.ingest_transaction(merchant, actual, category, "01:00", "low", month=month)
            kg.debit_order_history.append({"month": month, "merchant": merchant, "amount": actual})
            await self._emit("transaction", {
                "merchant": merchant, "amount": actual, "category": category,
                "icon": icon, "verdict": "SAFE",
            })
            await self._delay(0.4)

        # === Days 2-28: Daily spending ===
        self.phase = "daily"
        num_days = random.randint(18, 25)  # Not every day has spending

        for day in range(2, min(2 + num_days, 29)):
            self.current_day = day

            # Morning (1-2 transactions)
            if random.random() > 0.3:
                pool = DAILY_POOLS["morning"]
                merchant, (lo, hi), category, icon = random.choice(pool)
                amount = round(random.uniform(lo, hi), 2)
                time = f"{random.randint(6, 9):02d}:{random.randint(0, 59):02d}"
                kg.ingest_transaction(merchant, amount, category, time, "low", month=month)
                await self._emit("transaction", {
                    "merchant": merchant, "amount": amount, "category": category,
                    "icon": icon, "verdict": "SAFE",
                })
                await self._delay(0.6)

            # Midday (0-2 transactions)
            for _ in range(random.randint(0, 2)):
                pool = DAILY_POOLS["midday"]
                merchant, (lo, hi), category, icon = random.choice(pool)
                amount = round(random.uniform(lo, hi), 2)
                time = f"{random.randint(10, 14):02d}:{random.randint(0, 59):02d}"
                kg.ingest_transaction(merchant, amount, category, time, "low", month=month)
                await self._emit("transaction", {
                    "merchant": merchant, "amount": amount, "category": category,
                    "icon": icon, "verdict": "SAFE",
                })
                await self._delay(0.5)

            # Afternoon (0-1 transactions)
            if random.random() > 0.5:
                pool = DAILY_POOLS["afternoon"]
                merchant, (lo, hi), category, icon = random.choice(pool)
                amount = round(random.uniform(lo, hi), 2)
                time = f"{random.randint(14, 18):02d}:{random.randint(0, 59):02d}"
                kg.ingest_transaction(merchant, amount, category, time, "low", month=month)
                await self._emit("transaction", {
                    "merchant": merchant, "amount": amount, "category": category,
                    "icon": icon, "verdict": "SAFE",
                })
                await self._delay(0.5)

            # Evening (food delivery — increasing frequency)
            food_chance = 0.3 + (month * 0.05)  # gets more frequent over time
            if random.random() < food_chance:
                pool = DAILY_POOLS["evening"]
                merchant, (lo, hi), category, icon = random.choice(pool)
                amount = round(random.uniform(lo, hi) * (1 + month * 0.03), 2)
                time = f"{random.randint(18, 22):02d}:{random.randint(0, 59):02d}"
                kg.ingest_transaction(merchant, amount, category, time, "low", month=month)
                await self._emit("transaction", {
                    "merchant": merchant, "amount": amount, "category": category,
                    "icon": icon, "verdict": "SAFE",
                })
                await self._delay(0.4)

            # Tiny delay between simulated "days"
            await self._delay(0.3)

        # === Life Events (random, 0-2 per month) ===
        self.phase = "life_events"
        for event in LIFE_EVENTS:
            if random.random() < event["weight"]:
                data = event["generate"](month)
                merchant = data["merchant"]
                amount = data["amount"]
                alert_type = data["alert_type"]

                if alert_type == "refund":
                    # Credit
                    kg.record_income(merchant, amount, "refund", data["time"], "\U0001F4B0")
                    await self._emit("transaction", {
                        "merchant": merchant, "amount": -amount, "category": "Refund",
                        "icon": "\U0001F4B0", "verdict": "SAFE",
                        "toast": f"Refund: R{amount:,.0f} from {merchant}",
                    })
                elif alert_type == "fraud":
                    kg.ingest_transaction(merchant, amount, data["category"],
                                          data["time"], "critical", month=month)
                    alert_id = f"alert_fraud_{merchant.lower().replace(' ', '_')}_{month}"
                    kg._add_node(alert_id, f"Blocked: {merchant}", "alert", {
                        "severity": "critical", "merchant": merchant,
                        "amount": amount, "time": data["time"],
                        "reason": f"Unknown merchant, suspicious origin, R{amount:,.0f}",
                    })
                    kg._add_edge("user", alert_id, "ALERTED_BY")
                    kg._notify_change()
                    await self._emit("alert", {
                        "type": "fraud",
                        "severity": "critical",
                        "merchant": merchant,
                        "amount": amount,
                        "toast": f"BLOCKED: {merchant} R{amount:,.0f} - Card frozen!",
                        "cardFrozen": True,
                    })
                else:
                    kg.ingest_transaction(merchant, amount, data["category"],
                                          data["time"], data["risk"], month=month)
                    if alert_type in ("emergency", "spike", "unplanned"):
                        alert_id = f"alert_{alert_type}_{month}"
                        kg._add_node(alert_id, f"{alert_type.title()}: {merchant}", "alert", {
                            "severity": "warning",
                            "amount": amount, "merchant": merchant,
                            "reason": f"{data['category']} expense R{amount:,.0f}",
                        })
                        kg._add_edge("user", alert_id, "ALERTED_BY")
                        kg._notify_change()
                    await self._emit("transaction", {
                        "merchant": merchant, "amount": amount,
                        "category": data["category"], "icon": "\u26A0\uFE0F",
                        "verdict": "ALERT" if data["risk"] in ("high", "critical") else "SAFE",
                        "toast": f"{data['category']}: {merchant} R{amount:,.0f}",
                    })

                await self._delay(1)

        # === End of month: Proactive insights ===
        self.phase = "insights"
        insights = _generate_insights()
        if insights:
            await self._emit("insights", {"insights": insights[:3]})

        # Health score update
        health = calculate_health_score()
        await self._emit("health_score", health)

        await self._delay(1)
        self.phase = "idle"


# Singleton
simulator = LifeSimulator()
