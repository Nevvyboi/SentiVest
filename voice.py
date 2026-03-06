"""
SentiVest Voice AI Agent
Conversational AI with action capabilities — powered by knowledge graph data.
Handlers gather real data, AI model generates natural responses.
Persistent memory across server restarts.
"""

from knowledge_graph import kg
from model import model
from simulator import assess_loan_eligibility, calculate_health_score, execute_transfer
import agent
import json
import os
from datetime import datetime

import re
import asyncio
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


# ==================== CONVERSATION FLOW STATE ====================
# Multi-turn conversation state machine for dynamic interactions
_flow_state = {
    "active": None,       # Current flow: "payment", "add_beneficiary", etc.
    "step": None,         # Current step in the flow
    "data": {},           # Accumulated data for the flow
    "expires": None,      # Auto-expire stale flows
}

def _reset_flow():
    _flow_state["active"] = None
    _flow_state["step"] = None
    _flow_state["data"] = {}
    _flow_state["expires"] = None

def _set_flow(flow: str, step: str, data: dict = None):
    _flow_state["active"] = flow
    _flow_state["step"] = step
    _flow_state["data"] = data or _flow_state["data"]
    _flow_state["expires"] = datetime.now().timestamp() + 120  # 2 min timeout

def _flow_active() -> bool:
    if not _flow_state["active"]:
        return False
    if _flow_state["expires"] and datetime.now().timestamp() > _flow_state["expires"]:
        _reset_flow()
        return False
    return True


# ==================== PERSISTENT MEMORY ====================
_memory = {
    "conversations": [],   # [{role, text, intent, timestamp}]
    "facts": [],           # AI-extracted facts about the user: ["prefers savings", "worried about debt"]
    "preferences": {},     # {key: value} user preferences
    "summary": "",         # Rolling summary of past conversations
}
MAX_CONVERSATIONS = 100   # keep last 100 messages on disk
MAX_CONTEXT_MSGS = 20     # send last 20 to AI


def _load_memory():
    """Load persistent memory from disk."""
    global _memory
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            _memory["conversations"] = loaded.get("conversations", [])
            _memory["facts"] = loaded.get("facts", [])
            _memory["preferences"] = loaded.get("preferences", {})
            _memory["summary"] = loaded.get("summary", "")
        except (json.JSONDecodeError, IOError):
            pass


def _save_memory():
    """Persist memory to disk."""
    # Trim conversations before saving
    _memory["conversations"] = _memory["conversations"][-MAX_CONVERSATIONS:]
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_memory, f, indent=2, ensure_ascii=False)
    except IOError:
        pass


def _add_message(role: str, text: str, intent: str = ""):
    """Add a message to persistent memory."""
    _memory["conversations"].append({
        "role": role,
        "text": text,
        "intent": intent,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def _extract_facts(user_text: str, response: str, intent: str):
    """Extract memorable facts from conversation. Simple heuristic-based."""
    text_lower = user_text.lower()

    # Skip if this came from the explicit "remember" handler (already stored)
    if intent == "remember":
        return

    # Detect user preferences / personal info
    fact_triggers = [
        (["my name is", "i'm called", "call me"], lambda t: f"User's name: {t.lower().split('is')[-1].split('called')[-1].strip().title()}" if 'is' in t.lower() or 'called' in t.lower() else None),
        (["i prefer", "i like", "i always"], lambda t: f"Preference: {t}"),
        (["i'm saving for", "i am saving for", "saving up for", "i want to buy", "i want to save"], lambda t: f"Goal: {t}"),
        (["i'm worried about", "i am worried about", "concerned about", "stressed about"], lambda t: f"Concern: {t}"),
        (["i work at", "i'm at", "my job is", "i am a"], lambda t: f"Work: {t}"),
        (["i live in", "i stay in", "i'm from", "i am from"], lambda t: f"Location: {t}"),
    ]

    for triggers, extractor in fact_triggers:
        if any(t in text_lower for t in triggers):
            fact = extractor(user_text)
            if fact:
                # Dedup: check if similar fact exists (case-insensitive)
                existing = [f.lower() for f in _memory["facts"]]
                if fact.lower() not in existing:
                    _memory["facts"].append(fact)
                    if len(_memory["facts"]) > 30:
                        _memory["facts"] = _memory["facts"][-30:]
            break


def _build_memory_context() -> str:
    """Build memory context string for AI prompts."""
    parts = []

    # Rolling summary of past conversations
    if _memory["summary"]:
        parts.append(f"Previous conversation summary: {_memory['summary']}")

    # Known facts about user
    if _memory["facts"]:
        parts.append("Known facts about user: " + "; ".join(_memory["facts"][-10:]))

    # User preferences
    if _memory["preferences"]:
        prefs = ", ".join(f"{k}: {v}" for k, v in _memory["preferences"].items())
        parts.append(f"User preferences: {prefs}")

    # Recent conversation (last few exchanges)
    recent = _memory["conversations"][-MAX_CONTEXT_MSGS:]
    if recent:
        convo_lines = []
        for m in recent:
            ts = m.get("timestamp", "")
            prefix = "User" if m["role"] == "user" else "SentiVest"
            convo_lines.append(f"[{ts}] {prefix}: {m['text']}")
        parts.append("Recent conversation:\n" + "\n".join(convo_lines))

    return "\n\n".join(parts)


async def _update_summary():
    """Periodically update the rolling conversation summary using AI."""
    import asyncio
    # Only summarize every 20 messages
    if len(_memory["conversations"]) % 20 != 0 or len(_memory["conversations"]) < 20:
        return

    # Get the last 20 messages to summarize
    recent = _memory["conversations"][-20:]
    convo = "\n".join(f"{'User' if m['role'] == 'user' else 'AI'}: {m['text']}" for m in recent)
    old_summary = _memory["summary"]

    prompt = (
        f"Previous summary: {old_summary}\n\n"
        f"New conversation:\n{convo}\n\n"
        "Update the summary with key facts, user preferences, concerns, and financial decisions. "
        "Keep it under 200 words. Focus on what the user cares about and what they've asked for."
    )

    try:
        new_summary = await asyncio.wait_for(
            model.generate(prompt, "", "voice", 0.3), timeout=10
        )
        if new_summary and len(new_summary) > 20:
            _memory["summary"] = new_summary
    except Exception:
        pass


# Load memory on module import
_load_memory()


def get_history():
    return _memory["conversations"][-MAX_CONTEXT_MSGS:]


def clear_history():
    _memory["conversations"] = []
    _memory["facts"] = []
    _memory["summary"] = ""
    _save_memory()


# ==================== VOICE COMMANDS ====================
VOICE_COMMANDS = [
    # Memory triggers (highest priority)
    {"trigger": ["remember that", "remember my", "remember i", "don't forget", "keep in mind"],
     "handler": "remember", "display": "Remember that I prefer savings"},
    {"trigger": ["what do you remember", "what do you know about me", "do you remember", "my memory", "your memory", "forget everything", "clear memory"],
     "handler": "recall_memory", "display": "What do you remember about me?"},
    # Action triggers (these DO things)
    {"trigger": ["remind me", "add task", "create task", "new task", "create reminder", "set reminder", "add reminder"],
     "handler": "add_task", "display": "Remind me to pay rent"},
    {"trigger": ["complete task", "mark task", "task done", "finished with"],
     "handler": "complete_task", "display": "Mark my first task as done"},
    {"trigger": ["download statement", "download my", "get my statement", "fetch statement",
                  "download tax", "get tax", "tax certificate", "download proof", "fetch document",
                  "download doc", "get my tax", "fetch my"],
     "handler": "download_doc", "display": "Download my statement"},
    {"trigger": ["trust", "trustworthy", "not fraud", "legitimate", "approve transaction",
                  "unblock merchant", "it's safe", "it's fine", "not suspicious", "i know that merchant"],
     "handler": "trust_merchant", "display": "That merchant is trustworthy"},
    {"trigger": ["dismiss alert", "remove alert", "clear alert", "remove warning", "ignore alert", "dismiss that"],
     "handler": "dismiss_alert", "display": "Dismiss that alert"},
    {"trigger": ["block merchant", "this is fraud", "block this", "report fraud", "freeze card"],
     "handler": "block_merchant", "display": "Block this merchant"},
    # Multi-word action triggers
    {"trigger": ["set budget", "create budget", "new budget", "set a budget"],
     "handler": "set_budget", "display": "Set a food delivery budget"},
    {"trigger": ["set goal", "create goal", "new goal", "save for"],
     "handler": "set_goal", "display": "Set a savings goal"},
    {"trigger": ["cancel subscription", "cancel netflix", "unsubscribe", "stop paying"],
     "handler": "cancel_subscription", "display": "Cancel a subscription"},
    # Domain-specific triggers
    {"trigger": ["loan", "debt", "mortgage", "repay", "owe"],
     "handler": "loan", "display": "What's my loan status?"},
    {"trigger": ["invest", "portfolio", "stock", "share", "dividend", "etf"],
     "handler": "investment", "display": "How are my investments?"},
    {"trigger": ["insurance", "premium", "claim", "coverage"],
     "handler": "insurance", "display": "Insurance overview"},
    {"trigger": ["tax", "sars", "deduction", "capital gain"],
     "handler": "tax", "display": "Tax summary"},
    {"trigger": ["income", "salary", "earn", "freelance"],
     "handler": "income", "display": "What's my income?"},
    {"trigger": ["switch account", "savings account", "cheque account", "switch to"],
     "handler": "switch_account", "display": "Switch to savings account"},
    {"trigger": ["total balance", "all accounts", "combined balance", "overall balance"],
     "handler": "total_balance", "display": "What's my total balance?"},
    {"trigger": ["afford", "can i afford", "new loan", "affordability"],
     "handler": "affordability", "display": "Can I afford R5,000/month?"},
    {"trigger": ["spending trend", "why is my spending", "trend analysis"],
     "handler": "trend", "display": "What's my spending trend?"},
    {"trigger": ["recurring", "debit order", "subscription list", "regular payment"],
     "handler": "recurring", "display": "My recurring payments"},
    {"trigger": ["make a payment", "make payment", "payment to", "send money to", "eft to", "pay someone"],
     "handler": "pay", "display": "Pay R500 to Mom"},
    {"trigger": ["beneficiar", "who can i pay", "saved beneficiar", "my beneficiar"],
     "handler": "beneficiaries", "display": "Show my beneficiaries"},
    {"trigger": ["transfer", "move money", "move r"],
     "handler": "smart_transfer", "display": "Transfer R5,000 to savings"},
    {"trigger": ["eligible", "qualify", "loan application", "can i get a loan", "apply for"],
     "handler": "loan_eligibility", "display": "Am I eligible for a R500K loan?"},
    {"trigger": ["health score", "financial health", "how am i doing", "financial score", "my score"],
     "handler": "health_score", "display": "What's my financial health score?"},
    {"trigger": ["compare month", "last month", "month over month", "versus last"],
     "handler": "compare_months", "display": "Compare to last month"},
    {"trigger": ["start simulation", "start sim", "simulate", "run simulation", "auto mode"],
     "handler": "start_sim", "display": "Start the life simulator"},
    {"trigger": ["stop simulation", "stop sim", "pause sim", "stop auto"],
     "handler": "stop_sim", "display": "Stop the simulation"},
    {"trigger": ["pattern", "habit"],
     "handler": "pattern", "display": "Show my patterns"},
    {"trigger": ["predict", "forecast", "future"],
     "handler": "prediction", "display": "Balance forecast"},
    # General triggers
    {"trigger": ["alert", "suspicious", "fraud", "blocked", "danger", "stolen"],
     "handler": "alerts", "display": "Any suspicious activity?"},
    {"trigger": ["budget", "food delivery", "limit", "over budget"],
     "handler": "budget", "display": "How's my food budget?"},
    {"trigger": ["statement", "document", "proof"],
     "handler": "documents", "display": "Download my statement"},
    {"trigger": ["spend", "spent", "spending", "where"],
     "handler": "spending", "display": "Where am I spending most?"},
    {"trigger": ["save", "saving", "emergency fund"],
     "handler": "savings", "display": "How can I save more?"},
    {"trigger": ["balance", "how much", "money", "account"],
     "handler": "balance", "display": "What's my balance?"},
]


# ==================== AI RESPONSE HELPER ====================

async def _ai_respond(user_text: str, intent: str, data_summary: str, template: str) -> str:
    """Generate AI response using real data + persistent memory. Falls back to template."""
    import asyncio
    memory_context = _build_memory_context()

    prompt = (
        f"{memory_context}\n\n"
        f"User says: \"{user_text}\"\n"
        f"Intent detected: {intent}\n"
        f"Relevant financial data:\n{data_summary}\n\n"
        f"Respond like a friendly personal banker having a conversation. Be specific with numbers. "
        f"1-3 sentences max — this is spoken aloud. Use contractions. Sound warm and human. "
        f"If you know the user's name from memory, use it naturally. Give brief advice when helpful."
    )

    context = kg.build_context()
    try:
        response = await asyncio.wait_for(
            model.generate_voice_response(prompt, context), timeout=15
        )
    except (asyncio.TimeoutError, Exception):
        return template

    # If model returned a generic/empty response, use template
    if not response or len(response) < 10 or "I'm SentiVest" in response:
        response = template

    return response


def _get_user_name() -> str:
    for f in _memory.get("facts", []):
        fl = f.lower()
        if fl.startswith("user's name:") or fl.startswith("my name is"):
            return f.split(":")[-1].strip().split("is")[-1].strip().title()
    return ""

def _smart_fallback(text: str) -> str:
    """Data-driven fallback when AI model is slow. Uses KG data to answer common questions."""
    tl = text.lower()
    name = _get_user_name()
    greeting = f"{name}, " if name else ""
    acct = kg.accounts.get(kg.active_account_id, {})
    bal = acct.get("balance", 0)

    # Detect what they're asking about and give a real answer
    if any(w in tl for w in ["how am i doing", "how are things", "overview", "this month", "summary"]):
        spent = kg.total_spent
        alerts = sum(1 for n in kg.nodes.values() if n.type == "alert" and n.attrs.get("status") == "active")
        return (f"Hey {greeting}your balance is R{bal:,.2f}. "
                f"You've spent R{spent:,.0f} so far. "
                f"{'You have ' + str(alerts) + ' alerts to review.' if alerts else 'No urgent alerts.'}")

    if any(w in tl for w in ["worried", "concern", "stress", "anxious"]):
        loans = [n for n in kg.nodes.values() if n.type == "loan"]
        total_debt = sum(n.attrs.get("balance", 0) for n in loans)
        return (f"Hey {greeting}I hear you. Your total debt is R{total_debt:,.0f} across {len(loans)} loans. "
                f"Your balance is R{bal:,.2f}. Let's look at this together — ask me about your health score for a full picture.")

    if any(w in tl for w in ["advice", "suggest", "recommend", "should i", "what do you think"]):
        return (f"Hey {greeting}based on your profile, I'd say focus on building that emergency fund. "
                f"Your balance is R{bal:,.2f}. Say 'health score' for a full financial checkup.")

    if any(w in tl for w in ["thank", "thanks", "cheers", "great"]):
        return f"Anytime, {greeting.rstrip(', ')}! I'm here whenever you need me."

    if any(w in tl for w in ["hello", "hi ", "hey", "good morning", "good afternoon", "howzit"]):
        return f"Hey {greeting.rstrip(', ')}! Your balance is R{bal:,.2f}. What can I help you with?"

    if any(w in tl for w in ["bye", "goodbye", "see you", "later"]):
        return f"Take care, {greeting.rstrip(', ')}! Your finances are in good hands."

    # Generic but still warm
    return (f"Hey {greeting}your balance is R{bal:,.2f}. "
            f"I can help with payments, budgets, transfers, loans, and more. What would you like to do?")


# ==================== MAIN ROUTER ====================

async def route(text: str) -> dict:
    """Route voice/text command → gather data → AI response → store history."""
    text_lower = text.lower().strip()

    # Store user message in persistent memory
    _add_message("user", text)

    # Check for active multi-turn flow (payment, etc.)
    handler_result = None
    if _flow_active():
        handler_result = await _handle_flow_continue(text)

    # Fast-path: keyword matching
    if not handler_result:
        for cmd in VOICE_COMMANDS:
            if any(t in text_lower for t in cmd["trigger"]):
                handler = HANDLERS.get(cmd["handler"])
                if handler:
                    handler_result = await handler(text_lower)
                    break

    # Smart "pay [name]" / "send [name]" detection (not caught by keyword triggers)
    if not handler_result and re.match(r'^(?:pay|send)\s+(?!my\s|the\s|off\s|for\s|attention)', text_lower):
        handler_result = await _handle_pay(text_lower)

    # AI path: intent detection for unmatched commands
    if not handler_result:
        import asyncio
        context = kg.build_context()
        try:
            intent_result = await asyncio.wait_for(
                model.generate_structured(text, context), timeout=12
            )
        except (asyncio.TimeoutError, Exception):
            intent_result = {"intent": "general_query", "entities": {}, "confidence": 0.5}
        intent = intent_result.get("intent", "general_query")

        handler = HANDLERS.get(intent)
        if handler:
            handler_result = await handler(text_lower)
        else:
            # Free-form question — use slim context for faster AI response
            memory_context = _build_memory_context()
            acct = kg.accounts.get(kg.active_account_id, {})
            slim = (f"Balance: R{acct.get('balance',0):,.2f}, Available: R{acct.get('available',0):,.2f}. "
                    f"Salary: R{acct.get('salary',0):,.0f}. Total spent: R{kg.total_spent:,.0f}.\n"
                    f"{memory_context}")
            full_context = slim
            try:
                response = await asyncio.wait_for(
                    model.generate_voice_response(text, full_context), timeout=15
                )
            except (asyncio.TimeoutError, Exception):
                # Smart fallback — give data-driven answer from KG
                response = _smart_fallback(text)
            handler_result = {
                "command": intent,
                "recognized": text,
                "response": response,
                "data": {},
                "intent": intent,
                "action": None,
            }

    # Generate AI-enhanced response for query handlers (skip for actions — they have good templates)
    if handler_result.get("data_summary") and not handler_result.get("action"):
        ai_response = await _ai_respond(
            text, handler_result["intent"],
            handler_result["data_summary"],
            handler_result["response"]  # template fallback
        )
        handler_result["response"] = ai_response

    # Store assistant response in persistent memory
    _add_message("assistant", handler_result["response"], handler_result.get("intent", ""))

    # Extract facts from conversation
    _extract_facts(text, handler_result["response"], handler_result.get("intent", ""))

    # Persist to disk
    _save_memory()

    # Periodically update rolling summary
    await _update_summary()

    # Add history to response
    handler_result["history"] = get_history()

    return handler_result


# ==================== DATA HANDLERS (gather data for AI) ====================

async def _handle_balance(text: str) -> dict:
    result = kg.query("what's my balance")
    acct = kg.get_account()
    acct_name = acct.get("name", "account")
    data = (f"Account: {acct_name}. Balance: R{kg.balance:,.2f}, Available: R{kg.available:,.2f}, "
            f"Salary: R{kg.salary:,.2f} on the {kg.salary_day}th. "
            f"Demo month: {kg.get_demo_date_str()}.")
    return {
        "command": "balance", "recognized": text, "intent": "balance",
        "data": result.get("data", {}), "action": None,
        "data_summary": data,
        "response": f"Your {acct_name} balance is R{kg.balance:,.2f} with R{kg.available:,.2f} available. "
                     f"Your salary of R{kg.salary:,.2f} arrives on the {kg.salary_day}th.",
    }


async def _handle_alerts(text: str) -> dict:
    result = kg.query("any alerts")
    alerts = result.get("data", {}).get("alerts", [])
    critical = [a for a in alerts if a.get("severity") in ("critical", "warning")]
    alert_names = [n.label for n in kg.nodes.values() if n.type == "alert"]
    data = f"Active alerts: {len(alert_names)}. " + ", ".join(alert_names[:5]) if alert_names else "No alerts."
    template = f"You have {len(critical)} critical alerts. " + ". ".join(a.get("name", "") for a in critical[:3]) + "." if critical else "No critical alerts. All transactions look normal."
    return {
        "command": "alerts", "recognized": text, "intent": "alerts",
        "data": result.get("data", {}), "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_budget(text: str) -> dict:
    result = kg.query("budget status")
    budgets = result.get("data", {}).get("budgets", [])
    over = [b for b in budgets if b.get("status") == "OVER"]
    data = "Budgets: " + ", ".join(f"{b['category']} R{b['spent']:,.0f}/R{b['limit']:,.0f}" for b in budgets) if budgets else "No budgets set."
    template = f"{len(over)} budgets exceeded. " + ", ".join(f"{b['category']} at R{b['spent']:,.2f}" for b in over) if over else "All budgets within limits."
    return {
        "command": "budget", "recognized": text, "intent": "budgets",
        "data": result.get("data", {}), "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_documents(text: str) -> dict:
    data = "Available documents: Feb 2025 Statement (id=1), Jan 2025 Statement (id=2), Tax Certificate (id=3), Proof of Payment (id=4), Account Confirmation (id=5)."
    return {
        "command": "documents", "recognized": text, "intent": "documents",
        "data": {"available": ["statement_feb", "statement_jan", "tax_cert", "proof_payment", "account_confirm"]},
        "action": None,
        "data_summary": data,
        "response": "I have your February statement, tax certificate, and proof of payment ready. Which would you like?",
    }


async def _handle_spending(text: str) -> dict:
    result = kg.query("where am I spending")
    cats = [(n.label, n.attrs.get("total_amount", 0)) for n in kg.nodes.values() if n.type == "category"]
    cats.sort(key=lambda x: x[1], reverse=True)
    data = "Spending by category: " + ", ".join(f"{c}: R{a:,.0f}" for c, a in cats[:6]) if cats else "No spending data yet."
    return {
        "command": "spending", "recognized": text, "intent": "spending",
        "data": result.get("data", {}), "action": None,
        "data_summary": data,
        "response": result.get("text", "Let me check your spending patterns."),
    }


async def _handle_fraud(text: str) -> dict:
    blocked = [n.label for n in kg.nodes.values() if n.type == "merchant" and "unknown" in n.label.lower()]
    alerts = [n.label for n in kg.nodes.values() if n.type == "alert"]
    data = f"Blocked merchants: {', '.join(blocked) or 'none'}. Active alerts: {', '.join(alerts[:5]) or 'none'}."
    template = f"I blocked {len(blocked)} suspicious transaction(s): {', '.join(blocked)}." if blocked else "No suspicious transactions detected."
    return {
        "command": "fraud", "recognized": text, "intent": "fraud",
        "data": {"blocked_merchants": blocked}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_savings(text: str) -> dict:
    result = kg.query("how can I save")
    subs = kg.get_subscriptions()
    sub_total = sum(s.get("amount", 0) for s in subs)
    budgets = kg.get_budgets()
    over = [b for b in budgets if b.get("status") == "OVER"]
    data = f"Subscriptions: R{sub_total:,.0f}/mo ({len(subs)} active). Over-budget categories: {len(over)}. Balance: R{kg.balance:,.2f}."
    tips = []
    if sub_total > 0: tips.append(f"Review R{sub_total:,.2f}/mo in subscriptions")
    if over: tips.append(f"Cut {over[0]['category']} spending")
    tips.append("Set up automated savings of R3,000/month")
    template = "Ways to save: " + ". ".join(tips) + "."
    return {
        "command": "savings", "recognized": text, "intent": "savings",
        "data": result.get("data", {}), "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_set_budget(text: str) -> dict:
    result = kg.add_budget("Food Delivery", 500, "week")
    return {
        "command": "set_budget", "recognized": text, "intent": "set_budget",
        "data": result, "action": {"type": "kg_updated", "detail": "Budget created"},
        "data_summary": "Created budget: Food Delivery R500/week.",
        "response": "Done. Food Delivery budget set to R500 per week. I'll alert you when approaching the limit.",
    }


async def _handle_set_goal(text: str) -> dict:
    result = kg.add_goal("Emergency Fund", 50000, 3000)
    months = result.get("months_needed", 17)
    return {
        "command": "set_goal", "recognized": text, "intent": "set_goal",
        "data": result, "action": {"type": "kg_updated", "detail": "Goal created"},
        "data_summary": f"Goal: Emergency Fund R50,000, saving R3,000/mo, {months} months to go.",
        "response": f"Goal set: Emergency Fund R50,000, saving R3,000/month. About {months} months to go.",
    }


async def _handle_cancel_subscription(text: str) -> dict:
    result = kg.run_scenario("cancel_subscription", merchant="Netflix SA")
    return {
        "command": "cancel_subscription", "recognized": text, "intent": "cancel_subscription",
        "data": result, "action": {"type": "kg_updated", "detail": "Subscription cancelled"},
        "data_summary": "Cancelling Netflix SA: R299/mo, R3,588/year savings.",
        "response": result.get("recommendation", "Netflix SA costs R299/month. That's R3,588/year you could save."),
    }


async def _handle_loan(text: str) -> dict:
    loans = [n for n in kg.nodes.values() if n.type == "loan"]
    if loans:
        total_debt = sum(l.attrs.get("balance", 0) for l in loans)
        total_monthly = sum(l.attrs.get("monthly_payment", 0) for l in loans)
        details = ", ".join(f"{l.label} R{l.attrs.get('balance', 0):,.0f}" for l in loans[:3])
        data = f"Loans: {len(loans)} active, total debt R{total_debt:,.0f}, monthly R{total_monthly:,.0f}. {details}."
        template = f"{len(loans)} active loans totalling R{total_debt:,.0f}. Monthly: R{total_monthly:,.0f}. {details}."
    else:
        data = "No active loans."
        template = "No active loans tracked."
    return {
        "command": "loan", "recognized": text, "intent": "loan",
        "data": {"loans": [{"name": l.label, **l.attrs} for l in loans]}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_investment(text: str) -> dict:
    investments = [n for n in kg.nodes.values() if n.type == "investment"]
    if investments:
        total_value = sum(i.attrs.get("current_value", 0) for i in investments)
        total_pnl = sum(i.attrs.get("pnl", 0) for i in investments)
        data = f"Portfolio: R{total_value:,.0f} ({'+' if total_pnl >= 0 else ''}R{total_pnl:,.0f}). {len(investments)} positions."
        template = f"Portfolio value: R{total_value:,.0f} ({'+' if total_pnl >= 0 else ''}R{total_pnl:,.0f})."
    else:
        data = "No investments tracked."
        template = "No investments tracked yet."
    return {
        "command": "investment", "recognized": text, "intent": "investment",
        "data": {"investments": [{"name": i.label, **i.attrs} for i in investments]}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_insurance(text: str) -> dict:
    policies = [n for n in kg.nodes.values() if n.type == "insurance"]
    if policies:
        total = sum(p.attrs.get("premium", 0) for p in policies)
        details = ", ".join(f"{p.label} R{p.attrs.get('premium', 0):,.0f}/mo" for p in policies[:3])
        data = f"Insurance: {len(policies)} policies, R{total:,.0f}/mo. {details}."
        template = f"{len(policies)} policies costing R{total:,.0f}/month. {details}."
    else:
        data = "No insurance policies tracked."
        template = "No insurance policies tracked."
    return {
        "command": "insurance", "recognized": text, "intent": "insurance",
        "data": {"policies": [{"name": p.label, **p.attrs} for p in policies]}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_tax(text: str) -> dict:
    tax_items = [n for n in kg.nodes.values() if n.type == "tax"]
    if tax_items:
        income_total = sum(t.attrs.get("amount", 0) for t in tax_items if t.attrs.get("tax_type") == "income")
        deduction_total = sum(t.attrs.get("amount", 0) for t in tax_items if t.attrs.get("tax_type") == "deduction")
        data = f"Tax: Income R{income_total:,.0f}, Deductions R{deduction_total:,.0f}, Taxable R{income_total - deduction_total:,.0f}."
        template = f"Gross income R{income_total:,.0f}, deductions R{deduction_total:,.0f}. Taxable: R{income_total - deduction_total:,.0f}."
    else:
        data = "No tax data tracked."
        template = "No tax data tracked yet."
    return {
        "command": "tax", "recognized": text, "intent": "tax",
        "data": {"tax_items": [{"name": t.label, **t.attrs} for t in tax_items]}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_income(text: str) -> dict:
    incomes = [n for n in kg.nodes.values() if n.type == "income"]
    if incomes:
        total = sum(i.attrs.get("amount", 0) for i in incomes if i.attrs.get("frequency") == "monthly")
        details = ", ".join(f"{i.label} R{i.attrs.get('amount', 0):,.0f}" for i in incomes[:3])
        data = f"Income: R{total:,.0f}/mo. Sources: {details}."
        template = f"Monthly income: R{total:,.0f}. {details}."
    else:
        data = f"Salary: R{kg.salary:,.2f} on the {kg.salary_day}th."
        template = f"Your salary is R{kg.salary:,.2f} arriving on the {kg.salary_day}th."
    return {
        "command": "income", "recognized": text, "intent": "income",
        "data": {"incomes": [{"name": i.label, **i.attrs} for i in incomes]}, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_transfer(text: str) -> dict:
    acct = kg.get_account()
    acct_name = acct.get("name", "account")
    accounts = kg.list_accounts()
    acct_list = ", ".join(f"{a['name']} R{a['balance']:,.2f}" for a in accounts)
    data = f"Active account: {acct_name}. Available: R{kg.available:,.2f}. Accounts: {acct_list}."
    return {
        "command": "transfer", "recognized": text, "intent": "transfer",
        "data": {"available": kg.available, "accounts": accounts}, "action": None,
        "data_summary": data,
        "response": f"From {acct_name}, available: R{kg.available:,.2f}. Where would you like to transfer?",
    }


async def _handle_pattern(text: str) -> dict:
    result = kg.query("what patterns do you see")
    patterns = [n.label for n in kg.nodes.values() if n.type == "pattern"]
    data = "Detected patterns: " + ", ".join(patterns) if patterns else "No patterns detected yet."
    return {
        "command": "pattern", "recognized": text, "intent": "pattern",
        "data": result.get("data", {}), "action": None,
        "data_summary": data,
        "response": result.get("text", "Analyzing your spending patterns."),
    }


async def _handle_prediction(text: str) -> dict:
    result = kg.query("what are your predictions")
    predictions = [n for n in kg.nodes.values() if n.type == "prediction"]
    data = "Predictions: " + ", ".join(f"{p.label}: {p.attrs.get('description', '')}" for p in predictions) if predictions else "No predictions yet."
    return {
        "command": "prediction", "recognized": text, "intent": "prediction",
        "data": result.get("data", {}), "action": None,
        "data_summary": data,
        "response": result.get("text", "Let me check your financial forecast."),
    }


# ==================== ACTION HANDLERS (do things) ====================

async def _handle_add_task(text: str) -> dict:
    """Create a task/reminder from voice command."""
    # Extract task description — remove trigger phrases
    task_text = text
    for phrase in ["remind me to", "remind me", "add task", "create task", "new task",
                   "create reminder", "set reminder", "add reminder"]:
        task_text = task_text.replace(phrase, "").strip()
    task_text = task_text.strip(" .,!").capitalize() or "New task from voice"

    # Detect due date hints
    due = "This week"
    for hint, d in [("today", "Today"), ("tomorrow", "Tomorrow"), ("friday", "Friday"),
                    ("monday", "Monday"), ("this week", "This week"), ("next week", "Next week"),
                    ("payday", "Payday"), ("month end", "Month end")]:
        if hint in text.lower():
            due = d
            break

    # Create via imported main module's DEMO_TASKS
    from main import DEMO_TASKS
    new_task = {
        "id": len(DEMO_TASKS) + 1,
        "text": task_text,
        "priority": "medium",
        "done": False,
        "due": due,
        "source": "Voice Agent"
    }
    DEMO_TASKS.append(new_task)

    return {
        "command": "add_task", "recognized": text, "intent": "add_task",
        "data": new_task,
        "action": {"type": "task_created", "task": new_task},
        "data_summary": f"Created task: '{task_text}', due: {due}.",
        "response": f"Done. I've added '{task_text}' to your tasks, due {due}.",
    }


async def _handle_complete_task(text: str) -> dict:
    """Mark a task as done."""
    from main import DEMO_TASKS
    # Find first incomplete task (or try to match text)
    target = None
    for task in DEMO_TASKS:
        if not task["done"]:
            # Check if task text partially matches
            if any(w in task["text"].lower() for w in text.lower().split() if len(w) > 3):
                target = task
                break
    if not target:
        for task in DEMO_TASKS:
            if not task["done"]:
                target = task
                break
    if target:
        target["done"] = True
        return {
            "command": "complete_task", "recognized": text, "intent": "complete_task",
            "data": target,
            "action": {"type": "task_completed", "task": target},
            "data_summary": f"Completed task: '{target['text']}'.",
            "response": f"Marked '{target['text']}' as done.",
        }
    return {
        "command": "complete_task", "recognized": text, "intent": "complete_task",
        "data": {}, "action": None, "data_summary": "No pending tasks found.",
        "response": "No pending tasks to complete.",
    }


async def _handle_download_doc(text: str) -> dict:
    """Trigger document download."""
    text_lower = text.lower()
    doc_id = 1  # Default to latest statement
    if "tax" in text_lower:
        doc_id = 3
    elif "proof" in text_lower or "payment" in text_lower:
        doc_id = 4
    elif "confirm" in text_lower or "letter" in text_lower:
        doc_id = 5
    elif "jan" in text_lower:
        doc_id = 2

    doc_names = {1: "February 2025 Statement", 2: "January 2025 Statement",
                 3: "Tax Certificate", 4: "Proof of Payment", 5: "Account Confirmation"}
    name = doc_names.get(doc_id, "Document")
    return {
        "command": "download_doc", "recognized": text, "intent": "download_doc",
        "data": {"doc_id": doc_id, "name": name},
        "action": {"type": "download", "url": f"/api/documents/{doc_id}/download", "name": name},
        "data_summary": f"Preparing {name} for download (PDF).",
        "response": f"Downloading your {name} now.",
    }


async def _handle_trust_merchant(text: str) -> dict:
    """Mark a merchant as trusted, remove fraud alerts."""
    # Try to find which merchant from recent alerts or conversation
    alerts = [n for n in kg.nodes.values() if n.type == "alert"]
    if not alerts:
        return {
            "command": "trust_merchant", "recognized": text, "intent": "trust_merchant",
            "data": {}, "action": None, "data_summary": "No alerts to dismiss.",
            "response": "No flagged merchants found. Everything looks clean.",
        }

    # Find the most recent alert's linked merchant
    latest_alert = alerts[-1]
    merchant_name = None
    for e in kg.edges:
        if e.target == latest_alert.id and e.source in kg.nodes and kg.nodes[e.source].type == "merchant":
            merchant_name = kg.nodes[e.source].label
            break
        if e.source == latest_alert.id and e.target in kg.nodes and kg.nodes[e.target].type == "merchant":
            merchant_name = kg.nodes[e.target].label
            break

    if merchant_name:
        result = kg.trust_merchant(merchant_name)
    else:
        # Just dismiss the alert
        result = kg.dismiss_alert(alert_id=latest_alert.id)
        result["merchant"] = latest_alert.label

    return {
        "command": "trust_merchant", "recognized": text, "intent": "trust_merchant",
        "data": result,
        "action": {"type": "kg_updated", "detail": f"Trusted {result.get('merchant', 'merchant')}",
                   "unfreeze": True},
        "data_summary": result.get("message", "Merchant trusted."),
        "response": result.get("message", "Merchant marked as trusted. Alert removed."),
    }


async def _handle_dismiss_alert(text: str) -> dict:
    """Dismiss an alert from the knowledge graph."""
    alerts = [n for n in kg.nodes.values() if n.type == "alert"]
    if not alerts:
        return {
            "command": "dismiss_alert", "recognized": text, "intent": "dismiss_alert",
            "data": {}, "action": None, "data_summary": "No alerts to dismiss.",
            "response": "No active alerts to dismiss.",
        }
    # Dismiss the most recent alert
    target = alerts[-1]
    result = kg.dismiss_alert(alert_id=target.id)
    return {
        "command": "dismiss_alert", "recognized": text, "intent": "dismiss_alert",
        "data": result,
        "action": {"type": "kg_updated", "detail": f"Dismissed: {target.label}"},
        "data_summary": result.get("message", "Alert dismissed."),
        "response": result.get("message", "Alert dismissed."),
    }


async def _handle_block_merchant(text: str) -> dict:
    """Block a merchant / report fraud."""
    # Find the most recent suspicious merchant
    merchants = [n for n in kg.nodes.values()
                 if n.type == "merchant" and (n.attrs.get("status") == "blocked" or "unknown" in n.label.lower())]
    if merchants:
        m = merchants[-1]
        data = f"Blocked merchant: {m.label}. Card frozen."
        template = f"I've confirmed {m.label} as fraudulent. Card is frozen for your protection."
    else:
        data = "No specific merchant identified. Card frozen as precaution."
        template = "Card frozen as a precaution. I'll investigate further."
    return {
        "command": "block_merchant", "recognized": text, "intent": "block_merchant",
        "data": {"frozen": True}, "action": {"type": "card_frozen"},
        "data_summary": data, "response": template,
    }


# ==================== MEMORY HANDLERS ====================

async def _handle_remember(text: str) -> dict:
    """Store a user fact in persistent memory."""
    # Strip trigger phrases
    fact = text
    for phrase in ["remember that", "remember my", "remember i", "don't forget", "keep in mind"]:
        fact = fact.replace(phrase, "").strip()
    fact = fact.strip(" .,!").capitalize()

    if not fact or len(fact) < 3:
        return {
            "command": "remember", "recognized": text, "intent": "remember",
            "data": {}, "action": None,
            "response": "What would you like me to remember?",
        }

    _memory["facts"].append(fact)
    if len(_memory["facts"]) > 30:
        _memory["facts"] = _memory["facts"][-30:]
    _save_memory()

    return {
        "command": "remember", "recognized": text, "intent": "remember",
        "data": {"fact": fact, "total_facts": len(_memory["facts"])},
        "action": None,
        "response": f"Got it, I'll remember that: \"{fact}\". I now have {len(_memory['facts'])} things stored in memory.",
    }


async def _handle_recall_memory(text: str) -> dict:
    """Show what the AI remembers about the user."""
    text_lower = text.lower()

    # Clear memory if asked
    if "forget" in text_lower or "clear" in text_lower:
        old_count = len(_memory["facts"])
        clear_history()
        return {
            "command": "recall_memory", "recognized": text, "intent": "recall_memory",
            "data": {"cleared": True},
            "action": None,
            "response": f"Memory cleared. I've forgotten {old_count} facts and all conversation history. Fresh start.",
        }

    facts = _memory["facts"]
    conversations = _memory["conversations"]
    summary = _memory["summary"]

    if not facts and not summary:
        return {
            "command": "recall_memory", "recognized": text, "intent": "recall_memory",
            "data": {"facts": [], "conversations": 0},
            "action": None,
            "response": "I don't have any stored memories yet. Talk to me more, or say 'remember that...' to store something.",
        }

    parts = []
    if facts:
        parts.append(f"I remember {len(facts)} things about you: " + ". ".join(facts[-5:]))
    if summary:
        parts.append(f"From our past conversations: {summary[:200]}")
    parts.append(f"I have {len(conversations)} messages in our conversation history.")

    return {
        "command": "recall_memory", "recognized": text, "intent": "recall_memory",
        "data": {"facts": facts, "conversations": len(conversations), "summary": summary},
        "action": None,
        "data_summary": " ".join(parts),
        "response": " ".join(parts),
    }


# ==================== MULTI-ACCOUNT HANDLERS ====================

async def _handle_switch_account(text: str) -> dict:
    """Switch active account based on text match."""
    accounts = kg.list_accounts()
    target = None
    text_lower = text.lower()
    for acct in accounts:
        name_lower = acct["name"].lower()
        acct_type = acct["type"].lower()
        if acct_type in text_lower or any(w in text_lower for w in name_lower.split()):
            target = acct
            break
    if not target:
        # Switch to the other one (toggle)
        current = kg.active_account_id
        others = [a for a in accounts if a["id"] != current]
        target = others[0] if others else None
    if target:
        result = kg.switch_account(target["id"])
        return {
            "command": "switch_account", "recognized": text, "intent": "switch_account",
            "data": result,
            "action": {"type": "account_switched", "account_id": target["id"]},
            "data_summary": f"Switched to {target['name']} (R{target['balance']:,.2f}).",
            "response": f"Switched to {target['name']}. Balance: R{target['balance']:,.2f}.",
        }
    return {
        "command": "switch_account", "recognized": text, "intent": "switch_account",
        "data": {}, "action": None,
        "data_summary": "No matching account found.",
        "response": "I couldn't find a matching account to switch to.",
    }


async def _handle_total_balance(text: str) -> dict:
    """Show combined balance across all accounts."""
    totals = kg.get_total_balance()
    acct_list = ", ".join(f"{a['name']} R{a['balance']:,.2f}" for a in totals["accounts"])
    data = f"Total: R{totals['totalBalance']:,.2f} across {totals['accountCount']} accounts. {acct_list}."
    return {
        "command": "total_balance", "recognized": text, "intent": "total_balance",
        "data": totals, "action": None,
        "data_summary": data,
        "response": f"Your combined balance across {totals['accountCount']} accounts is R{totals['totalBalance']:,.2f}. {acct_list}.",
    }


async def _handle_affordability(text: str) -> dict:
    """Check affordability of a monthly amount."""
    import re
    match = re.search(r'r?\s?(\d[\d,. ]*)', text.lower())
    amount = 5000  # default
    if match:
        amount = float(match.group(1).replace(',', '').replace(' ', ''))
    result = kg.check_affordability(amount)
    return {
        "command": "affordability", "recognized": text, "intent": "affordability",
        "data": result, "action": None,
        "data_summary": result["summary"],
        "response": result["summary"],
    }


async def _handle_trend(text: str) -> dict:
    """Show spending trend analysis."""
    result = kg.get_spending_trend()
    return {
        "command": "trend", "recognized": text, "intent": "trend",
        "data": result, "action": None,
        "data_summary": result["summary"],
        "response": result["summary"],
    }


async def _handle_recurring(text: str) -> dict:
    """Show recurring payments / debit orders."""
    payments = kg.get_recurring_payments()
    total = sum(p["amount"] for p in payments)
    data = f"{len(payments)} recurring payments totalling R{total:,.2f}/mo. " + ", ".join(
        f"{p['merchant']} R{p['amount']:,.0f}" for p in payments[:6])
    template = f"You have {len(payments)} recurring payments totalling R{total:,.2f}/month." if payments else "No recurring payments detected yet."
    return {
        "command": "recurring", "recognized": text, "intent": "recurring",
        "data": {"payments": payments, "total": round(total, 2)}, "action": None,
        "data_summary": data, "response": template,
    }


# ==================== NEW CAPABILITY HANDLERS ====================

async def _handle_loan_eligibility(text: str) -> dict:
    """Assess loan eligibility based on natural language request."""
    import re
    # Extract amount
    match = re.search(r'r?\s?(\d[\d,. ]*)', text.lower())
    amount = 100000  # default
    if match:
        raw = match.group(1).replace(',', '').replace(' ', '').rstrip('.')
        try:
            amount = float(raw)
        except ValueError:
            pass
    # Detect loan type
    loan_type = "personal"
    for lt, keywords in [("mortgage", ["home", "house", "property", "mortgage"]),
                         ("vehicle", ["car", "vehicle", "auto"]),
                         ("education", ["study", "education", "university", "tuition"])]:
        if any(k in text.lower() for k in keywords):
            loan_type = lt
            break
    # Detect term
    term = 60
    term_match = re.search(r'(\d+)\s*(month|year)', text.lower())
    if term_match:
        val = int(term_match.group(1))
        if "year" in term_match.group(2):
            term = val * 12
        else:
            term = val

    result = assess_loan_eligibility(amount, term, loan_type)
    verdict = result["verdict"]
    factors_str = "; ".join(f"{f['factor']}: {f['detail']}" for f in result["factors"][:4])
    data = (f"Loan: R{amount:,.0f} {loan_type}, {term}mo. Verdict: {verdict}. "
            f"Payment: R{result['estimated_payment']:,.0f}/mo. DTI: {result['new_dti']:.0f}%. "
            f"Factors: {factors_str}")

    if verdict == "APPROVED":
        template = (f"You're eligible for a R{amount:,.0f} {loan_type} loan. "
                    f"Estimated payment: R{result['estimated_payment']:,.0f}/month over {term} months at {result['interest_rate']}%. "
                    f"Your DTI would be {result['new_dti']:.0f}%.")
    elif verdict == "CONDITIONAL":
        template = (f"Conditional approval for R{amount:,.0f}. DTI at {result['new_dti']:.0f}% is elevated. "
                    f"Payment would be R{result['estimated_payment']:,.0f}/month. "
                    f"Maximum I'd recommend: R{result['max_affordable']:,.0f}.")
    else:
        template = (f"Not eligible for R{amount:,.0f} at this time. DTI would reach {result['new_dti']:.0f}%. "
                    f"Maximum affordable: R{result['max_affordable']:,.0f} with R{result['max_affordable'] * result['interest_rate'] / 100 / 12 * 1.5:,.0f}/month payment.")

    return {
        "command": "loan_eligibility", "recognized": text, "intent": "loan_eligibility",
        "data": result, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_health_score(text: str) -> dict:
    """Calculate and present financial health score."""
    result = calculate_health_score()
    score = result["score"]
    grade = result["grade"]
    details = result["details"]
    data = (f"Health score: {score}/100 ({grade}). "
            f"{details['dti']}. {details['buffer']}. {details['budgets']}. "
            f"{details['insurance']}. {details['investments']}. {details['habits']}.")
    template = (f"Your financial health score is {score} out of 100, grade {grade}. "
                f"{details['dti']}. {details['buffer']}. {details['budgets']}.")
    return {
        "command": "health_score", "recognized": text, "intent": "health_score",
        "data": result, "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_smart_transfer(text: str) -> dict:
    """Parse transfer request and execute between accounts."""
    import re
    # Extract amount
    match = re.search(r'r?\s?(\d[\d,. ]*)', text.lower())
    amount = 0
    if match:
        raw = match.group(1).replace(',', '').replace(' ', '').rstrip('.')
        try:
            amount = float(raw)
        except ValueError:
            pass

    if amount <= 0:
        return {
            "command": "smart_transfer", "recognized": text, "intent": "smart_transfer",
            "data": {}, "action": None,
            "data_summary": "No amount specified.",
            "response": "How much would you like to transfer? Say something like 'transfer R5000 to savings'.",
        }

    # Determine destination
    accounts = kg.list_accounts()
    from_id = kg.active_account_id
    to_id = None

    for acct in accounts:
        if acct["id"] == from_id:
            continue
        name_lower = acct["name"].lower()
        type_lower = acct["type"].lower()
        if type_lower in text.lower() or any(w in text.lower() for w in name_lower.split()):
            to_id = acct["id"]
            break

    # Default: transfer to the other account
    if not to_id:
        others = [a for a in accounts if a["id"] != from_id]
        to_id = others[0]["id"] if others else None

    if not to_id:
        return {
            "command": "smart_transfer", "recognized": text, "intent": "smart_transfer",
            "data": {}, "action": None,
            "data_summary": "Only one account available.",
            "response": "You only have one account. No transfer destination available.",
        }

    result = execute_transfer(from_id, to_id, amount)
    if result["success"]:
        return {
            "command": "smart_transfer", "recognized": text, "intent": "smart_transfer",
            "data": result,
            "action": {"type": "kg_updated", "detail": result["message"]},
            "data_summary": result["message"],
            "response": result["message"],
        }
    else:
        return {
            "command": "smart_transfer", "recognized": text, "intent": "smart_transfer",
            "data": result, "action": None,
            "data_summary": result.get("error", "Transfer failed."),
            "response": result.get("error", "Transfer failed. Check your balance."),
        }


async def _handle_compare_months(text: str) -> dict:
    """Compare current month spending vs previous month."""
    trend = kg.get_spending_trend()
    history = kg.monthly_history
    if len(history) < 2:
        data = "Not enough data for comparison. Need at least 2 months."
        template = "I need at least 2 months of data to compare. Keep the simulation running!"
    else:
        months_sorted = sorted(history.keys())
        prev_data = history[months_sorted[-2]]
        curr_data = history[months_sorted[-1]]
        prev_total = prev_data["total_expenses"]
        curr_total = curr_data["total_expenses"]
        change = curr_total - prev_total
        pct = ((change / prev_total) * 100) if prev_total > 0 else 0

        # Category comparison
        cat_changes = []
        all_cats = set(list(prev_data.get("categories", {}).keys()) +
                       list(curr_data.get("categories", {}).keys()))
        for cat in all_cats:
            p = prev_data.get("categories", {}).get(cat, 0)
            c = curr_data.get("categories", {}).get(cat, 0)
            if abs(c - p) > 100:
                direction = "up" if c > p else "down"
                cat_changes.append(f"{cat} {'+'if c > p else ''}R{c - p:,.0f}")

        data = (f"Previous: R{prev_total:,.0f}, Current: R{curr_total:,.0f}, "
                f"Change: {'+'if change > 0 else ''}R{change:,.0f} ({pct:+.0f}%). "
                f"Category shifts: {', '.join(cat_changes[:5])}")
        template = (f"Spending {'increased' if change > 0 else 'decreased'} by "
                    f"R{abs(change):,.0f} ({abs(pct):.0f}%) vs last month. "
                    f"R{prev_total:,.0f} -> R{curr_total:,.0f}. "
                    + (f"Biggest moves: {', '.join(cat_changes[:3])}." if cat_changes else ""))

    return {
        "command": "compare_months", "recognized": text, "intent": "compare_months",
        "data": {"trend": trend, "history": {str(k): v for k, v in history.items()}},
        "action": None,
        "data_summary": data, "response": template,
    }


async def _handle_start_sim(text: str) -> dict:
    """Start the life simulator."""
    import re
    speed = 1.0
    match = re.search(r'(\d+(?:\.\d+)?)\s*x', text.lower())
    if match:
        speed = float(match.group(1))
    elif "fast" in text.lower():
        speed = 2.0
    elif "slow" in text.lower():
        speed = 0.5

    from simulator import simulator
    result = await simulator.start(speed)
    return {
        "command": "start_sim", "recognized": text, "intent": "start_sim",
        "data": result,
        "action": {"type": "kg_updated", "detail": "Simulator started"},
        "data_summary": f"Simulator started at {speed}x speed.",
        "response": f"Life simulator started at {speed}x speed. Watch your financial life unfold in real-time.",
    }


async def _handle_stop_sim(text: str) -> dict:
    """Stop the life simulator."""
    from simulator import simulator
    result = await simulator.stop()
    return {
        "command": "stop_sim", "recognized": text, "intent": "stop_sim",
        "data": result,
        "action": {"type": "kg_updated", "detail": "Simulator stopped"},
        "data_summary": f"Simulator stopped after {result['months_simulated']} months.",
        "response": f"Simulator paused after {result['months_simulated']} months of financial data.",
    }


# ==================== PAYMENT FLOW (multi-turn) ====================

async def _handle_pay(text: str) -> dict:
    """Start payment flow — find beneficiary, get amount, confirm."""
    # Extract beneficiary name from text
    name_patterns = [
        r'pay\s+(?:r\s?\d[\d,.]*\s+to\s+)?(.+?)(?:\s+r\s?\d|\s*$)',
        r'send\s+(?:r\s?\d[\d,.]*\s+to\s+)?(.+?)(?:\s+r\s?\d|\s*$)',
        r'(?:pay|send)\s+(?:money\s+)?to\s+(.+?)(?:\s+r\s?\d|\s*$)',
        r'payment\s+to\s+(.+?)(?:\s+r\s?\d|\s*$)',
    ]

    # Extract amount
    amt_match = re.search(r'r\s?(\d[\d,. ]*)', text)
    amount = 0
    if amt_match:
        try:
            amount = float(amt_match.group(1).replace(',', '').replace(' ', '').rstrip('.'))
        except ValueError:
            pass

    # Extract beneficiary name
    ben_name = ""
    for pattern in name_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Remove amount if it crept in
            candidate = re.sub(r'r\s?\d[\d,.]*', '', candidate).strip()
            # Remove common filler words
            for filler in ["please", "now", "asap", "urgently", "quickly"]:
                candidate = candidate.replace(filler, "").strip()
            if candidate and len(candidate) > 1:
                ben_name = candidate
                break

    if not ben_name:
        # No name detected — ask
        _set_flow("payment", "awaiting_name", {"amount": amount})
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {}, "action": None,
            "response": "Who would you like to pay? Tell me the beneficiary name.",
            "ui": {"type": "payment_flow", "step": "ask_name", "beneficiaries": kg.get_beneficiaries()},
        }

    # Search for beneficiary
    matches = kg.find_beneficiary(ben_name)

    if len(matches) == 0:
        # No match found
        _set_flow("payment", "no_match", {"query": ben_name, "amount": amount})
        bens = kg.get_beneficiaries()
        ben_list = ", ".join(b["name"] for b in bens[:5])
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"query": ben_name}, "action": None,
            "response": f"I don't have a beneficiary called \"{ben_name}\". Your saved beneficiaries are: {ben_list}. Who did you mean?",
            "ui": {"type": "payment_flow", "step": "not_found", "query": ben_name, "beneficiaries": bens},
        }

    if len(matches) == 1 or (len(matches) > 1 and matches[0]["score"] >= 80 and matches[0]["score"] - matches[1]["score"] >= 20):
        # Clear match
        ben = matches[0]
        if amount <= 0:
            _set_flow("payment", "awaiting_amount", {"beneficiary": ben})
            return {
                "command": "pay", "recognized": text, "intent": "pay",
                "data": {"beneficiary": ben}, "action": None,
                "response": f"How much would you like to pay {ben['name']}?",
                "ui": {"type": "payment_flow", "step": "ask_amount", "beneficiary": ben},
            }
        # Have both name and amount — show confirmation
        _set_flow("payment", "awaiting_confirm", {"beneficiary": ben, "amount": amount})
        acct = kg.accounts.get(kg.active_account_id, {})
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"beneficiary": ben, "amount": amount}, "action": None,
            "response": f"Pay R{amount:,.2f} to {ben['name']} ({ben.get('bank','')})? Reference: \"{ben.get('reference','')}\".",
            "ui": {"type": "payment_flow", "step": "confirm",
                   "beneficiary": ben, "amount": amount,
                   "from_account": kg.active_account_id,
                   "balance": acct.get("balance", 0)},
        }

    # Multiple matches — disambiguate
    _set_flow("payment", "disambiguate", {"matches": matches[:4], "amount": amount})
    names = " or ".join(f"\"{m['name']}\"" for m in matches[:4])
    return {
        "command": "pay", "recognized": text, "intent": "pay",
        "data": {"matches": matches[:4]}, "action": None,
        "response": f"I found multiple matches: {names}. Which one did you mean?",
        "ui": {"type": "payment_flow", "step": "disambiguate", "matches": matches[:4], "amount": amount},
    }


async def _handle_flow_continue(text: str) -> dict:
    """Handle continuation of an active multi-turn flow."""
    flow = _flow_state["active"]
    step = _flow_state["step"]
    data = _flow_state["data"]
    text_lower = text.lower().strip()

    # Cancel flow
    if any(w in text_lower for w in ["cancel", "nevermind", "never mind", "stop", "forget it", "no thanks"]):
        _reset_flow()
        return {
            "command": "flow_cancel", "recognized": text, "intent": "flow_cancel",
            "data": {}, "action": None,
            "response": "No problem, payment cancelled.",
            "ui": {"type": "payment_flow", "step": "cancelled"},
        }

    if flow == "payment":
        return await _continue_payment_flow(text, text_lower, step, data)

    # Unknown flow state — reset
    _reset_flow()
    return None


async def _continue_payment_flow(text: str, text_lower: str, step: str, data: dict) -> dict:
    """Continue the payment flow based on current step."""

    if step == "awaiting_name" or step == "no_match":
        # User is providing a beneficiary name
        query = text.strip()
        matches = kg.find_beneficiary(query)
        amount = data.get("amount", 0)

        if len(matches) == 0:
            bens = kg.get_beneficiaries()
            ben_list = ", ".join(b["name"] for b in bens[:5])
            _set_flow("payment", "no_match", {"query": query, "amount": amount})
            return {
                "command": "pay", "recognized": text, "intent": "pay",
                "data": {"query": query}, "action": None,
                "response": f"No beneficiary \"{query}\" found. Your saved ones: {ben_list}. Try again or say \"cancel\".",
                "ui": {"type": "payment_flow", "step": "not_found", "query": query, "beneficiaries": bens},
            }

        if len(matches) == 1 or matches[0]["score"] >= 80:
            ben = matches[0]
            if amount <= 0:
                _set_flow("payment", "awaiting_amount", {"beneficiary": ben})
                return {
                    "command": "pay", "recognized": text, "intent": "pay",
                    "data": {"beneficiary": ben}, "action": None,
                    "response": f"Got it, {ben['name']}. How much?",
                    "ui": {"type": "payment_flow", "step": "ask_amount", "beneficiary": ben},
                }
            _set_flow("payment", "awaiting_confirm", {"beneficiary": ben, "amount": amount})
            acct = kg.accounts.get(kg.active_account_id, {})
            return {
                "command": "pay", "recognized": text, "intent": "pay",
                "data": {"beneficiary": ben, "amount": amount}, "action": None,
                "response": f"Pay R{amount:,.2f} to {ben['name']}? Say \"confirm\" or \"cancel\".",
                "ui": {"type": "payment_flow", "step": "confirm", "beneficiary": ben, "amount": amount,
                       "from_account": kg.active_account_id, "balance": acct.get("balance", 0)},
            }

        _set_flow("payment", "disambiguate", {"matches": matches[:4], "amount": amount})
        names = " or ".join(f"\"{m['name']}\"" for m in matches[:4])
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"matches": matches[:4]}, "action": None,
            "response": f"Did you mean {names}?",
            "ui": {"type": "payment_flow", "step": "disambiguate", "matches": matches[:4], "amount": amount},
        }

    if step == "disambiguate":
        # User picking from multiple matches
        matches = data.get("matches", [])
        amount = data.get("amount", 0)
        # Try to match their response to one of the options
        for m in matches:
            if m["name"].lower() in text_lower or text_lower in m["name"].lower():
                ben = m
                if amount <= 0:
                    _set_flow("payment", "awaiting_amount", {"beneficiary": ben})
                    return {
                        "command": "pay", "recognized": text, "intent": "pay",
                        "data": {"beneficiary": ben}, "action": None,
                        "response": f"{ben['name']}, got it. How much?",
                        "ui": {"type": "payment_flow", "step": "ask_amount", "beneficiary": ben},
                    }
                _set_flow("payment", "awaiting_confirm", {"beneficiary": ben, "amount": amount})
                acct = kg.accounts.get(kg.active_account_id, {})
                return {
                    "command": "pay", "recognized": text, "intent": "pay",
                    "data": {"beneficiary": ben, "amount": amount}, "action": None,
                    "response": f"Pay R{amount:,.2f} to {ben['name']}? Confirm or cancel.",
                    "ui": {"type": "payment_flow", "step": "confirm", "beneficiary": ben, "amount": amount,
                           "from_account": kg.active_account_id, "balance": acct.get("balance", 0)},
                }
        # Try number selection (1, 2, 3...)
        try:
            idx = int(text_lower.strip()) - 1
            if 0 <= idx < len(matches):
                ben = matches[idx]
                if amount <= 0:
                    _set_flow("payment", "awaiting_amount", {"beneficiary": ben})
                    return {
                        "command": "pay", "recognized": text, "intent": "pay",
                        "data": {"beneficiary": ben}, "action": None,
                        "response": f"{ben['name']}. How much would you like to pay?",
                        "ui": {"type": "payment_flow", "step": "ask_amount", "beneficiary": ben},
                    }
        except ValueError:
            pass

        names = ", ".join(f"{i+1}. {m['name']}" for i, m in enumerate(matches))
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"matches": matches}, "action": None,
            "response": f"I didn't catch that. Please say one of: {names}",
            "ui": {"type": "payment_flow", "step": "disambiguate", "matches": matches, "amount": amount},
        }

    if step == "awaiting_amount":
        # Extract amount from response
        amt_match = re.search(r'r?\s?(\d[\d,. ]*)', text_lower)
        amount = 0
        if amt_match:
            try:
                amount = float(amt_match.group(1).replace(',', '').replace(' ', '').rstrip('.'))
            except ValueError:
                pass
        if amount <= 0:
            return {
                "command": "pay", "recognized": text, "intent": "pay",
                "data": data, "action": None,
                "response": "I need an amount. How much? For example, \"R500\" or \"1000\".",
                "ui": {"type": "payment_flow", "step": "ask_amount", "beneficiary": data.get("beneficiary")},
            }
        ben = data["beneficiary"]
        _set_flow("payment", "awaiting_confirm", {"beneficiary": ben, "amount": amount})
        acct = kg.accounts.get(kg.active_account_id, {})
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"beneficiary": ben, "amount": amount}, "action": None,
            "response": f"R{amount:,.2f} to {ben['name']}. Shall I go ahead? Say \"confirm\" to pay.",
            "ui": {"type": "payment_flow", "step": "confirm", "beneficiary": ben, "amount": amount,
                   "from_account": kg.active_account_id, "balance": acct.get("balance", 0)},
        }

    if step == "awaiting_confirm":
        ben = data["beneficiary"]
        amount = data["amount"]

        if any(w in text_lower for w in ["confirm", "yes", "go ahead", "do it", "pay", "send", "approve", "ok", "okay"]):
            # Execute payment
            result = kg.pay_beneficiary(ben["id"], amount, ben.get("reference", ""))
            _reset_flow()

            if "error" in result:
                return {
                    "command": "pay", "recognized": text, "intent": "pay",
                    "data": {"error": result["error"]}, "action": None,
                    "response": result["error"],
                    "ui": {"type": "payment_flow", "step": "error", "error": result["error"]},
                }

            return {
                "command": "pay", "recognized": text, "intent": "pay",
                "data": result,
                "action": {"type": "payment_complete", "beneficiary": ben["name"],
                           "amount": amount, "new_balance": result["new_balance"]},
                "response": f"Done! R{amount:,.2f} paid to {ben['name']}. New balance: R{result['new_balance']:,.2f}.",
                "ui": {"type": "payment_flow", "step": "success",
                       "beneficiary": ben, "amount": amount,
                       "new_balance": result["new_balance"],
                       "reference": result.get("reference", "")},
            }

        # Not confirmed
        return {
            "command": "pay", "recognized": text, "intent": "pay",
            "data": {"beneficiary": ben, "amount": amount}, "action": None,
            "response": f"Payment of R{amount:,.2f} to {ben['name']} is ready. Say \"confirm\" to proceed or \"cancel\" to abort.",
            "ui": {"type": "payment_flow", "step": "confirm", "beneficiary": ben, "amount": amount,
                   "from_account": kg.active_account_id,
                   "balance": kg.accounts.get(kg.active_account_id, {}).get("balance", 0)},
        }

    # Unknown step
    _reset_flow()
    return None


async def _handle_beneficiaries(text: str) -> dict:
    """List saved beneficiaries."""
    bens = kg.get_beneficiaries()
    if not bens:
        return {
            "command": "beneficiaries", "recognized": text, "intent": "beneficiaries",
            "data": {"beneficiaries": []}, "action": None,
            "response": "You don't have any saved beneficiaries yet.",
        }
    names = ", ".join(f"{b['name']} ({b.get('bank','')})" for b in bens)
    return {
        "command": "beneficiaries", "recognized": text, "intent": "beneficiaries",
        "data": {"beneficiaries": bens}, "action": None,
        "data_summary": f"{len(bens)} beneficiaries: {names}",
        "response": f"You have {len(bens)} saved beneficiaries: {names}.",
        "ui": {"type": "beneficiary_list", "beneficiaries": bens},
    }


# ==================== HANDLER MAP ====================

HANDLERS = {
    # Memory handlers
    "remember": _handle_remember,
    "recall_memory": _handle_recall_memory,
    # Query handlers
    "balance": _handle_balance,
    "alerts": _handle_alerts,
    "fraud": _handle_fraud,
    "budget": _handle_budget,
    "documents": _handle_documents,
    "spending": _handle_spending,
    "savings": _handle_savings,
    "set_budget": _handle_set_budget,
    "set_goal": _handle_set_goal,
    "cancel_subscription": _handle_cancel_subscription,
    "loan": _handle_loan,
    "investment": _handle_investment,
    "insurance": _handle_insurance,
    "tax": _handle_tax,
    "income": _handle_income,
    "pay": _handle_pay,
    "beneficiaries": _handle_beneficiaries,
    "transfer": _handle_smart_transfer,
    "smart_transfer": _handle_smart_transfer,
    "loan_eligibility": _handle_loan_eligibility,
    "health_score": _handle_health_score,
    "compare_months": _handle_compare_months,
    "start_sim": _handle_start_sim,
    "stop_sim": _handle_stop_sim,
    "pattern": _handle_pattern,
    "prediction": _handle_prediction,
    # Multi-account handlers
    "switch_account": _handle_switch_account,
    "total_balance": _handle_total_balance,
    "affordability": _handle_affordability,
    "trend": _handle_trend,
    "recurring": _handle_recurring,
    # Action handlers
    "add_task": _handle_add_task,
    "complete_task": _handle_complete_task,
    "download_doc": _handle_download_doc,
    "trust_merchant": _handle_trust_merchant,
    "dismiss_alert": _handle_dismiss_alert,
    "block_merchant": _handle_block_merchant,
}


def get_random_command() -> dict:
    import random
    cmd = random.choice(VOICE_COMMANDS)
    return {"display": cmd["display"], "handler": cmd["handler"]}
