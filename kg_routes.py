"""
SentiVest Knowledge Graph API Routes
Mount with: app.include_router(kg_router, prefix="/api/kg")
"""

from fastapi import APIRouter, Body
from knowledge_graph import kg

kg_router = APIRouter()


@kg_router.post("/query")
async def kg_query(body: dict = Body(...)):
    text = body.get("text", "")
    result = kg.query(text)
    graph_path = []
    return {**result, "graph_path": graph_path}


@kg_router.post("/ingest")
async def kg_ingest(body: dict = Body(...)):
    merchant = body.get("merchant", "Unknown")
    amount = float(body.get("amount", 0))
    category = body.get("category", "Unknown")
    time = body.get("time", "12:00")
    risk = body.get("risk_level", "low")

    report = kg.ingest_transaction(merchant, amount, category, time, risk)
    return {"report": report, "stats": kg.get_stats()}


@kg_router.post("/ingest/batch")
async def kg_ingest_batch(body: dict = Body(...)):
    transactions = body.get("transactions", [])
    reports = []
    for txn in transactions:
        report = kg.ingest_transaction(
            txn.get("merchant", "Unknown"),
            float(txn.get("amount", 0)),
            txn.get("category", "Unknown"),
            txn.get("time", "12:00"),
            txn.get("risk_level", "low")
        )
        reports.append(report)
    return {"count": len(reports), "reports": reports, "stats": kg.get_stats()}


@kg_router.post("/scenario")
async def kg_scenario(body: dict = Body(...)):
    scenario_type = body.get("type", "")
    params = {k: v for k, v in body.items() if k != "type"}
    result = kg.run_scenario(scenario_type, **params)
    return result


@kg_router.get("/visualize")
async def kg_visualize():
    return kg.visualize()


@kg_router.get("/stats")
async def kg_stats():
    return kg.get_stats()


@kg_router.get("/export")
async def kg_export():
    return kg.export_full()


@kg_router.get("/patterns")
async def kg_patterns():
    return {"patterns": kg.get_patterns()}


@kg_router.get("/predictions")
async def kg_predictions():
    return {"predictions": kg.get_predictions()}


@kg_router.get("/subscriptions")
async def kg_subscriptions():
    return {"subscriptions": kg.get_subscriptions()}


@kg_router.get("/budgets")
async def kg_budgets():
    return {"budgets": kg.get_budgets()}


@kg_router.get("/traverse/{node_id}")
async def kg_traverse(node_id: str, depth: int = 2):
    return kg.traverse(node_id, depth)


@kg_router.get("/node/{node_id}")
async def kg_node(node_id: str):
    result = kg.get_node(node_id)
    if result is None:
        return {"error": "Node not found"}
    return result


@kg_router.post("/budget")
async def kg_add_budget(body: dict = Body(...)):
    category = body.get("category", "")
    limit_amount = float(body.get("limit", 0))
    period = body.get("period", "month")
    return kg.add_budget(category, limit_amount, period)


@kg_router.post("/goal")
async def kg_add_goal(body: dict = Body(...)):
    name = body.get("name", "")
    target = float(body.get("target", 0))
    monthly = float(body.get("monthly_contribution", body.get("monthly", 0)))
    return kg.add_goal(name, target, monthly)


@kg_router.post("/seed")
async def kg_seed():
    result = kg.seed_demo_data()
    return result


# ==================== Account Endpoints ====================

@kg_router.get("/accounts")
async def kg_accounts():
    return {"accounts": kg.list_accounts()}


@kg_router.get("/accounts/active")
async def kg_active_account():
    return kg.get_account()


@kg_router.post("/accounts/switch")
async def kg_switch_account(body: dict = Body(...)):
    account_id = body.get("account_id", "")
    result = kg.switch_account(account_id)
    return result


@kg_router.post("/accounts")
async def kg_create_account(body: dict = Body(...)):
    import uuid
    account_id = body.get("id", f"acc_{uuid.uuid4().hex[:8]}")
    name = body.get("name", "New Account")
    acct_type = body.get("type", "cheque")
    balance = float(body.get("balance", 0))
    available = float(body.get("available", balance))
    salary = float(body.get("salary", 0))
    salary_day = int(body.get("salary_day", 25))
    last4 = body.get("last4", f"{hash(name) % 10000:04d}")
    color = body.get("color", "#6366F1")
    result = kg.create_account(account_id, name, acct_type, balance, available,
                                salary, salary_day, last4, color)
    return result


# ==================== New Endpoints ====================

@kg_router.post("/income")
async def kg_add_income(body: dict = Body(...)):
    source = body.get("source", "")
    amount = float(body.get("amount", 0))
    frequency = body.get("frequency", "monthly")
    income_type = body.get("type", "salary")
    return kg.add_income(source, amount, frequency, income_type)


@kg_router.post("/loan")
async def kg_add_loan(body: dict = Body(...)):
    name = body.get("name", "")
    principal = float(body.get("principal", 0))
    rate = float(body.get("rate", 0))
    term = int(body.get("term_months", 60))
    balance = float(body.get("balance", principal))
    loan_type = body.get("type", "personal")
    return kg.add_loan(name, principal, rate, term, balance, loan_type)


@kg_router.post("/investment")
async def kg_add_investment(body: dict = Body(...)):
    name = body.get("name", "")
    invested = float(body.get("invested", 0))
    current_value = float(body.get("current_value", invested))
    asset_type = body.get("type", "etf")
    return kg.add_investment(name, invested, current_value, asset_type)


@kg_router.post("/insurance")
async def kg_add_insurance(body: dict = Body(...)):
    provider = body.get("provider", "")
    insurance_type = body.get("type", "health")
    premium = float(body.get("premium", 0))
    coverage = float(body.get("coverage", 0))
    renewal = body.get("renewal", "")
    return kg.add_insurance(provider, insurance_type, premium, coverage, renewal)


@kg_router.post("/tax")
async def kg_add_tax(body: dict = Body(...)):
    name = body.get("name", "")
    amount = float(body.get("amount", 0))
    tax_type = body.get("type", "income")
    category = body.get("category", "")
    return kg.add_tax_item(name, amount, tax_type, category)


@kg_router.get("/loans")
async def kg_loans():
    return {"loans": kg.get_loans()}


@kg_router.get("/investments")
async def kg_investments():
    return {"investments": kg.get_investments()}


@kg_router.get("/insurance")
async def kg_insurance():
    return {"insurance": kg.get_insurance()}
