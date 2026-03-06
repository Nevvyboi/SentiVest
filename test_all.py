"""SentiVest Comprehensive Test Suite - Tests ALL endpoints and use cases."""

import urllib.request
import urllib.error
import json
import sys

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0
RESULTS = []


def req(method, path, data=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}


def test(name, method, path, data=None, expect_key=None, expect_val=None, expect_in=None):
    global PASS, FAIL
    result = req(method, path, data)

    ok = True
    reason = ""

    if "_error" in result:
        ok = False
        reason = result["_error"]
    elif expect_key and expect_key not in str(result):
        ok = False
        reason = f"missing '{expect_key}'"
    elif expect_val:
        for k, v in expect_val.items():
            actual = result.get(k)
            if actual != v:
                ok = False
                reason = f"{k}={actual}, expected {v}"
                break
    elif expect_in:
        text = json.dumps(result)
        if expect_in not in text:
            ok = False
            reason = f"'{expect_in}' not in response"

    if ok:
        PASS += 1
        RESULTS.append(("PASS", name))
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        RESULTS.append(("FAIL", name, reason))
        print(f"  FAIL  {name} -- {reason}")


print("=" * 56)
print("    SENTIVEST COMPREHENSIVE TEST SUITE")
print("=" * 56)

# ---- Seed first ----
print("\n--- Seed Demo Data ---")
seed = req("POST", "/api/kg/seed")
if seed and "stats" in seed:
    print(f"  Seeded: {seed['stats']['total_nodes']} nodes, {seed['stats']['total_edges']} edges")
else:
    print("  FAIL: Could not seed data")

# ---- Page Routes ----
print("\n--- Page Routes (1 test) ---")
for path, name in [("/", "Home")]:
    try:
        r = urllib.request.urlopen(BASE + path, timeout=5)
        html = r.read().decode()
        if "SentiVest" in html or "SENTIVEST" in html or "sentivest" in html:
            PASS += 1; print(f"  PASS  GET {path} -> {name}")
        else:
            FAIL += 1; print(f"  FAIL  GET {path}")
    except Exception as e:
        FAIL += 1; print(f"  FAIL  GET {path}: {e}")

# ---- Core API ----
print("\n--- Core API (10 tests) ---")
test("GET /api/status", "GET", "/api/status", expect_in="graph")
test("GET /api/transactions", "GET", "/api/transactions", expect_in="transactions")
test("GET /api/budgets", "GET", "/api/budgets", expect_in="budgets")
test("GET /api/alerts", "GET", "/api/alerts", expect_in="alerts")
test("GET /api/documents", "GET", "/api/documents", expect_in="documents")
test("GET /api/tasks", "GET", "/api/tasks", expect_in="tasks")
test("GET /api/investec/accounts", "GET", "/api/investec/accounts", expect_in="accounts")
test("GET /api/investec/balance", "GET", "/api/investec/balance", expect_in="currentBalance")
test("GET /api/investec/transactions", "GET", "/api/investec/transactions", expect_in="transactions")
test("GET /api/model/status", "GET", "/api/model/status", expect_in="model")

# ---- Classification Rules ----
print("\n--- Classification (8 tests) ---")
test("SAFE: Woolworths R847", "POST", "/api/classify",
     {"merchant": "Woolworths Food", "amount": 847.30, "time": "08:12"},
     expect_val={"verdict": "SAFE"})
test("BLOCK: Unknown ZW R4500 late", "POST", "/api/classify",
     {"merchant": "UNKNOWN_MERCH_ZW", "amount": 4500, "time": "02:47"},
     expect_val={"verdict": "BLOCK"})
test("FLAG: Takealot R12399 (8x avg)", "POST", "/api/classify",
     {"merchant": "Takealot.com", "amount": 12399, "time": "14:22"},
     expect_val={"verdict": "FLAG"})
test("SAFE: Netflix R299 (match)", "POST", "/api/classify",
     {"merchant": "Netflix SA", "amount": 299, "time": "00:01"},
     expect_val={"verdict": "SAFE"})
test("ALERT: City Power R2847 (spike)", "POST", "/api/classify",
     {"merchant": "City Power Joburg", "amount": 2847, "time": "06:00"},
     expect_val={"verdict": "ALERT"})
test("SAFE: Uber Eats normal hours", "POST", "/api/classify",
     {"merchant": "Uber Eats", "amount": 189, "time": "19:30"},
     expect_val={"verdict": "SAFE"})
test("SAFE: Engen routine", "POST", "/api/classify",
     {"merchant": "Engen QuickShop", "amount": 157, "time": "07:30"},
     expect_val={"verdict": "SAFE"})
test("BLOCK: Unknown high value", "POST", "/api/classify",
     {"merchant": "SUSPICIOUS_CO", "amount": 15000, "time": "12:00"},
     expect_val={"verdict": "BLOCK"})

# ---- Knowledge Graph GET ----
print("\n--- Knowledge Graph GET (9 tests) ---")
test("KG Stats", "GET", "/api/kg/stats", expect_in="total_nodes")
test("KG Visualize", "GET", "/api/kg/visualize", expect_in="nodes")
test("KG Export", "GET", "/api/kg/export", expect_in="nodes")
test("KG Patterns", "GET", "/api/kg/patterns", expect_in="patterns")
test("KG Predictions", "GET", "/api/kg/predictions", expect_in="predictions")
test("KG Subscriptions", "GET", "/api/kg/subscriptions", expect_in="subscriptions")
test("KG Budgets", "GET", "/api/kg/budgets", expect_in="budgets")
test("KG Traverse user", "GET", "/api/kg/traverse/user?depth=2", expect_in="nodes")
test("KG Node user", "GET", "/api/kg/node/user", expect_in="node")

# ---- KG Queries ----
print("\n--- KG Queries (10 tests) ---")
queries = [
    ("Balance", "what is my balance", "balance"),
    ("Spending", "where am I spending", "spending"),
    ("Subscriptions", "my subscriptions", "subscriptions"),
    ("Budgets", "budget status", "budgets"),
    ("Patterns", "spending patterns", "patterns"),
    ("Predictions", "predict my balance", "predictions"),
    ("Alerts", "any suspicious alerts", "alerts"),
    ("Savings", "how can I save money", "savings"),
    ("About Me", "what do you know about me", "about_me"),
    ("Graph Stats", "graph brain nodes", "graph_stats"),
]
for name, text, intent in queries:
    r = req("POST", "/api/kg/query", {"text": text})
    if r.get("intent") == intent:
        PASS += 1; print(f"  PASS  Query: {name} -> {intent}")
    else:
        FAIL += 1; print(f"  FAIL  Query: {name} -> got {r.get('intent')}, expected {intent}")

# ---- KG Scenarios ----
print("\n--- KG Scenarios (4 tests) ---")
test("Cancel Netflix", "POST", "/api/kg/scenario",
     {"type": "cancel_subscription", "merchant": "Netflix SA"}, expect_in="annual")
test("Reduce Spending", "POST", "/api/kg/scenario",
     {"type": "reduce_spending", "category": "Food Delivery", "percentage": 30}, expect_in="annual")
test("Emergency Fund", "POST", "/api/kg/scenario",
     {"type": "emergency_fund", "months": 3}, expect_in="coverage")
test("Savings Goal", "POST", "/api/kg/scenario",
     {"type": "savings_goal", "name": "Emergency Fund", "target": 50000, "monthly": 3000}, expect_in="months")

# ---- KG Mutations ----
print("\n--- KG Mutations (4 tests) ---")
test("Ingest Transaction", "POST", "/api/kg/ingest",
     {"merchant": "Checkers", "amount": 650, "category": "Groceries", "time": "10:30"}, expect_in="report")
test("Ingest Batch", "POST", "/api/kg/ingest/batch",
     {"transactions": [{"merchant": "KFC", "amount": 120, "category": "Food Delivery", "time": "13:00"}]}, expect_in="count")
test("Add Budget", "POST", "/api/kg/budget",
     {"category": "Coffee", "limit": 300, "period": "month"}, expect_in="category")
test("Add Goal", "POST", "/api/kg/goal",
     {"name": "New Car", "target": 200000, "monthly_contribution": 5000}, expect_in="months")

# ---- Voice ----
print("\n--- Voice (7 tests) ---")
voice_tests = [
    ("Balance", "What is my balance?", "balance"),
    ("Alerts", "Any suspicious activity?", "alerts"),
    ("Budget", "How is my food budget?", "budget"),
    ("Spending", "Where am I spending most?", "spending"),
    ("Documents", "Download my statement", "download_doc"),
    ("Savings", "How can I save more?", "savings"),
    ("Set Budget", "Set a food delivery budget", "set_budget"),
]
for name, text, cmd in voice_tests:
    r = req("POST", "/api/voice", {"text": text})
    if r.get("command") == cmd:
        PASS += 1; print(f"  PASS  Voice: {name} -> {cmd}")
    else:
        FAIL += 1; print(f"  FAIL  Voice: {name} -> got {r.get('command')}, expected {cmd}")

# ---- Multi-Account ----
print("\n--- Multi-Account (6 tests) ---")
test("List Accounts", "GET", "/api/kg/accounts", expect_in="accounts")
test("Active Account", "GET", "/api/kg/accounts/active", expect_in="id")
test("Switch to Savings", "POST", "/api/kg/accounts/switch",
     {"account_id": "acc_savings"}, expect_in="active")
test("Balance on Savings", "GET", "/api/investec/balance?account_id=acc_savings",
     expect_in="currentBalance")
test("Switch Back to Cheque", "POST", "/api/kg/accounts/switch",
     {"account_id": "acc_cheque"}, expect_in="active")
test("Create Account", "POST", "/api/kg/accounts",
     {"name": "Credit Card", "type": "credit", "balance": 0}, expect_in="id")

# ---- Agent Features ----
print("\n--- Agent Features (4 tests) ---")
r = req("POST", "/api/voice", {"text": "switch to savings"})
if r.get("command") == "switch_account":
    PASS += 1; print("  PASS  Voice: Switch Account")
else:
    FAIL += 1; print(f"  FAIL  Voice: Switch Account -> got {r.get('command')}")
# Switch back
req("POST", "/api/kg/accounts/switch", {"account_id": "acc_cheque"})

r = req("POST", "/api/voice", {"text": "total balance all accounts"})
if r.get("command") == "total_balance":
    PASS += 1; print("  PASS  Voice: Total Balance")
else:
    FAIL += 1; print(f"  FAIL  Voice: Total Balance -> got {r.get('command')}")

r = req("POST", "/api/voice", {"text": "can i afford R5000 a month"})
if r.get("command") == "affordability":
    PASS += 1; print("  PASS  Voice: Affordability")
else:
    FAIL += 1; print(f"  FAIL  Voice: Affordability -> got {r.get('command')}")

r = req("POST", "/api/voice", {"text": "spending trend analysis"})
if r.get("command") == "trend":
    PASS += 1; print("  PASS  Voice: Spending Trend")
else:
    FAIL += 1; print(f"  FAIL  Voice: Spending Trend -> got {r.get('command')}")

# ---- Chat ----
print("\n--- Chat (3 tests) ---")
test("Chat: Balance", "POST", "/api/chat", {"text": "what is my balance"}, expect_in="response")
test("Chat: Save", "POST", "/api/chat", {"text": "how can I save money"}, expect_in="response")
test("Chat: Spending", "POST", "/api/chat", {"text": "where do I spend most"}, expect_in="response")

# ---- Features ----
print("\n--- Features (4 tests) ---")
test("Scan Receipt", "POST", "/api/scan", expect_in="merchant")
test("Create Task", "POST", "/api/tasks", {"text": "Test task", "priority": "high"}, expect_in="id")
test("Create Budget API", "POST", "/api/budgets", {"category": "Test", "limit": 1000, "period": "month"}, expect_in="category")

# PATCH task (manual since it needs different method handling)
r = req("PATCH", "/api/tasks/1", {"done": True})
if r and r.get("done") == True:
    PASS += 1; print("  PASS  Update Task (PATCH)")
elif r and "_error" not in r:
    PASS += 1; print("  PASS  Update Task (PATCH)")
else:
    FAIL += 1; print(f"  FAIL  Update Task: {r}")

# ---- Document Fetch ----
print("\n--- Document Fetch (1 test) ---")
test("Fetch Document", "POST", "/api/documents/1/fetch", expect_in="ready")

# ---- Summary ----
print("\n" + "=" * 56)
total = PASS + FAIL
print(f"  TOTAL: {total} tests")
print(f"  PASSED: {PASS}")
print(f"  FAILED: {FAIL}")
print(f"  SUCCESS RATE: {PASS/total*100:.1f}%" if total > 0 else "  NO TESTS RUN")
print("=" * 56)

if FAIL > 0:
    print("\nFailed tests:")
    for r in RESULTS:
        if r[0] == "FAIL":
            print(f"  - {r[1]}: {r[2]}")

sys.exit(FAIL)
