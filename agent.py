"""
SentiVest Transaction Classification Engine
Rule-based classifier with AI reasoning enhancement.
"""

from datetime import datetime
from model import model

KNOWN_MERCHANTS = {
    # Groceries
    "woolworths", "woolworths food", "checkers", "pick n pay", "shoprite", "spar", "food lovers",
    # Fuel
    "shell", "shell garage n1", "engen", "engen quickshop", "bp", "caltex", "sasol",
    # Shopping
    "takealot", "takealot.com", "amazon", "amazon sa", "incredible connection", "makro", "game",
    # Food Delivery
    "uber eats", "mr d", "mr d food", "kfc", "nandos", "steers", "debonairs", "roman's pizza",
    # Subscriptions
    "netflix", "netflix sa", "spotify", "spotify premium", "showmax", "dstv", "apple", "google play",
    # Telecom
    "vodacom", "mtn", "telkom", "cell c", "rain",
    # Insurance
    "discovery", "discovery health", "outsurance", "old mutual", "sanlam", "liberty", "momentum",
    # Utilities
    "city power", "city power joburg", "eskom", "rand water", "joburg water",
    # Coffee/Food
    "vida", "vida e caffe", "starbucks", "wimpy", "ocean basket", "spur",
    # Health
    "dis-chem", "clicks", "medirite",
    # Transport
    "uber", "bolt", "gautrain", "e-toll", "sanral",
    # Banking
    "investec", "fnb", "standard bank", "absa", "capitec", "nedbank",
    # Income sources
    "acme corp", "salary", "payroll",
    # Debit orders
    "home loan", "vehicle finance", "personal loan",
}

CATEGORIES = {
    "woolworths": "Groceries", "woolworths food": "Groceries",
    "checkers": "Groceries", "pick n pay": "Groceries", "shoprite": "Groceries",
    "spar": "Groceries", "food lovers": "Groceries",
    "shell": "Fuel", "shell garage n1": "Fuel", "engen": "Fuel",
    "engen quickshop": "Convenience", "bp": "Fuel", "caltex": "Fuel", "sasol": "Fuel",
    "takealot": "Shopping", "takealot.com": "Shopping", "amazon": "Shopping",
    "amazon sa": "Shopping", "incredible connection": "Electronics",
    "makro": "Shopping", "game": "Shopping",
    "uber eats": "Food Delivery", "mr d": "Food Delivery", "mr d food": "Food Delivery",
    "kfc": "Food Delivery", "nandos": "Food Delivery", "steers": "Food Delivery",
    "debonairs": "Food Delivery", "roman's pizza": "Food Delivery",
    "netflix": "Subscription", "netflix sa": "Subscription",
    "spotify": "Subscription", "spotify premium": "Subscription",
    "showmax": "Subscription", "dstv": "Subscription",
    "apple": "Subscription", "google play": "Subscription",
    "vodacom": "Telecom", "mtn": "Telecom", "telkom": "Telecom",
    "cell c": "Telecom", "rain": "Telecom",
    "discovery": "Insurance", "discovery health": "Insurance",
    "outsurance": "Insurance", "old mutual": "Insurance",
    "sanlam": "Insurance", "liberty": "Insurance", "momentum": "Insurance",
    "city power": "Utilities", "city power joburg": "Utilities",
    "eskom": "Utilities", "rand water": "Utilities", "joburg water": "Utilities",
    "vida": "Coffee", "vida e caffe": "Coffee", "starbucks": "Coffee",
    "wimpy": "Dining", "ocean basket": "Dining", "spur": "Dining",
    "dis-chem": "Health", "clicks": "Health", "medirite": "Health",
    "uber": "Transport", "bolt": "Transport", "gautrain": "Transport",
    "e-toll": "Transport", "sanral": "Transport",
    "investec": "Banking", "fnb": "Banking", "standard bank": "Banking",
    "absa": "Banking", "capitec": "Banking", "nedbank": "Banking",
    "acme corp": "Income", "salary": "Income", "payroll": "Income",
    "home loan": "Loan Repayment", "vehicle finance": "Loan Repayment",
    "personal loan": "Loan Repayment",
}

MERCHANT_AVERAGES = {
    "woolworths food": 850, "checkers": 650, "pick n pay": 720, "shoprite": 480,
    "spar": 550, "food lovers": 920,
    "shell garage n1": 1200, "engen": 900, "engen quickshop": 160, "bp": 950,
    "takealot.com": 1500, "amazon sa": 800,
    "uber eats": 280, "mr d food": 220, "kfc": 180, "nandos": 350,
    "netflix sa": 299, "spotify premium": 80, "showmax": 99, "dstv": 899,
    "vodacom": 599, "mtn": 399, "telkom": 499, "rain": 999,
    "discovery health": 4200, "outsurance": 1847, "old mutual": 650,
    "sanlam": 1200, "liberty": 800,
    "city power joburg": 2200, "eskom": 1500, "rand water": 450,
    "dis-chem": 350, "clicks": 280,
    "uber": 150, "bolt": 120, "gautrain": 85,
    "vida e caffe": 75, "starbucks": 95, "wimpy": 180,
}

# Transaction type patterns
TXN_TYPE_PATTERNS = {
    "debit_order": ["debit order", "recurring", "d/o", "magtape"],
    "eft": ["eft", "electronic fund", "payment to", "internet banking"],
    "card_purchase": ["pos", "card purchase", "visa", "mastercard", "contactless"],
    "atm": ["atm", "cash withdrawal", "cash deposit"],
    "salary": ["salary", "payroll", "wage", "commission"],
    "interest": ["interest earned", "interest paid", "interest credited"],
    "reversal": ["reversal", "refund", "chargeback", "credit back"],
    "forex": ["forex", "foreign exchange", "usd", "eur", "gbp", "international"],
    "transfer": ["transfer", "own account", "inter-account"],
    "fee": ["bank fee", "service fee", "admin fee", "monthly fee"],
}

# Fraud indicator patterns
FRAUD_INDICATORS = {
    "unknown_merchant": {"weight": 0.3, "desc": "Unrecognized merchant"},
    "late_night": {"weight": 0.25, "desc": "Transaction between 00:00-05:00"},
    "high_value": {"weight": 0.2, "desc": "Amount exceeds R10,000"},
    "foreign_origin": {"weight": 0.15, "desc": "Foreign or cross-border transaction"},
    "rapid_succession": {"weight": 0.1, "desc": "Multiple transactions in short period"},
    "round_amount": {"weight": 0.05, "desc": "Suspiciously round amount"},
}


def classify(merchant: str, amount: float, time: str = "12:00",
             description: str = "", reference: str = "", account_id: str = None) -> dict:
    """Classify a transaction and return verdict with reasoning."""
    merchant_lower = merchant.lower().strip()
    is_known = merchant_lower in KNOWN_MERCHANTS
    category = CATEGORIES.get(merchant_lower, "Unknown")

    try:
        hour = int(time.split(":")[0])
    except (ValueError, IndexError):
        hour = 12

    is_late_night = 0 <= hour < 5
    avg = MERCHANT_AVERAGES.get(merchant_lower, amount)
    is_high_value = amount > 10000
    is_above_avg = amount > avg * 3 if avg > 0 else False
    is_subscription = category == "Subscription"
    is_utility = category in ("Utilities", "Telecom")
    is_utility_spike = is_utility and amount > avg * 1.25 if avg > 0 else False

    # Detect transaction type
    txn_type = detect_transaction_type(merchant, description, reference, amount)

    # Check fraud indicators
    fraud_score, fraud_flags = check_fraud_indicators(
        merchant_lower, is_known, amount, hour, description
    )

    # Rule engine
    verdict = "SAFE"
    confidence = 0.90
    reasoning = ""
    tags = []
    actions = []

    # Rule 1: High fraud score -> BLOCK
    if fraud_score >= 0.7:
        verdict = "BLOCK"
        confidence = min(0.97, 0.8 + fraud_score * 0.2)
        flag_descs = [FRAUD_INDICATORS[f]["desc"] for f in fraud_flags]
        reasoning = (f"High fraud risk ({fraud_score:.0%}): {', '.join(flag_descs)}. "
                     f"Transaction R{amount:,.2f} at {merchant} blocked.")
        tags = ["high_risk", "auto_blocked"] + fraud_flags
        actions = ["freeze_card", "notify_user", "flag_investigation"]

    # Rule 2: Unknown + late night -> BLOCK
    elif not is_known and is_late_night:
        verdict = "BLOCK"
        confidence = 0.97
        reasoning = (f"Unknown merchant '{merchant}' transacting at {time} (late night). "
                     f"Amount R{amount:,.2f} from unverified source. High fraud probability.")
        tags = ["unknown_merchant", "late_night", "high_risk", "auto_blocked"]
        actions = ["freeze_card", "notify_user", "flag_investigation"]

    # Rule 3: Unknown + high value -> BLOCK
    elif not is_known and is_high_value:
        verdict = "BLOCK"
        confidence = 0.94
        reasoning = (f"Unknown merchant '{merchant}' with high-value transaction R{amount:,.2f}. "
                     f"No transaction history. Blocked pending verification.")
        tags = ["unknown_merchant", "high_value", "auto_blocked"]
        actions = ["freeze_card", "verify_identity"]

    # Rule 4: Known + way above average -> FLAG
    elif is_known and is_above_avg:
        verdict = "FLAG"
        confidence = 0.78
        reasoning = (f"Transaction at {merchant} for R{amount:,.2f} is {amount/avg:.1f}x the average "
                     f"(R{avg:,.2f}). Unusual amount for this merchant.")
        tags = ["known_merchant", "above_average", "review_needed"]
        actions = ["confirm_transaction", "decline_option"]

    # Rule 5: Late night + high amount -> ALERT
    elif is_late_night and amount > 5000:
        verdict = "ALERT"
        confidence = 0.85
        reasoning = (f"Late-night transaction at {time} for R{amount:,.2f}. "
                     f"High amount during unusual hours warrants review.")
        tags = ["late_night", "high_amount", "review"]
        actions = ["notify_user", "review_transaction"]

    # Rule 6: Subscription -> check expected amount
    elif is_subscription:
        expected = avg
        diff = abs(amount - expected)
        if diff < 1:
            verdict = "SAFE"
            confidence = 0.95
            reasoning = (f"Recurring subscription at {merchant} for R{amount:,.2f}. "
                         f"Matches expected amount of R{expected:,.2f}.")
            tags = ["subscription", "recurring", "expected"]
        else:
            verdict = "ALERT"
            confidence = 0.88
            reasoning = (f"Subscription at {merchant} charged R{amount:,.2f}, "
                         f"expected R{expected:,.2f}. Review for price changes.")
            tags = ["subscription", "price_change"]
            actions = ["review_subscription", "cancel_option"]

    # Rule 7: Utility spike -> ALERT
    elif is_utility_spike:
        verdict = "ALERT"
        confidence = 0.92
        reasoning = (f"Utility payment to {merchant} of R{amount:,.2f} is "
                     f"{amount/avg:.1f}x the average (R{avg:,.2f}). Consider disputing.")
        tags = ["utility", "spike", "review"]
        actions = ["dispute_charge", "review_bill"]

    # Rule 8: Income/salary -> SAFE (credit)
    elif category == "Income":
        verdict = "SAFE"
        confidence = 0.98
        reasoning = f"Income credit from {merchant} for R{amount:,.2f}. Expected transaction."
        tags = ["income", "credit", "expected"]

    # Rule 9: Loan repayment -> SAFE (debit order)
    elif category == "Loan Repayment":
        verdict = "SAFE"
        confidence = 0.95
        reasoning = f"Loan repayment to {merchant} for R{amount:,.2f}. Scheduled debit order."
        tags = ["loan", "debit_order", "scheduled"]

    # Rule 10: Food delivery normal hours -> SAFE
    elif category == "Food Delivery" and not is_late_night:
        verdict = "SAFE"
        confidence = 0.91
        reasoning = (f"Food delivery from {merchant} for R{amount:,.2f} during "
                     f"normal hours ({time}). Within expected range.")
        tags = ["food_delivery", "normal_hours", "routine"]

    # Rule 11: Default known merchant -> SAFE
    elif is_known:
        confidence = 0.80 + min(0.15, (avg / max(amount, 1)) * 0.1)
        confidence = min(confidence, 0.95)
        reasoning = (f"Known merchant {merchant} ({category}). "
                     f"R{amount:,.2f} within normal range. No anomalies detected.")
        tags = [category.lower().replace(" ", "_"), "known_merchant", "routine"]

    # Default unknown -> SAFE with lower confidence
    else:
        confidence = 0.80
        reasoning = (f"Transaction at {merchant} for R{amount:,.2f}. "
                     f"First-time merchant, monitoring for patterns.")
        tags = ["new_merchant", "monitoring"]

    return {
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "tags": tags,
        "actions": actions,
        "category": category,
        "merchant": merchant,
        "amount": amount,
        "time": time,
        "timestamp": datetime.now().isoformat(),
        "risk_level": _risk_level(verdict),
        "transaction_type": txn_type,
        "fraud_score": round(fraud_score, 2),
        "fraud_flags": fraud_flags,
        "account_id": account_id,
    }


def detect_transaction_type(merchant: str, description: str = "",
                            reference: str = "", amount: float = 0) -> str:
    """Detect the type of transaction from metadata."""
    combined = f"{merchant} {description} {reference}".lower()

    for txn_type, patterns in TXN_TYPE_PATTERNS.items():
        if any(p in combined for p in patterns):
            return txn_type

    # Heuristic: negative amount or credit keywords = income
    if amount < 0 or any(w in combined for w in ["credit", "deposit", "received"]):
        return "credit"

    # Heuristic: round amounts at certain merchants = debit order
    if amount > 0 and amount == int(amount) and amount > 100:
        merchant_lower = merchant.lower()
        if merchant_lower in ("discovery health", "outsurance", "old mutual",
                              "sanlam", "vodacom", "mtn", "dstv"):
            return "debit_order"

    return "card_purchase"


def check_fraud_indicators(merchant: str, is_known: bool, amount: float,
                           hour: int, description: str = "") -> tuple:
    """Check for fraud indicators and return (score, list_of_flags)."""
    score = 0.0
    flags = []

    if not is_known:
        score += FRAUD_INDICATORS["unknown_merchant"]["weight"]
        flags.append("unknown_merchant")

    if 0 <= hour < 5:
        score += FRAUD_INDICATORS["late_night"]["weight"]
        flags.append("late_night")

    if amount > 10000:
        score += FRAUD_INDICATORS["high_value"]["weight"]
        flags.append("high_value")

    desc_lower = (description or "").lower()
    if any(w in desc_lower for w in ["international", "forex", "foreign", "zw", "ng", "ke"]):
        score += FRAUD_INDICATORS["foreign_origin"]["weight"]
        flags.append("foreign_origin")

    if any(w in merchant.lower() for w in ["unknown", "test", "suspicious"]):
        score += 0.2
        flags.append("unknown_merchant")

    # Round amount check (exact thousands)
    if amount >= 1000 and amount == int(amount) and amount % 1000 == 0 and not is_known:
        score += FRAUD_INDICATORS["round_amount"]["weight"]
        flags.append("round_amount")

    return min(score, 1.0), flags


def _risk_level(verdict: str) -> str:
    return {"BLOCK": "critical", "FLAG": "high", "ALERT": "medium", "SAFE": "low"}.get(verdict, "low")
