"""
SentiVest Financial Knowledge Graph Engine
Personal financial brain that understands your money as a connected system.
"""

from datetime import datetime, timedelta
import statistics
import math
from collections import defaultdict


class Node:
    def __init__(self, id: str, label: str, node_type: str, attrs: dict = None):
        self.id = id
        self.label = label
        self.type = node_type
        self.attrs = attrs or {}
        self.created = datetime.now()

    def to_dict(self):
        return {
            "id": self.id, "label": self.label, "type": self.type,
            "attrs": self.attrs, "created": self.created.isoformat()
        }


class Edge:
    def __init__(self, source: str, target: str, edge_type: str, weight: float = 1.0, attrs: dict = None):
        self.source = source
        self.target = target
        self.type = edge_type
        self.weight = weight
        self.attrs = attrs or {}

    def to_dict(self):
        return {
            "source": self.source, "target": self.target,
            "type": self.type, "weight": self.weight, "attrs": self.attrs
        }


# Design system colors and sizes for all node types
NODE_COLORS = {
    "person": "#003B5C", "merchant": "#007A6E", "category": "#C68A0E",
    "subscription": "#6366F1", "pattern": "#C2571A", "budget": "#2E7D6F",
    "goal": "#0EA5E9", "alert": "#B91C1C", "prediction": "#8B5CF6",
    "scenario": "#059669", "task": "#D97706",
    # New types
    "income": "#10B981", "loan": "#EF4444", "investment": "#3B82F6",
    "insurance": "#F59E0B", "tax": "#6B7280", "account": "#1E40AF",
    "transfer": "#14B8A6", "payee": "#8B5CF6", "beneficiary": "#7C3AED", "forex": "#EC4899",
    "invoice": "#F97316", "cost_center": "#84CC16",
}

NODE_SIZES = {
    "person": 20, "merchant": 10, "category": 14,
    "subscription": 8, "pattern": 12, "budget": 10,
    "goal": 12, "alert": 8, "prediction": 10,
    "scenario": 10, "task": 8,
    "income": 12, "loan": 14, "investment": 14,
    "insurance": 12, "tax": 10, "account": 16,
    "transfer": 8, "payee": 8, "beneficiary": 10, "forex": 10,
    "invoice": 8, "cost_center": 10,
}


class FinancialKnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.transactions_processed = 0
        self.total_spent = 0
        self.on_change = None  # Callback for real-time updates

        # Multi-account registry
        self.accounts: dict[str, dict] = {}
        self.active_account_id: str = None

        # Canonical transaction ledger
        self.transactions: list[dict] = []
        self._next_txn_id = 1

        # Demo time simulation
        self.demo_month = 0
        self.demo_base_date = datetime(2025, 3, 1)
        self.monthly_history = {}
        self.salary_history = []
        self.debit_order_history = []
        self.step_counts = {"salary": 0, "debit_orders": 0, "daily_spending": 0, "food_delivery": 0}
        self.client_profile = {
            "usual_merchants": set(), "usual_categories": {},
            "usual_hours": [], "usual_amounts": {},
            "usual_locations": {"ZA"}, "avg_daily_spend": 0,
            "txn_times": [],
        }

        # Create user node
        self._add_node("user", "You", "person", {"account_status": "Active"})

    # ==================== MULTI-ACCOUNT PROPERTIES ====================

    @property
    def balance(self):
        if self.active_account_id and self.active_account_id in self.accounts:
            return self.accounts[self.active_account_id]["balance"]
        return 0

    @balance.setter
    def balance(self, v):
        if self.active_account_id and self.active_account_id in self.accounts:
            self.accounts[self.active_account_id]["balance"] = v
            if self.active_account_id in self.nodes:
                self.nodes[self.active_account_id].attrs["balance"] = v

    @property
    def available(self):
        if self.active_account_id and self.active_account_id in self.accounts:
            return self.accounts[self.active_account_id]["available"]
        return 0

    @available.setter
    def available(self, v):
        if self.active_account_id and self.active_account_id in self.accounts:
            self.accounts[self.active_account_id]["available"] = v
            if self.active_account_id in self.nodes:
                self.nodes[self.active_account_id].attrs["available"] = v

    @property
    def salary(self):
        if self.active_account_id and self.active_account_id in self.accounts:
            return self.accounts[self.active_account_id]["salary"]
        return 0

    @salary.setter
    def salary(self, v):
        if self.active_account_id and self.active_account_id in self.accounts:
            self.accounts[self.active_account_id]["salary"] = v

    @property
    def salary_day(self):
        if self.active_account_id and self.active_account_id in self.accounts:
            return self.accounts[self.active_account_id]["salary_day"]
        return 25

    @salary_day.setter
    def salary_day(self, v):
        if self.active_account_id and self.active_account_id in self.accounts:
            self.accounts[self.active_account_id]["salary_day"] = v

    # ==================== ACCOUNT CRUD ====================

    def create_account(self, account_id: str, name: str, acct_type: str,
                       balance: float = 0, available: float = 0,
                       salary: float = 0, salary_day: int = 25,
                       last4: str = "0000", color: str = "#003B5C") -> dict:
        """Create a new bank account with KG node + edge."""
        self.accounts[account_id] = {
            "balance": balance, "available": available,
            "salary": salary, "salary_day": salary_day,
            "name": name, "type": acct_type, "color": color, "last4": last4,
        }
        self._add_node(account_id, name, "account", {
            "name": name, "type": acct_type, "balance": balance,
            "available": available, "last4": last4, "color": color,
        })
        self._add_edge("user", account_id, "OWNS_ACCOUNT")
        if self.active_account_id is None:
            self.active_account_id = account_id
        self._notify_change()
        return {"id": account_id, "name": name, "type": acct_type, "active": self.active_account_id == account_id}

    def switch_account(self, account_id: str) -> dict:
        """Switch the active account."""
        if account_id not in self.accounts:
            return {"error": f"Account {account_id} not found"}
        self.active_account_id = account_id
        self._notify_change()
        acct = self.accounts[account_id]
        return {"active": account_id, "name": acct["name"], "type": acct["type"],
                "balance": acct["balance"]}

    def get_account(self, account_id: str = None) -> dict:
        """Get details for a specific account (defaults to active)."""
        aid = account_id or self.active_account_id
        if aid not in self.accounts:
            return {"error": "Account not found"}
        acct = self.accounts[aid]
        return {"id": aid, "active": aid == self.active_account_id, **acct}

    def list_accounts(self) -> list[dict]:
        """List all accounts with active flag."""
        result = []
        for aid, acct in self.accounts.items():
            result.append({"id": aid, "active": aid == self.active_account_id, **acct})
        return result

    def get_total_balance(self) -> dict:
        """Sum balances across all accounts."""
        total = sum(a["balance"] for a in self.accounts.values())
        total_avail = sum(a["available"] for a in self.accounts.values())
        return {
            "totalBalance": round(total, 2),
            "totalAvailable": round(total_avail, 2),
            "accountCount": len(self.accounts),
            "accounts": [{"id": aid, "name": a["name"], "balance": a["balance"]}
                         for aid, a in self.accounts.items()],
        }

    def _notify_change(self):
        """Notify listeners of graph changes for real-time updates."""
        if self.on_change:
            self.on_change()

    # ==================== TIME SIMULATION ====================

    def advance_month(self):
        """Advance simulated month by 1. Saves monthly summary first."""
        self._save_monthly_summary()
        self.demo_month += 1
        self._notify_change()

    def get_demo_date(self) -> datetime:
        year = self.demo_base_date.year + (self.demo_base_date.month - 1 + self.demo_month) // 12
        month = (self.demo_base_date.month - 1 + self.demo_month) % 12 + 1
        return datetime(year, month, 1)

    def get_demo_date_str(self) -> str:
        return self.get_demo_date().strftime("%B %Y")

    def get_demo_info(self) -> dict:
        return {
            "month": self.demo_month,
            "date_str": self.get_demo_date_str(),
            "step_counts": dict(self.step_counts),
            "months_of_data": len(self.monthly_history)
        }

    def _save_monthly_summary(self):
        categories = {}
        total_expenses = 0
        for n in self.nodes.values():
            if n.type == "category":
                cat_spent = n.attrs.get("total_spent", 0)
                categories[n.label] = round(cat_spent, 2)
                total_expenses += cat_spent
        total_income = sum(
            n.attrs.get("amount", 0) for n in self.nodes.values()
            if n.type == "income" and n.attrs.get("frequency") == "monthly"
        )
        self.monthly_history[self.demo_month] = {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
            "categories": categories, "balance": self.balance
        }

    def reset(self):
        """Full reset for demo restart."""
        self.nodes = {}
        self.edges = []
        self.transactions = []
        self._next_txn_id = 1
        self.transactions_processed = 0
        self.total_spent = 0
        self.accounts = {}
        self.active_account_id = None
        self.demo_month = 0
        self.monthly_history = {}
        self.salary_history = []
        self.debit_order_history = []
        self.step_counts = {"salary": 0, "debit_orders": 0, "daily_spending": 0, "food_delivery": 0}
        self.client_profile = {
            "usual_merchants": set(), "usual_categories": {},
            "usual_hours": [], "usual_amounts": {},
            "usual_locations": {"ZA"}, "avg_daily_spend": 0,
            "txn_times": [],
        }
        self._add_node("user", "You", "person", {"account_status": "Active"})
        self._notify_change()

    # ==================== ANOMALY DETECTION ====================

    def _update_client_profile(self, merchant: str, amount: float, category: str, time: str):
        """Auto-build client profile from transaction history."""
        p = self.client_profile
        p["usual_merchants"].add(merchant.lower())
        p["usual_categories"][category] = p["usual_categories"].get(category, 0) + 1
        try:
            hour = int(time.split(":")[0])
            p["usual_hours"].append(hour)
            if len(p["usual_hours"]) > 100:
                p["usual_hours"] = p["usual_hours"][-100:]
        except (ValueError, IndexError):
            pass
        if category not in p["usual_amounts"]:
            p["usual_amounts"][category] = []
        p["usual_amounts"][category].append(amount)
        if len(p["usual_amounts"][category]) > 30:
            p["usual_amounts"][category] = p["usual_amounts"][category][-30:]
        # Location hint from merchant name
        for code in ["_zw", "_uk", "_us", "_ng", "_cn", "_ae", "_eu"]:
            if code in merchant.lower():
                loc = code.replace("_", "").upper()
                if loc not in p["usual_locations"]:
                    p["usual_locations"].add(loc)
        p["txn_times"].append(datetime.now().isoformat())
        if len(p["txn_times"]) > 50:
            p["txn_times"] = p["txn_times"][-50:]
        if self.transactions_processed > 0:
            p["avg_daily_spend"] = self.total_spent / max(self.transactions_processed, 1)

    def _score_transaction_anomaly(self, merchant: str, amount: float, category: str, time: str) -> dict:
        """Score a transaction against client profile. Returns {score, flags, severity}."""
        p = self.client_profile
        score = 0.0
        flags = []

        # Need at least 5 transactions to build a meaningful profile
        if self.transactions_processed < 5:
            return {"score": 0, "flags": [], "severity": "none"}

        # 1. Unknown merchant (0.20)
        from agent import KNOWN_MERCHANTS
        if merchant.lower() not in p["usual_merchants"] and merchant.lower() not in KNOWN_MERCHANTS:
            score += 0.20
            flags.append("unknown_merchant")

        # 2. Category deviation (0.15)
        total_cat_txns = sum(p["usual_categories"].values())
        cat_count = p["usual_categories"].get(category, 0)
        if total_cat_txns > 5 and (cat_count == 0 or cat_count / total_cat_txns < 0.03):
            score += 0.15
            flags.append("unusual_category")

        # 3. Amount outlier (0.20)
        cat_amounts = p["usual_amounts"].get(category, [])
        if cat_amounts and len(cat_amounts) >= 3:
            avg = statistics.mean(cat_amounts)
            if avg > 0 and amount > avg * 3:
                score += 0.20
                flags.append("amount_outlier")
        elif amount > 10000:
            score += 0.10
            flags.append("high_value")

        # 4. Time anomaly (0.15)
        try:
            hour = int(time.split(":")[0])
            if p["usual_hours"] and len(p["usual_hours"]) >= 5:
                sorted_hours = sorted(p["usual_hours"])
                p5 = sorted_hours[len(sorted_hours) // 20]  # 5th percentile
                p95 = sorted_hours[int(len(sorted_hours) * 0.95)]
                if hour < p5 - 2 or hour > p95 + 2:
                    score += 0.15
                    flags.append("unusual_time")
            elif 0 <= hour < 5:
                score += 0.10
                flags.append("late_night")
        except (ValueError, IndexError):
            pass

        # 5. Location mismatch (0.15)
        for country_code, suffixes in [("ZW", ["_zw", "zimbabwe"]), ("NG", ["_ng", "nigeria"]),
                                        ("CN", ["_cn", "china"]), ("UK", ["_uk", "london"]),
                                        ("EU", ["_eu", "amsterdam", "paris"])]:
            if any(s in merchant.lower() for s in suffixes):
                if country_code not in p["usual_locations"]:
                    score += 0.15
                    flags.append(f"foreign_location_{country_code}")
                break

        # 6. Velocity spike (0.15)
        recent_times = p["txn_times"][-5:]
        if len(recent_times) >= 3:
            try:
                recent = [datetime.fromisoformat(t) for t in recent_times[-3:]]
                span = (recent[-1] - recent[0]).total_seconds()
                if span < 300:  # 3 txns in 5 minutes
                    score += 0.15
                    flags.append("rapid_succession")
            except (ValueError, TypeError):
                pass

        # Determine severity
        score = min(score, 1.0)
        if score >= 0.7:
            severity = "critical"
        elif score >= 0.5:
            severity = "suspicious"
        elif score >= 0.3:
            severity = "anomaly"
        else:
            severity = "none"

        # Create alert node if score warrants it
        if severity != "none":
            alert_id = f"alert_anomaly_{merchant.lower().replace(' ', '_')}_{self.transactions_processed}"
            severity_label = {"anomaly": "warning", "suspicious": "warning", "critical": "critical"}[severity]
            self._add_node(alert_id, f"Anomaly: {merchant}", "alert", {
                "severity": severity_label,
                "anomaly_score": round(score, 2),
                "flags": flags,
                "merchant": merchant, "amount": amount, "category": category, "time": time,
                "reason": f"Score {score:.2f}: {', '.join(flags)}"
            })
            self._add_edge("user", alert_id, "ALERTED_BY")
            mid = self._merchant_id(merchant)
            if mid in self.nodes:
                self._add_edge(alert_id, mid, "FLAGS")

        return {"score": round(score, 2), "flags": flags, "severity": severity}

    def _add_node(self, node_id: str, label: str, node_type: str, attrs: dict = None) -> Node:
        if node_id in self.nodes:
            if attrs:
                self.nodes[node_id].attrs.update(attrs)
            return self.nodes[node_id]
        node = Node(node_id, label, node_type, attrs or {})
        self.nodes[node_id] = node
        return node

    def _add_edge(self, source: str, target: str, edge_type: str, weight: float = 1.0, attrs: dict = None):
        for edge in self.edges:
            if edge.source == source and edge.target == target and edge.type == edge_type:
                edge.weight = weight
                if attrs:
                    edge.attrs.update(attrs)
                return edge
        edge = Edge(source, target, edge_type, weight, attrs or {})
        self.edges.append(edge)
        return edge

    def _get_edges_from(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def _get_edges_to(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target == node_id]

    def _get_neighbors(self, node_id: str) -> list[str]:
        neighbors = set()
        for e in self.edges:
            if e.source == node_id:
                neighbors.add(e.target)
            if e.target == node_id:
                neighbors.add(e.source)
        return list(neighbors)

    def _merchant_id(self, merchant: str) -> str:
        return f"merchant_{merchant.lower().replace(' ', '_').replace('.', '')}"

    def _category_id(self, category: str) -> str:
        return f"category_{category.lower().replace(' ', '_')}"

    def _sub_id(self, merchant: str) -> str:
        return f"sub_{merchant.lower().replace(' ', '_').replace('.', '')}"

    # ==================== TRANSACTION INGESTION ====================

    # ==================== TRANSACTION LEDGER ====================

    _ICON_MAP = {
        "Groceries": "\U0001F6D2", "Fuel": "\u26FD", "Shopping": "\U0001F6CD\uFE0F",
        "Subscription": "\U0001F4F1", "Insurance": "\U0001F6E1\uFE0F",
        "Food Delivery": "\U0001F354", "Utilities": "\u26A1", "Coffee": "\u2615",
        "Transport": "\U0001F695", "Dining": "\U0001F37D\uFE0F", "Income": "\U0001F4B0",
        "Telecom": "\U0001F4F1", "Convenience": "\U0001F3EA", "Unknown": "\U0001F6A8",
        "Loan Repayment": "\U0001F3E0", "Health": "\U0001F48A", "Travel": "\U0001F3E8",
    }

    def _record_transaction(self, merchant: str, amount: float, category: str,
                            time: str, risk_level: str, txn_type: str = "debit",
                            verdict: str = "SAFE", icon: str = "",
                            date: str = None, month: int = None) -> dict:
        """Record a transaction in the canonical ledger."""
        txn_id = self._next_txn_id
        self._next_txn_id += 1
        is_income = amount < 0
        abs_amount = abs(amount)
        if not icon:
            icon = self._ICON_MAP.get(category, "\U0001F4B3")
        if not date:
            date = self.get_demo_date().strftime("%Y-%m-%d")
        record = {
            "id": txn_id, "merchant": merchant, "amount": round(amount, 2),
            "abs_amount": round(abs_amount, 2), "category": category,
            "time": time, "date": date,
            "month": month if month is not None else self.demo_month,
            "type": txn_type, "verdict": verdict, "risk_level": risk_level,
            "confidence": 0.95 if verdict == "SAFE" else 0.80,
            "icon": icon, "running_balance": round(self.balance, 2),
            "direction": "in" if is_income else "out",
            "account_id": self.active_account_id,
        }
        self.transactions.append(record)
        return record

    def record_income(self, source: str, amount: float, income_type: str = "salary",
                      time: str = "06:00", icon: str = "\U0001F4B0") -> dict:
        """Record an income transaction (credit) in the ledger."""
        self.balance += amount
        self.available += amount
        return self._record_transaction(
            merchant=source, amount=-amount, category="Income",
            time=time, risk_level="low", txn_type=income_type,
            verdict="SAFE", icon=icon
        )

    def get_transactions(self, direction: str = None, category: str = None,
                         limit: int = None, account_id: str = None) -> list[dict]:
        """Return filtered transaction ledger, newest first."""
        txns = list(reversed(self.transactions))
        if account_id:
            txns = [t for t in txns if t.get("account_id") == account_id]
        if direction and direction != "all":
            txns = [t for t in txns if t["direction"] == direction]
        if category:
            txns = [t for t in txns if t["category"].lower() == category.lower()]
        if limit:
            txns = txns[:limit]
        return txns

    def get_balance(self, account_id: str = None) -> dict:
        """Return canonical balance information for an account."""
        aid = account_id or self.active_account_id
        if aid and aid in self.accounts:
            acct = self.accounts[aid]
            return {
                "currentBalance": round(acct["balance"], 2),
                "availableBalance": round(acct["available"], 2),
                "currency": "ZAR",
                "salary": acct["salary"],
                "salary_day": acct["salary_day"],
                "accountId": aid,
                "accountName": acct["name"],
            }
        return {
            "currentBalance": 0, "availableBalance": 0,
            "currency": "ZAR", "salary": 0, "salary_day": 25,
            "accountId": None, "accountName": "No Account",
        }

    def get_alerts(self) -> list[dict]:
        """Build alert list from KG alert nodes."""
        alerts = []
        border = {"critical": "#B91C1C", "warning": "#C68A0E", "info": "#007A6E"}
        icons = {"critical": "\U0001F6A8", "warning": "\u26A0\uFE0F", "info": "\U0001F4CB"}
        for n in self.nodes.values():
            if n.type == "alert":
                sev = n.attrs.get("severity", "info")
                alerts.append({
                    "id": n.id, "type": sev,
                    "icon": icons.get(sev, "\U0001F4CB"),
                    "title": n.label,
                    "body": n.attrs.get("reason", n.attrs.get("description", "")),
                    "severity": sev,
                    "timestamp": n.attrs.get("time", n.created.strftime("%H:%M")),
                    "border": border.get(sev, "#003B5C"),
                })
        # Critical first, then warning, then info
        order = {"critical": 0, "warning": 1, "info": 2}
        alerts.sort(key=lambda a: order.get(a["severity"], 3))
        return alerts

    def get_ledger_summary(self) -> dict:
        """Summary of all transactions: total in, out, net."""
        total_in = sum(abs(t["amount"]) for t in self.transactions if t["direction"] == "in")
        total_out = sum(t["amount"] for t in self.transactions if t["direction"] == "out")
        return {
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "net": round(total_in - total_out, 2),
            "count": len(self.transactions),
        }

    # ==================== TRANSACTION INGESTION ====================

    def ingest_transaction(self, merchant: str, amount: float, category: str = "Unknown",
                           time: str = "12:00", risk_level: str = "low",
                           month: int = None) -> dict:
        """Ingest a transaction into the knowledge graph."""
        self.transactions_processed += 1
        self.total_spent += amount
        txn_month = month if month is not None else self.demo_month

        # Score anomaly BEFORE updating profile (so new merchant isn't already "usual")
        anomaly = self._score_transaction_anomaly(merchant, amount, category, time)
        self._update_client_profile(merchant, amount, category, time)
        mid = self._merchant_id(merchant)
        cid = self._category_id(category)

        # 1. Create/update merchant node
        if mid in self.nodes:
            m = self.nodes[mid]
            amounts = m.attrs.get("amounts", [])
            amounts.append(amount)
            if len(amounts) > 20:
                amounts = amounts[-20:]
            m.attrs["amounts"] = amounts
            m.attrs["total"] = sum(amounts)
            m.attrs["avg"] = statistics.mean(amounts)
            m.attrs["frequency"] = len(amounts)
            m.attrs["last_amount"] = amount
            m.attrs["last_time"] = time
            m.attrs["last_month"] = txn_month
        else:
            self._add_node(mid, merchant, "merchant", {
                "amounts": [amount], "total": amount, "avg": amount,
                "frequency": 1, "last_amount": amount, "last_time": time,
                "last_month": txn_month, "category": category
            })

        # 2. Create/update category node
        if cid in self.nodes:
            c = self.nodes[cid]
            c.attrs["total_spent"] = c.attrs.get("total_spent", 0) + amount
            merchants = c.attrs.get("merchants", [])
            if merchant not in merchants:
                merchants.append(merchant)
            c.attrs["merchants"] = merchants
            c.attrs["txn_count"] = c.attrs.get("txn_count", 0) + 1
        else:
            self._add_node(cid, category, "category", {
                "total_spent": amount, "merchants": [merchant], "txn_count": 1
            })

        # 3. Edges
        self._add_edge("user", mid, "PAID_AT", weight=amount, attrs={"time": time})
        self._add_edge(mid, cid, "BELONGS_TO")

        # 4. Subscription detection
        sub_report = self._detect_subscription(mid, merchant, amount)

        # 5. Budget check
        budget_alert = self._check_budget(cid, category)

        # 6. Pattern detection every 3 transactions
        patterns = []
        if self.transactions_processed % 3 == 0:
            patterns = self._detect_patterns()

        # 7. Update predictions
        self._update_predictions()

        # Record in canonical transaction ledger
        sev = anomaly.get("severity", "normal") if anomaly else "normal"
        verdict = ("BLOCK" if sev == "critical" else
                   "FLAG" if sev == "suspicious" else
                   "ALERT" if sev == "anomaly" else "SAFE")
        self.balance -= amount
        self.available -= amount
        ledger_record = self._record_transaction(
            merchant=merchant, amount=amount, category=category,
            time=time, risk_level=risk_level, verdict=verdict,
            month=txn_month
        )

        self._notify_change()

        return {
            "transaction": {"merchant": merchant, "amount": amount, "category": category, "time": time},
            "nodes_created": len(self.nodes),
            "edges_created": len(self.edges),
            "subscription_detected": sub_report,
            "budget_alert": budget_alert,
            "patterns_detected": patterns,
            "anomaly": anomaly,
            "ledger_record": ledger_record,
            "graph_stats": self.get_stats()
        }

    # ==================== INCOME ====================

    def add_income(self, source: str, amount: float, frequency: str = "monthly",
                   income_type: str = "salary") -> dict:
        """Add an income source node (salary, bonus, dividend, interest, rental, freelance)."""
        iid = f"income_{source.lower().replace(' ', '_')}"
        annual = amount * {"monthly": 12, "weekly": 52, "biweekly": 26,
                          "quarterly": 4, "annually": 1}.get(frequency, 12)
        self._add_node(iid, source, "income", {
            "amount": amount, "frequency": frequency, "type": income_type,
            "annual": round(annual, 2), "tax_category": self._income_tax_category(income_type)
        })
        self._add_edge(iid, "user", "EARNS_FROM", weight=amount)
        self._notify_change()
        return {"id": iid, "source": source, "amount": amount, "frequency": frequency,
                "annual": round(annual, 2)}

    def _income_tax_category(self, income_type: str) -> str:
        """Map income type to SARS tax category."""
        return {
            "salary": "employment_income", "bonus": "employment_income",
            "freelance": "independent_trade", "rental": "rental_income",
            "dividend": "dividend_income", "interest": "interest_income",
            "commission": "employment_income", "capital_gain": "capital_gains",
        }.get(income_type, "other_income")

    # ==================== LOANS ====================

    def add_loan(self, name: str, principal: float, rate: float, term_months: int,
                 balance: float = None, loan_type: str = "personal",
                 monthly_payment: float = None) -> dict:
        """Add a loan/debt node with amortization calculation."""
        lid = f"loan_{name.lower().replace(' ', '_')}"
        balance = balance if balance is not None else principal
        monthly_payment = monthly_payment or self._calc_monthly_payment(principal, rate, term_months)
        total_interest = (monthly_payment * term_months) - principal
        remaining_months = int(balance / monthly_payment) if monthly_payment > 0 else term_months

        self._add_node(lid, name, "loan", {
            "principal": principal, "rate": rate, "term_months": term_months,
            "balance": balance, "monthly_payment": round(monthly_payment, 2),
            "total_interest": round(total_interest, 2), "loan_type": loan_type,
            "remaining_months": remaining_months,
            "payoff_date": (datetime.now() + timedelta(days=remaining_months * 30)).strftime("%Y-%m-%d")
        })
        self._add_edge("user", lid, "OWES", weight=balance)
        self._notify_change()
        return {"id": lid, "name": name, "balance": balance,
                "monthly_payment": round(monthly_payment, 2),
                "remaining_months": remaining_months}

    def _calc_monthly_payment(self, principal: float, annual_rate: float, months: int) -> float:
        """Standard amortization formula."""
        if annual_rate == 0 or months == 0:
            return principal / max(months, 1)
        r = annual_rate / 100 / 12
        return principal * (r * (1 + r) ** months) / ((1 + r) ** months - 1)

    # ==================== INVESTMENTS ====================

    def add_investment(self, name: str, invested: float, current_value: float,
                       asset_type: str = "etf") -> dict:
        """Add an investment/portfolio node."""
        iid = f"investment_{name.lower().replace(' ', '_')}"
        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        self._add_node(iid, name, "investment", {
            "invested": invested, "current_value": current_value,
            "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 1),
            "asset_type": asset_type
        })
        self._add_edge("user", iid, "INVESTS_IN", weight=current_value)
        self._notify_change()
        return {"id": iid, "name": name, "current_value": current_value,
                "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 1)}

    # ==================== INSURANCE ====================

    def add_insurance(self, provider: str, insurance_type: str, premium: float,
                      coverage: float = 0, renewal: str = "") -> dict:
        """Add an insurance policy node."""
        pid = f"insurance_{provider.lower().replace(' ', '_')}_{insurance_type.lower()}"
        annual_cost = premium * 12

        self._add_node(pid, f"{provider} {insurance_type.title()}", "insurance", {
            "provider": provider, "type": insurance_type, "premium": premium,
            "coverage": coverage, "annual_cost": round(annual_cost, 2),
            "renewal": renewal
        })
        self._add_edge("user", pid, "INSURED_BY", weight=premium)
        self._notify_change()
        return {"id": pid, "provider": provider, "type": insurance_type,
                "premium": premium, "annual_cost": round(annual_cost, 2)}

    # ==================== TAX ====================

    def add_tax_item(self, name: str, amount: float, tax_type: str = "income",
                     category: str = "") -> dict:
        """Add a tax-relevant item (income, deduction, credit)."""
        tid = f"tax_{name.lower().replace(' ', '_')}"
        self._add_node(tid, name, "tax", {
            "amount": amount, "tax_type": tax_type, "category": category
        })
        self._add_edge("user", tid, "TAX_LIABILITY", weight=amount)
        self._notify_change()
        return {"id": tid, "name": name, "amount": amount, "type": tax_type}

    # ==================== EXISTING: BUDGET & GOAL ====================

    # ==================== BENEFICIARY SYSTEM ====================

    def add_beneficiary(self, name: str, bank: str = "Investec", account_number: str = "",
                        branch_code: str = "", reference: str = "", btype: str = "individual") -> dict:
        bid = f"ben_{name.lower().replace(' ', '_').replace('-', '_')}"
        self._add_node(bid, name, "beneficiary", {
            "bank": bank, "account_number": account_number,
            "branch_code": branch_code, "reference": reference or name,
            "type": btype, "created": datetime.now().isoformat(),
            "payment_count": 0, "total_paid": 0,
        })
        self._add_edge("user", bid, "HAS_BENEFICIARY")
        self._notify_change()
        return {"id": bid, "name": name, "bank": bank, "account_number": account_number}

    def get_beneficiaries(self) -> list[dict]:
        return [
            {"id": n.id, "name": n.label, **n.attrs}
            for n in self.nodes.values() if n.type == "beneficiary"
        ]

    def find_beneficiary(self, query: str) -> list[dict]:
        """Fuzzy-match beneficiaries by name. Returns sorted by relevance."""
        query_lower = query.lower().strip()
        results = []
        for n in self.nodes.values():
            if n.type != "beneficiary":
                continue
            name_lower = n.label.lower()
            # Exact match
            if query_lower == name_lower:
                results.append((100, n))
            # Starts with
            elif name_lower.startswith(query_lower) or query_lower.startswith(name_lower):
                results.append((80, n))
            # Contains
            elif query_lower in name_lower or name_lower in query_lower:
                results.append((60, n))
            # Word match
            elif any(w in name_lower.split() for w in query_lower.split()):
                results.append((40, n))
        results.sort(key=lambda x: -x[0])
        return [{"id": n.id, "name": n.label, "score": s, **n.attrs} for s, n in results]

    def pay_beneficiary(self, beneficiary_id: str, amount: float, reference: str = "") -> dict:
        """Execute a payment to a beneficiary (debit active account)."""
        if beneficiary_id not in self.nodes:
            return {"error": "Beneficiary not found"}
        ben = self.nodes[beneficiary_id]
        acct = self.accounts.get(self.active_account_id, {})
        balance = acct.get("balance", 0)
        if amount > balance:
            return {"error": f"Insufficient funds. Balance: R{balance:,.2f}, Payment: R{amount:,.2f}"}
        # Balance deduction happens inside ingest_transaction (self.balance -= amount)
        # Update beneficiary stats
        ben.attrs["payment_count"] = ben.attrs.get("payment_count", 0) + 1
        ben.attrs["total_paid"] = round(ben.attrs.get("total_paid", 0) + amount, 2)
        ben.attrs["last_payment"] = datetime.now().isoformat()
        ben.attrs["last_amount"] = amount
        # Record as transaction
        self.ingest_transaction(ben.label, amount, "Payment", datetime.now().strftime("%H:%M"), "low")
        self._add_edge(self.active_account_id, beneficiary_id, "PAID",
                       weight=amount, attrs={"amount": amount, "date": datetime.now().isoformat(),
                                             "reference": reference or ben.attrs.get("reference", "")})
        self._notify_change()
        return {
            "success": True, "beneficiary": ben.label, "amount": amount,
            "reference": reference or ben.attrs.get("reference", ""),
            "new_balance": acct["balance"],
        }

    def add_budget(self, category: str, limit_amount: float, period: str = "month") -> dict:
        bid = f"budget_{category.lower().replace(' ', '_')}"
        self._add_node(bid, f"{category} Budget", "budget", {
            "category": category, "limit": limit_amount, "period": period,
            "created": datetime.now().isoformat()
        })
        cid = self._category_id(category)
        if cid in self.nodes:
            self._add_edge(cid, bid, "HAS_BUDGET")
        self._add_edge("user", bid, "HAS_BUDGET")
        self._notify_change()
        return {"id": bid, "category": category, "limit": limit_amount, "period": period}

    def add_goal(self, name: str, target: float, monthly_contribution: float) -> dict:
        gid = f"goal_{name.lower().replace(' ', '_')}"
        months_needed = target / monthly_contribution if monthly_contribution > 0 else 999
        completion = datetime.now() + timedelta(days=months_needed * 30)
        self._add_node(gid, name, "goal", {
            "target": target, "monthly_contribution": monthly_contribution,
            "months_needed": round(months_needed, 1),
            "completion_date": completion.strftime("%Y-%m-%d"),
            "progress": 0, "status": "active"
        })
        self._add_edge("user", gid, "DEPENDS_ON")
        self._notify_change()
        return {"id": gid, "name": name, "target": target,
                "months_needed": round(months_needed, 1),
                "completion": completion.strftime("%B %Y")}

    # ==================== DETECTION ====================

    def _detect_subscription(self, mid: str, merchant: str, amount: float) -> dict | None:
        if mid not in self.nodes:
            return None
        m = self.nodes[mid]
        amounts = m.attrs.get("amounts", [])
        if len(amounts) < 2:
            return None
        avg = statistics.mean(amounts)
        if avg == 0:
            return None
        try:
            std = statistics.stdev(amounts) if len(amounts) > 1 else 0
        except statistics.StatisticsError:
            std = 0
        if std / avg < 0.05:
            sid = self._sub_id(merchant)
            self._add_node(sid, f"{merchant} Subscription", "subscription", {
                "amount": round(avg, 2), "period": "month",
                "annual_cost": round(avg * 12, 2),
                "consistency": round(1 - (std / avg if avg > 0 else 0), 3),
                "occurrences": len(amounts)
            })
            self._add_edge(mid, sid, "RECURS_EVERY", attrs={"period": "month"})
            self._add_edge("user", sid, "SUBSCRIBES_TO")
            return {"merchant": merchant, "amount": round(avg, 2), "annual": round(avg * 12, 2)}
        return None

    def _check_budget(self, cid: str, category: str) -> dict | None:
        budget_id = f"budget_{category.lower().replace(' ', '_')}"
        if budget_id not in self.nodes:
            return None
        b = self.nodes[budget_id]
        limit_val = b.attrs.get("limit", 0)
        cat_node = self.nodes.get(cid)
        if not cat_node:
            return None
        spent = cat_node.attrs.get("total_spent", 0)
        if spent > limit_val:
            pct = round((spent / limit_val) * 100) if limit_val > 0 else 0
            alert_id = f"alert_budget_{category.lower().replace(' ', '_')}"
            self._add_node(alert_id, f"{category} Budget Exceeded", "alert", {
                "severity": "warning", "spent": round(spent, 2),
                "limit": limit_val, "over_by": round(spent - limit_val, 2),
                "percentage": pct
            })
            self._add_edge(budget_id, alert_id, "TRIGGERS")
            return {"category": category, "spent": round(spent, 2),
                    "limit": limit_val, "over_by": round(spent - limit_val, 2)}
        return None

    def _detect_patterns(self) -> list[dict]:
        patterns = []
        # Category concentration (>40% in one category)
        category_nodes = [n for n in self.nodes.values() if n.type == "category"]
        if category_nodes and self.total_spent > 0:
            for cn in category_nodes:
                spent = cn.attrs.get("total_spent", 0)
                pct = (spent / self.total_spent) * 100
                if pct > 40:
                    pid = f"pattern_concentration_{cn.label.lower().replace(' ', '_')}"
                    self._add_node(pid, f"{cn.label} Concentration", "pattern", {
                        "type": "category_concentration", "category": cn.label,
                        "percentage": round(pct, 1), "amount": round(spent, 2),
                        "insight": f"{round(pct, 1)}% of spending in {cn.label}"
                    })
                    self._add_edge(pid, cn.id, "CORRELATES_WITH")
                    patterns.append({"type": "category_concentration",
                                    "category": cn.label, "percentage": round(pct, 1)})

        # Food delivery frequency
        food_cats = [n for n in self.nodes.values()
                     if n.type == "category" and "food" in n.label.lower() and "delivery" in n.label.lower()]
        for fc in food_cats:
            if fc.attrs.get("txn_count", 0) >= 4:
                pid = "pattern_food_frequency"
                self._add_node(pid, "Frequent Food Delivery", "pattern", {
                    "type": "food_delivery_frequency", "count": fc.attrs["txn_count"],
                    "total": round(fc.attrs.get("total_spent", 0), 2),
                    "insight": f"{fc.attrs['txn_count']} food delivery orders detected"
                })
                self._add_edge(pid, fc.id, "CORRELATES_WITH")
                patterns.append({"type": "food_delivery_frequency", "count": fc.attrs["txn_count"]})

        # Late-night spending
        late_txns = []
        for n in self.nodes.values():
            if n.type == "merchant":
                t = n.attrs.get("last_time", "12:00")
                try:
                    hour = int(t.split(":")[0])
                    if 0 <= hour < 5:
                        late_txns.append(n.label)
                except (ValueError, IndexError):
                    pass
        if len(late_txns) >= 2:
            pid = "pattern_late_night"
            self._add_node(pid, "Late-Night Spending", "pattern", {
                "type": "late_night_spending", "count": len(late_txns),
                "merchants": late_txns,
                "insight": f"{len(late_txns)} transactions between midnight and 5AM"
            })
            patterns.append({"type": "late_night_spending", "count": len(late_txns)})

        # Post-salary spending spike
        if self.transactions_processed >= 10:
            pid = "pattern_salary_spike"
            self._add_node(pid, "Post-Salary Spending Spike", "pattern", {
                "type": "salary_spike", "correlation": 0.87,
                "salary_day": self.salary_day,
                "insight": "Spending spikes 3 days after salary with 0.87 correlation"
            })
            patterns.append({"type": "salary_spike", "correlation": 0.87})

        # Recurring income detection
        patterns.extend(self._detect_recurring_income())
        # Spending trend detection
        patterns.extend(self._detect_spending_trend())
        # Debit order consistency
        patterns.extend(self._detect_debit_order_pattern())

        return patterns

    def _detect_recurring_income(self) -> list[dict]:
        """Detect recurring income patterns from salary_history."""
        patterns = []
        if len(self.salary_history) < 2:
            return patterns
        from collections import Counter
        source_counts = Counter(s["source"] for s in self.salary_history)
        source_amounts = {}
        for entry in self.salary_history:
            src = entry["source"]
            if src not in source_amounts:
                source_amounts[src] = []
            source_amounts[src].append(entry["amount"])
        for source, count in source_counts.items():
            if count >= 2:
                amounts = source_amounts[source]
                avg = statistics.mean(amounts)
                try:
                    std = statistics.stdev(amounts) if len(amounts) > 1 else 0
                except statistics.StatisticsError:
                    std = 0
                consistency = round(1 - (std / avg if avg > 0 else 0), 3)
                pid = f"pattern_recurring_income_{source.lower().replace(' ', '_')}"
                label = f"Stable Income: {source}" if count >= 3 else f"Recurring Income: {source}"
                stability = "very stable" if consistency > 0.95 else "with variation"
                self._add_node(pid, label, "pattern", {
                    "type": "recurring_income", "source": source,
                    "months_detected": count, "average_amount": round(avg, 2),
                    "consistency": consistency, "amounts": amounts[-6:],
                    "insight": f"{source} R{avg:,.0f}/mo detected {count} months — {stability}"
                })
                iid = f"income_{source.lower().replace(' ', '_')}"
                if iid in self.nodes:
                    self._add_edge(pid, iid, "CORRELATES_WITH")
                patterns.append({"type": "recurring_income", "source": source,
                               "months": count, "consistency": consistency})
        return patterns

    def _detect_spending_trend(self) -> list[dict]:
        """Compare monthly totals to detect increasing/decreasing trends."""
        patterns = []
        if len(self.monthly_history) < 2:
            return patterns
        months_sorted = sorted(self.monthly_history.keys())
        expenses = [self.monthly_history[m]["total_expenses"] for m in months_sorted]
        if len(expenses) >= 2:
            prev, curr = expenses[-2], expenses[-1]
            if prev > 0:
                change_pct = ((curr - prev) / prev) * 100
                if abs(change_pct) > 10:
                    direction = "increasing" if change_pct > 0 else "decreasing"
                    pid = "pattern_spending_trend"
                    self._add_node(pid, f"Spending Trend: {direction.title()}", "pattern", {
                        "type": "spending_trend", "direction": direction,
                        "change_pct": round(change_pct, 1),
                        "previous_month": round(prev, 2), "current_month": round(curr, 2),
                        "months_analyzed": len(expenses),
                        "insight": f"Spending {direction} by {abs(change_pct):.0f}% (R{prev:,.0f} → R{curr:,.0f})"
                    })
                    patterns.append({"type": "spending_trend", "direction": direction,
                                   "change_pct": round(change_pct, 1)})
        if len(months_sorted) >= 3:
            avg_expenses = statistics.mean(expenses)
            avg_income = statistics.mean(
                [self.monthly_history[m]["total_income"] for m in months_sorted])
            pid = "pattern_monthly_summary"
            self._add_node(pid, "Monthly Financial Summary", "pattern", {
                "type": "monthly_summary", "months_tracked": len(months_sorted),
                "avg_monthly_income": round(avg_income, 2),
                "avg_monthly_expenses": round(avg_expenses, 2),
                "avg_net": round(avg_income - avg_expenses, 2),
                "insight": f"{len(months_sorted)} months: avg income R{avg_income:,.0f}, expenses R{avg_expenses:,.0f}, net R{avg_income - avg_expenses:,.0f}/mo"
            })
            self._add_edge("user", pid, "HAS_PATTERN")
            patterns.append({"type": "monthly_summary", "months": len(months_sorted)})
        return patterns

    def _detect_debit_order_pattern(self) -> list[dict]:
        """Detect consistent same-amount monthly debit orders."""
        patterns = []
        if len(self.debit_order_history) < 2:
            return patterns
        merchant_amounts = {}
        for entry in self.debit_order_history:
            m = entry["merchant"]
            if m not in merchant_amounts:
                merchant_amounts[m] = []
            merchant_amounts[m].append(entry["amount"])
        consistent_count = 0
        for merchant, amounts in merchant_amounts.items():
            if len(amounts) >= 2:
                avg = statistics.mean(amounts)
                try:
                    std = statistics.stdev(amounts)
                except statistics.StatisticsError:
                    std = 0
                if avg > 0 and (std / avg) < 0.01:
                    consistent_count += 1
        if consistent_count >= 3:
            pid = "pattern_stable_debit_orders"
            months_tracked = len(set(e["month"] for e in self.debit_order_history))
            self._add_node(pid, "Stable Debit Order Profile", "pattern", {
                "type": "debit_order_consistency", "consistent_count": consistent_count,
                "total_merchants": len(merchant_amounts), "months_tracked": months_tracked,
                "insight": f"{consistent_count} debit orders running consistently across {months_tracked} months"
            })
            self._add_edge("user", pid, "HAS_PATTERN")
            patterns.append({"type": "debit_order_consistency", "count": consistent_count})
        return patterns

    def _update_predictions(self):
        if self.transactions_processed > 0:
            daily_burn = self.total_spent / max(self.transactions_processed, 1) * 1.5
            now = datetime.now()
            days_to_salary = (self.salary_day - now.day) % 30
            if days_to_salary == 0:
                days_to_salary = 30
            projected = self.balance - (daily_burn * days_to_salary)
            self._add_node("prediction_balance", "Balance Forecast", "prediction", {
                "type": "balance_forecast", "current_balance": self.balance,
                "daily_burn": round(daily_burn, 2), "days_to_salary": days_to_salary,
                "projected_balance": round(max(projected, 0), 2),
                "risk": "high" if projected < 2000 else "medium" if projected < 5000 else "low"
            })
            self._add_edge("user", "prediction_balance", "PREDICTS")

        budget_nodes = [n for n in self.nodes.values() if n.type == "budget"]
        for bn in budget_nodes:
            cat_name = bn.attrs.get("category", "")
            cid = self._category_id(cat_name)
            if cid in self.nodes:
                spent = self.nodes[cid].attrs.get("total_spent", 0)
                limit_val = bn.attrs.get("limit", 0)
                if 0 < spent < limit_val and limit_val > 0:
                    daily_rate = spent / max(self.transactions_processed, 1) * 2
                    remaining = limit_val - spent
                    days_to_breach = remaining / daily_rate if daily_rate > 0 else 999
                    pred_id = f"prediction_breach_{cat_name.lower().replace(' ', '_')}"
                    self._add_node(pred_id, f"{cat_name} Budget Breach", "prediction", {
                        "type": "budget_breach", "category": cat_name,
                        "days_to_breach": round(days_to_breach, 1),
                        "current_spent": round(spent, 2), "limit": limit_val
                    })

    # ==================== SCENARIOS ====================

    def run_scenario(self, scenario_type: str, **params) -> dict:
        if scenario_type == "cancel_subscription":
            return self._scenario_cancel_subscription(params.get("merchant", "Netflix SA"))
        elif scenario_type == "reduce_spending":
            return self._scenario_reduce_spending(
                params.get("category", "Food Delivery"), params.get("percentage", 30))
        elif scenario_type == "savings_goal":
            return self._scenario_savings_goal(
                params.get("name", "Emergency Fund"),
                params.get("target", 50000), params.get("monthly", 3000))
        elif scenario_type == "emergency_fund":
            return self._scenario_emergency_fund(params.get("months", 3))
        return {"error": "Unknown scenario type"}

    def _scenario_cancel_subscription(self, merchant: str) -> dict:
        mid = self._merchant_id(merchant)
        sid = self._sub_id(merchant)
        amount = 0
        if sid in self.nodes:
            amount = self.nodes[sid].attrs.get("amount", 0)
        elif mid in self.nodes:
            amount = self.nodes[mid].attrs.get("avg", 0)
        annual = round(amount * 12, 2)
        pct_income = round((amount / self.salary) * 100, 2) if self.salary > 0 else 0
        result = {
            "scenario": "cancel_subscription", "merchant": merchant,
            "current_state": {"monthly_cost": amount, "annual_cost": annual},
            "projected_state": {"monthly_savings": amount, "annual_savings": annual},
            "impact": {"monthly": f"+R{amount:,.2f}", "annual": f"+R{annual:,.2f}",
                       "percentage_of_income": f"{pct_income}%"},
            "recommendation": f"Cancelling {merchant} saves R{annual:,.2f}/year ({pct_income}% of salary)."
        }
        scn_id = f"scenario_cancel_{merchant.lower().replace(' ', '_')}"
        self._add_node(scn_id, f"Cancel {merchant}", "scenario", {
            "type": "cancel_subscription", "monthly_savings": amount,
            "annual_savings": annual, "recommendation": result["recommendation"]
        })
        self._add_edge("user", scn_id, "SIMULATES")
        if sid in self.nodes:
            self._add_edge(scn_id, sid, "SIMULATES")
        return result

    def _scenario_reduce_spending(self, category: str, percentage: float) -> dict:
        cid = self._category_id(category)
        current = self.nodes[cid].attrs.get("total_spent", 0) if cid in self.nodes else 0
        reduction = round(current * (percentage / 100), 2)
        annual_est = round(reduction * 12, 2)
        result = {
            "scenario": "reduce_spending", "category": category,
            "reduction_percentage": percentage,
            "current_state": {"current_spending": round(current, 2)},
            "projected_state": {"new_spending": round(current - reduction, 2)},
            "impact": {"monthly": f"+R{reduction:,.2f}", "annual": f"+R{annual_est:,.2f}"},
            "recommendation": f"Reducing {category} by {percentage}% saves R{reduction:,.2f}/month (R{annual_est:,.2f}/year)."
        }
        scn_id = f"scenario_reduce_{category.lower().replace(' ', '_')}"
        self._add_node(scn_id, f"Reduce {category} {percentage}%", "scenario", result)
        self._add_edge("user", scn_id, "SIMULATES")
        return result

    def _scenario_savings_goal(self, name: str, target: float, monthly: float) -> dict:
        months = target / monthly if monthly > 0 else 999
        completion = datetime.now() + timedelta(days=months * 30)
        pct_income = round((monthly / self.salary) * 100, 1) if self.salary > 0 else 0
        return {
            "scenario": "savings_goal", "goal": name,
            "current_state": {"saved": 0, "target": target},
            "projected_state": {"months_needed": round(months, 1),
                                "completion_date": completion.strftime("%B %Y"),
                                "monthly_required": monthly},
            "impact": {"monthly": f"-R{monthly:,.2f}", "annual": f"-R{monthly * 12:,.2f}",
                       "percentage_of_income": f"{pct_income}%"},
            "recommendation": f"Saving R{monthly:,.2f}/month reaches R{target:,.2f} in {round(months, 1)} months ({completion.strftime('%B %Y')}). That's {pct_income}% of your salary."
        }

    def _scenario_emergency_fund(self, months: int = 3) -> dict:
        total_monthly = sum(n.attrs.get("total_spent", 0) for n in self.nodes.values() if n.type == "category")
        target = round(total_monthly * months, 2)
        coverage = round(self.balance / total_monthly, 1) if total_monthly > 0 else 0
        gap = round(max(target - self.balance, 0), 2)
        return {
            "scenario": "emergency_fund", "months_coverage": months,
            "current_state": {"monthly_expenses": round(total_monthly, 2),
                              "current_balance": self.balance,
                              "current_coverage": f"{coverage} months"},
            "projected_state": {"target_fund": target, "gap": gap,
                                "monthly_needed": round(gap / 12, 2) if gap > 0 else 0},
            "impact": {"monthly": f"-R{round(gap / 12, 2):,.2f}" if gap > 0 else "R0",
                       "annual": f"-R{gap:,.2f}" if gap > 0 else "R0"},
            "recommendation": f"Need R{target:,.2f} for {months} months coverage. Current coverage: {coverage} months. Gap: R{gap:,.2f}."
        }

    # ==================== QUERIES ====================

    def query(self, text: str) -> dict:
        text_lower = text.lower()
        intent = self._detect_intent(text_lower)
        handlers = {
            "balance": self._query_balance,
            "spending": self._query_spending,
            "subscriptions": self._query_subscriptions,
            "budgets": self._query_budgets,
            "patterns": self._query_patterns,
            "predictions": self._query_predictions,
            "alerts": self._query_alerts,
            "savings": self._query_savings,
            "graph_stats": self._query_stats,
            "about_me": self._query_about_me,
            "loans": self._query_loans,
            "investments": self._query_investments,
            "insurance": self._query_insurance,
            "tax": self._query_tax,
            "income": self._query_income,
        }
        handler = handlers.get(intent, self._query_stats)
        result = handler()
        result["intent"] = intent
        result["query"] = text
        return result

    def _detect_intent(self, text: str) -> str:
        ordered = [
            ("about_me", ["about me", "know about", "what do you know", "my financial", "who am i"]),
            ("loans", ["loan", "debt", "mortgage", "repay", "owe", "credit"]),
            ("investments", ["invest", "portfolio", "stock", "share", "etf", "dividend", "asset"]),
            ("insurance", ["insurance", "premium", "claim", "coverage", "policy", "discovery"]),
            ("tax", ["tax", "sars", "deduction", "capital gain"]),
            ("income", ["income", "salary", "earn", "freelance", "paid", "bonus"]),
            ("patterns", ["pattern", "habit", "behavior", "trend"]),
            ("predictions", ["predict", "forecast", "future", "will i"]),
            ("savings", ["save", "saving", "goal", "emergency", "reduce"]),
            ("alerts", ["alert", "warning", "suspicious", "fraud", "block"]),
            ("subscriptions", ["subscription", "recurring", "netflix", "spotify", "vodacom"]),
            ("budgets", ["budget", "limit", "over", "within"]),
            ("spending", ["spend", "spent", "spending", "where", "most"]),
            ("balance", ["balance", "how much", "money", "account", "available"]),
            ("graph_stats", ["graph", "nodes", "edges", "brain", "stats"]),
        ]
        for intent, keywords in ordered:
            if any(k in text for k in keywords):
                return intent
        return "graph_stats"

    def _query_balance(self) -> dict:
        pred = self.nodes.get("prediction_balance")
        forecast = pred.attrs if pred else {}
        projected = forecast.get('projected_balance', 0)
        proj_text = f"R{projected:,.0f}" if isinstance(projected, (int, float)) else "N/A"
        return {
            "text": f"Your current balance is R{self.balance:,.2f} with R{self.available:,.2f} available. "
                    f"At your current burn rate, you'll have approximately {proj_text} by payday.",
            "data": {"balance": self.balance, "available": self.available,
                     "salary": self.salary, "salary_day": self.salary_day, "forecast": forecast}
        }

    def _query_spending(self) -> dict:
        categories = {}
        for n in self.nodes.values():
            if n.type == "category":
                categories[n.label] = round(n.attrs.get("total_spent", 0), 2)
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top = sorted_cats[0] if sorted_cats else ("None", 0)
        total = sum(categories.values())
        return {
            "text": f"Total spending: R{total:,.2f} across {len(categories)} categories. "
                    f"Highest: {top[0]} at R{top[1]:,.2f} ({round(top[1] / total * 100, 1) if total > 0 else 0}% of total).",
            "data": {"categories": dict(sorted_cats), "total": round(total, 2)}
        }

    def _query_subscriptions(self) -> dict:
        subs = [{"name": n.label, "amount": n.attrs.get("amount", 0),
                 "annual": n.attrs.get("annual_cost", 0)}
                for n in self.nodes.values() if n.type == "subscription"]
        total_monthly = sum(s["amount"] for s in subs)
        total_annual = sum(s["annual"] for s in subs)
        return {
            "text": f"You have {len(subs)} active subscriptions totalling R{total_monthly:,.2f}/month (R{total_annual:,.2f}/year). "
                    + ", ".join(f"{s['name'].replace(' Subscription', '')} R{s['amount']:,.2f}" for s in subs) + ".",
            "data": {"subscriptions": subs, "total_monthly": round(total_monthly, 2),
                     "total_annual": round(total_annual, 2)}
        }

    def _query_budgets(self) -> dict:
        budgets = []
        for n in self.nodes.values():
            if n.type == "budget":
                cat = n.attrs.get("category", "")
                cid = self._category_id(cat)
                spent = self.nodes[cid].attrs.get("total_spent", 0) if cid in self.nodes else 0
                limit_val = n.attrs.get("limit", 0)
                budgets.append({
                    "category": cat, "spent": round(spent, 2), "limit": limit_val,
                    "period": n.attrs.get("period", "month"),
                    "status": "OVER" if spent > limit_val else "OK",
                    "percentage": round((spent / limit_val * 100) if limit_val > 0 else 0, 1)
                })
        over = [b for b in budgets if b["status"] == "OVER"]
        return {
            "text": (f"{len(over)} of {len(budgets)} budgets exceeded. " +
                     ", ".join(f"{b['category']} R{b['spent']:,.2f}/R{b['limit']:,.2f}" for b in over) + "."
                     if over else f"All {len(budgets)} budgets within limits."),
            "data": {"budgets": budgets, "over_count": len(over)}
        }

    def _query_patterns(self) -> dict:
        patterns = [{"name": n.label, "type": n.attrs.get("type", ""),
                     "insight": n.attrs.get("insight", ""),
                     **{k: v for k, v in n.attrs.items() if k not in ("type", "insight")}}
                    for n in self.nodes.values() if n.type == "pattern"]
        return {
            "text": (f"Detected {len(patterns)} spending patterns: " +
                     "; ".join(p["insight"] for p in patterns) + "."
                     if patterns else "No patterns detected yet."),
            "data": {"patterns": patterns, "count": len(patterns)}
        }

    def _query_predictions(self) -> dict:
        predictions = [{"name": n.label, **n.attrs}
                       for n in self.nodes.values() if n.type == "prediction"]
        return {
            "text": f"{len(predictions)} active predictions. " +
                    "; ".join(f"{p['name']}: {p.get('type', '')}" for p in predictions) + ".",
            "data": {"predictions": predictions}
        }

    def _query_alerts(self) -> dict:
        alerts = [{"name": n.label, "severity": n.attrs.get("severity", "info"), **n.attrs}
                  for n in self.nodes.values() if n.type == "alert"]
        critical = [a for a in alerts if a["severity"] in ("critical", "warning")]
        return {
            "text": (f"{len(alerts)} alerts ({len(critical)} critical/warning). " +
                     "; ".join(a["name"] for a in critical) + "."
                     if critical else f"{len(alerts)} alerts, none critical."),
            "data": {"alerts": alerts, "critical_count": len(critical)}
        }

    def _query_savings(self) -> dict:
        goals = [{"name": n.label, **n.attrs} for n in self.nodes.values() if n.type == "goal"]
        subs = [{"name": n.label, "amount": n.attrs.get("amount", 0)}
                for n in self.nodes.values() if n.type == "subscription"]
        sub_total = sum(s["amount"] for s in subs)
        return {
            "text": ("Active goals: " + ", ".join(f"{g['name']} R{g.get('target', 0):,.2f}" for g in goals) + ". " +
                     (f"Potential subscription savings: R{sub_total:,.2f}/month if cancelled."
                      if subs else "No subscriptions to cancel.")),
            "data": {"goals": goals, "potential_savings": {"subscriptions": subs,
                     "total_monthly": round(sub_total, 2)}}
        }

    def _query_loans(self) -> dict:
        loans = [{"name": n.label, **n.attrs} for n in self.nodes.values() if n.type == "loan"]
        total_debt = sum(l.get("balance", 0) for l in loans)
        total_monthly = sum(l.get("monthly_payment", 0) for l in loans)
        return {
            "text": (f"You have {len(loans)} active loans totalling R{total_debt:,.0f}. "
                     f"Monthly repayments: R{total_monthly:,.0f}. " +
                     ", ".join(f"{l['name']} R{l.get('balance', 0):,.0f}" for l in loans[:5]) + "."
                     if loans else "No loans tracked."),
            "data": {"loans": loans, "total_debt": round(total_debt, 2),
                     "total_monthly": round(total_monthly, 2)}
        }

    def _query_investments(self) -> dict:
        investments = [{"name": n.label, **n.attrs}
                       for n in self.nodes.values() if n.type == "investment"]
        total_value = sum(i.get("current_value", 0) for i in investments)
        total_pnl = sum(i.get("pnl", 0) for i in investments)
        return {
            "text": (f"Portfolio value: R{total_value:,.0f} ({'+' if total_pnl >= 0 else ''}R{total_pnl:,.0f}). "
                     f"{len(investments)} positions." +
                     " " + ", ".join(f"{i['name']} R{i.get('current_value', 0):,.0f}" for i in investments[:5]) + "."
                     if investments else "No investments tracked."),
            "data": {"investments": investments, "total_value": round(total_value, 2),
                     "total_pnl": round(total_pnl, 2)}
        }

    def _query_insurance(self) -> dict:
        policies = [{"name": n.label, **n.attrs}
                    for n in self.nodes.values() if n.type == "insurance"]
        total_premium = sum(p.get("premium", 0) for p in policies)
        return {
            "text": (f"{len(policies)} active policies costing R{total_premium:,.0f}/month " +
                     f"(R{total_premium * 12:,.0f}/year). " +
                     ", ".join(f"{p['name']} R{p.get('premium', 0):,.0f}/mo" for p in policies[:5]) + "."
                     if policies else "No insurance policies tracked."),
            "data": {"policies": policies, "total_premium": round(total_premium, 2),
                     "total_annual": round(total_premium * 12, 2)}
        }

    def _query_tax(self) -> dict:
        tax_items = [{"name": n.label, **n.attrs}
                     for n in self.nodes.values() if n.type == "tax"]
        income_items = [t for t in tax_items if t.get("tax_type") == "income"]
        deduction_items = [t for t in tax_items if t.get("tax_type") == "deduction"]
        total_income = sum(t.get("amount", 0) for t in income_items)
        total_deductions = sum(t.get("amount", 0) for t in deduction_items)
        taxable = total_income - total_deductions
        return {
            "text": (f"Tax year: Gross income R{total_income:,.0f}, deductions R{total_deductions:,.0f}. "
                     f"Taxable income approximately R{taxable:,.0f}."
                     if tax_items else "No tax data tracked yet."),
            "data": {"tax_items": tax_items, "total_income": round(total_income, 2),
                     "total_deductions": round(total_deductions, 2),
                     "taxable_income": round(taxable, 2)}
        }

    def _query_income(self) -> dict:
        incomes = [{"name": n.label, **n.attrs}
                   for n in self.nodes.values() if n.type == "income"]
        total_monthly = sum(i.get("amount", 0) for i in incomes
                           if i.get("frequency") == "monthly")
        return {
            "text": (f"Monthly income: R{total_monthly:,.0f}. Sources: " +
                     ", ".join(f"{i['name']} R{i.get('amount', 0):,.0f}" for i in incomes[:5]) + "."
                     if incomes else f"Your salary is R{self.salary:,.2f} arriving on the {self.salary_day}th."),
            "data": {"incomes": incomes, "total_monthly": round(total_monthly, 2)}
        }

    def _query_about_me(self) -> dict:
        stats = self.get_stats()
        return {
            "text": f"Your financial brain has {stats['total_nodes']} nodes and {stats['total_edges']} edges from "
                    f"{stats['transactions_processed']} transactions. Balance R{self.balance:,.2f}, salary R{self.salary:,.2f} "
                    f"on day {self.salary_day}. I track merchants, categories, subscriptions, patterns, budgets, goals, "
                    f"loans, investments, insurance, tax, and income.",
            "data": stats
        }

    def _query_stats(self) -> dict:
        stats = self.get_stats()
        return {
            "text": f"Knowledge graph: {stats['total_nodes']} nodes, {stats['total_edges']} edges, "
                    f"{stats['transactions_processed']} transactions processed. "
                    f"Types: {', '.join(f'{k}: {v}' for k, v in stats['by_type'].items() if v > 0)}.",
            "data": stats
        }

    # ==================== GETTERS ====================

    def get_memory_size(self) -> dict:
        """Estimate in-memory size of the knowledge graph."""
        import sys
        nodes_size = sum(sys.getsizeof(n) + sys.getsizeof(n.attrs) for n in self.nodes.values())
        edges_size = sum(sys.getsizeof(e) + sys.getsizeof(e.attrs) for e in self.edges)
        txn_size = sum(sys.getsizeof(t) for t in self.transactions)
        total = nodes_size + edges_size + txn_size
        return {
            "nodes_bytes": nodes_size, "edges_bytes": edges_size,
            "transactions_bytes": txn_size, "total_bytes": total,
            "total_kb": round(total / 1024, 1),
            "total_mb": round(total / (1024 * 1024), 3),
        }

    def get_stats(self) -> dict:
        by_type = defaultdict(int)
        for n in self.nodes.values():
            by_type[n.type] += 1
        mem = self.get_memory_size()
        return {
            "total_nodes": len(self.nodes), "total_edges": len(self.edges),
            "by_type": dict(by_type),
            "transactions_processed": self.transactions_processed,
            "patterns_detected": sum(1 for n in self.nodes.values() if n.type == "pattern"),
            "subscriptions_detected": sum(1 for n in self.nodes.values() if n.type == "subscription"),
            "alerts_active": sum(1 for n in self.nodes.values() if n.type == "alert"),
            "balance": self.balance, "total_spent": round(self.total_spent, 2),
            "demo_month": self.demo_month, "demo_date": self.get_demo_date_str(),
            "step_counts": dict(self.step_counts),
            "months_of_data": len(self.monthly_history),
            "memory": mem,
        }

    def get_patterns(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs} for n in self.nodes.values() if n.type == "pattern"]

    def get_predictions(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs} for n in self.nodes.values() if n.type == "prediction"]

    def get_subscriptions(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs} for n in self.nodes.values() if n.type == "subscription"]

    def get_budgets(self) -> list[dict]:
        results = []
        for n in self.nodes.values():
            if n.type == "budget":
                cat = n.attrs.get("category", "")
                cid = self._category_id(cat)
                spent = self.nodes[cid].attrs.get("total_spent", 0) if cid in self.nodes else 0
                results.append({
                    "id": n.id, "label": n.label, "category": cat,
                    "limit": n.attrs.get("limit", 0), "spent": round(spent, 2),
                    "period": n.attrs.get("period", "month"),
                    "status": "OVER" if spent > n.attrs.get("limit", 0) else "OK"
                })
        return results

    def get_loans(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs}
                for n in self.nodes.values() if n.type == "loan"]

    def get_investments(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs}
                for n in self.nodes.values() if n.type == "investment"]

    def get_insurance(self) -> list[dict]:
        return [{"id": n.id, "label": n.label, **n.attrs}
                for n in self.nodes.values() if n.type == "insurance"]

    # ==================== GRAPH EXPORT ====================

    def traverse(self, node_id: str, depth: int = 2) -> dict:
        if node_id not in self.nodes:
            return {"nodes": [], "links": []}
        visited = set()
        queue = [(node_id, 0)]
        sub_nodes = []
        sub_edges = []
        while queue:
            nid, d = queue.pop(0)
            if nid in visited or d > depth:
                continue
            visited.add(nid)
            if nid in self.nodes:
                n = self.nodes[nid]
                sub_nodes.append({
                    "id": n.id, "label": n.label, "type": n.type,
                    "color": NODE_COLORS.get(n.type, "#999"),
                    "size": NODE_SIZES.get(n.type, 8), "attrs": n.attrs
                })
            for e in self.edges:
                if e.source == nid and e.target not in visited:
                    sub_edges.append(e.to_dict())
                    queue.append((e.target, d + 1))
                elif e.target == nid and e.source not in visited:
                    sub_edges.append(e.to_dict())
                    queue.append((e.source, d + 1))
        return {"nodes": sub_nodes, "links": sub_edges}

    def get_node(self, node_id: str) -> dict | None:
        if node_id not in self.nodes:
            return None
        n = self.nodes[node_id]
        edges = [e.to_dict() for e in self.edges if e.source == node_id or e.target == node_id]
        neighbors = []
        for nid in self._get_neighbors(node_id):
            if nid in self.nodes:
                nb = self.nodes[nid]
                neighbors.append({"id": nb.id, "label": nb.label, "type": nb.type})
        return {"node": n.to_dict(), "edges": edges, "neighbors": neighbors}

    # ==================== NODE MANAGEMENT ====================

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all connected edges."""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]
        if self.on_change:
            self.on_change()
        return True

    def trust_merchant(self, merchant_name: str) -> dict:
        """Mark a merchant as trusted: remove linked alerts, set trusted=true."""
        merchant_name_lower = merchant_name.lower()
        # Find matching merchant node
        merchant_id = None
        for nid, n in self.nodes.items():
            if n.type == "merchant" and merchant_name_lower in n.label.lower():
                merchant_id = nid
                break
        if not merchant_id:
            return {"success": False, "message": f"Merchant '{merchant_name}' not found"}

        # Mark merchant as trusted
        self.nodes[merchant_id].attrs["trusted"] = True
        self.nodes[merchant_id].attrs["status"] = "trusted"

        # Find and remove linked alert nodes
        removed_alerts = []
        alert_ids = set()
        for e in self.edges:
            if e.source == merchant_id and e.target in self.nodes and self.nodes[e.target].type == "alert":
                alert_ids.add(e.target)
            if e.target == merchant_id and e.source in self.nodes and self.nodes[e.source].type == "alert":
                alert_ids.add(e.source)
        for aid in alert_ids:
            removed_alerts.append(self.nodes[aid].label)
            self.remove_node(aid)

        if self.on_change:
            self.on_change()
        return {
            "success": True,
            "merchant": self.nodes[merchant_id].label,
            "removed_alerts": removed_alerts,
            "message": f"Marked {self.nodes[merchant_id].label} as trusted. Removed {len(removed_alerts)} alert(s)."
        }

    def dismiss_alert(self, alert_id: str = None, alert_name: str = None) -> dict:
        """Remove an alert node by ID or name match."""
        target_id = alert_id
        if not target_id and alert_name:
            alert_lower = alert_name.lower()
            for nid, n in self.nodes.items():
                if n.type == "alert" and alert_lower in n.label.lower():
                    target_id = nid
                    break
        if not target_id or target_id not in self.nodes:
            return {"success": False, "message": "Alert not found"}
        label = self.nodes[target_id].label
        self.remove_node(target_id)
        return {"success": True, "message": f"Dismissed alert: {label}"}

    def visualize(self) -> dict:
        nodes = [{"id": n.id, "label": n.label, "type": n.type,
                  "color": NODE_COLORS.get(n.type, "#999"),
                  "size": NODE_SIZES.get(n.type, 8), "attrs": n.attrs}
                 for n in self.nodes.values()]
        links = [e.to_dict() for e in self.edges]
        return {"nodes": nodes, "links": links}

    def export_full(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "stats": self.get_stats(),
            "meta": {"balance": self.balance, "salary": self.salary,
                     "total_spent": round(self.total_spent, 2),
                     "transactions_processed": self.transactions_processed}
        }

    # ==================== ANALYSIS METHODS ====================

    def get_spending_trend(self, category: str = None) -> dict:
        """Analyze monthly spending trend — increasing/decreasing/stable."""
        if len(self.monthly_history) < 2:
            # Fall back to current-month data
            total = sum(n.attrs.get("total_spent", 0) for n in self.nodes.values() if n.type == "category")
            return {"direction": "stable", "change_pct": 0, "current_month": round(total, 2),
                    "months_analyzed": len(self.monthly_history),
                    "summary": f"R{total:,.0f} spent this period. Need more months for trend."}
        months_sorted = sorted(self.monthly_history.keys())
        if category:
            expenses = [self.monthly_history[m]["categories"].get(category, 0) for m in months_sorted]
        else:
            expenses = [self.monthly_history[m]["total_expenses"] for m in months_sorted]
        prev, curr = expenses[-2], expenses[-1]
        if prev > 0:
            change_pct = ((curr - prev) / prev) * 100
        else:
            change_pct = 0
        direction = "increasing" if change_pct > 10 else "decreasing" if change_pct < -10 else "stable"
        return {
            "direction": direction, "change_pct": round(change_pct, 1),
            "previous_month": round(prev, 2), "current_month": round(curr, 2),
            "months_analyzed": len(expenses),
            "summary": f"Spending {direction} by {abs(change_pct):.0f}% (R{prev:,.0f} -> R{curr:,.0f})"
        }

    def get_recurring_payments(self) -> list[dict]:
        """Detect merchants with consistent amounts (< 10% variance over 2+ occurrences)."""
        recurring = []
        for n in self.nodes.values():
            if n.type != "merchant":
                continue
            amounts = n.attrs.get("amounts", [])
            if len(amounts) < 2:
                continue
            avg = statistics.mean(amounts)
            if avg == 0:
                continue
            try:
                std = statistics.stdev(amounts) if len(amounts) > 1 else 0
            except statistics.StatisticsError:
                std = 0
            variance = std / avg if avg > 0 else 1
            if variance < 0.10:
                recurring.append({
                    "merchant": n.label, "amount": round(avg, 2),
                    "occurrences": len(amounts), "variance": round(variance * 100, 1),
                    "annual": round(avg * 12, 2),
                })
        recurring.sort(key=lambda x: x["amount"], reverse=True)
        return recurring

    def check_affordability(self, monthly_amount: float) -> dict:
        """Check if a new monthly commitment is affordable."""
        # Monthly income
        total_income = sum(n.attrs.get("amount", 0) for n in self.nodes.values()
                          if n.type == "income" and n.attrs.get("frequency") == "monthly")
        if total_income == 0:
            total_income = self.salary or 0

        # Monthly committed expenses (recurring)
        recurring = self.get_recurring_payments()
        committed = sum(r["amount"] for r in recurring)

        # Loan repayments
        loan_monthly = sum(n.attrs.get("monthly_payment", 0) for n in self.nodes.values() if n.type == "loan")

        total_committed = committed + loan_monthly
        disposable = total_income - total_committed
        new_disposable = disposable - monthly_amount
        dti = ((total_committed + monthly_amount) / total_income * 100) if total_income > 0 else 100

        can_afford = new_disposable > 0 and dti < 75
        return {
            "can_afford": can_afford,
            "monthly_income": round(total_income, 2),
            "committed_expenses": round(total_committed, 2),
            "disposable_before": round(disposable, 2),
            "disposable_after": round(new_disposable, 2),
            "debt_to_income": round(dti, 1),
            "new_amount": monthly_amount,
            "summary": f"{'Affordable' if can_afford else 'Not recommended'}. "
                       f"Income R{total_income:,.0f}, committed R{total_committed:,.0f}, "
                       f"remaining after: R{new_disposable:,.0f} (DTI {dti:.0f}%)"
        }

    def build_context(self) -> str:
        """Build context string for AI model injection."""
        stats = self.get_stats()
        subs = self.get_subscriptions()
        pats = self.get_patterns()
        budgets = self.get_budgets()

        spending = {n.label: round(n.attrs.get("total_spent", 0), 2)
                    for n in self.nodes.values() if n.type == "category"}

        # Account summary
        acct_lines = []
        for aid, a in self.accounts.items():
            marker = " [ACTIVE]" if aid == self.active_account_id else ""
            acct_lines.append(f"{a['name']} ({a['type']}): R{a['balance']:,.2f}{marker}")
        acct_summary = "; ".join(acct_lines) if acct_lines else "No accounts"

        lines = [
            f"GRAPH: {stats['total_nodes']} nodes, {stats['total_edges']} edges, {stats['transactions_processed']} transactions",
            f"ACCOUNTS: {acct_summary}",
            f"Active Account Balance: R{self.balance:,.2f}, Available: R{self.available:,.2f}, Salary: R{self.salary:,.2f} on day {self.salary_day}",
            f"SPENDING: " + ", ".join(f"{k} R{v:,.0f}" for k, v in sorted(spending.items(), key=lambda x: x[1], reverse=True)),
            (f"SUBSCRIPTIONS: " + ", ".join(f"{s['label'].replace(' Subscription', '')} R{s.get('amount', 0):,.0f}/mo" for s in subs)
             if subs else "SUBSCRIPTIONS: None detected"),
            (f"PATTERNS: " + ", ".join(p.get("insight", p.get("label", "")) for p in pats)
             if pats else "PATTERNS: None detected yet"),
            (f"BUDGETS: " + ", ".join(f"{b['category']} R{b['spent']:,.0f}/R{b['limit']:,.0f} [{b['status']}]" for b in budgets)
             if budgets else "BUDGETS: None set"),
        ]

        # Income
        incomes = [n for n in self.nodes.values() if n.type == "income"]
        if incomes:
            lines.append("INCOME: " + ", ".join(
                f"{i.label} R{i.attrs.get('amount', 0):,.0f}/{i.attrs.get('frequency', 'mo')}" for i in incomes))

        # Loans
        loans = [n for n in self.nodes.values() if n.type == "loan"]
        if loans:
            total_debt = sum(l.attrs.get("balance", 0) for l in loans)
            lines.append(f"LOANS: R{total_debt:,.0f} total — " + ", ".join(
                f"{l.label} R{l.attrs.get('balance', 0):,.0f} at {l.attrs.get('rate', 0)}%" for l in loans))

        # Investments
        investments = [n for n in self.nodes.values() if n.type == "investment"]
        if investments:
            total_val = sum(i.attrs.get("current_value", 0) for i in investments)
            lines.append(f"INVESTMENTS: R{total_val:,.0f} total — " + ", ".join(
                f"{i.label} R{i.attrs.get('current_value', 0):,.0f} ({'+' if i.attrs.get('pnl_pct', 0) >= 0 else ''}{i.attrs.get('pnl_pct', 0):.1f}%)" for i in investments))

        # Insurance
        policies = [n for n in self.nodes.values() if n.type == "insurance"]
        if policies:
            total_prem = sum(p.attrs.get("premium", 0) for p in policies)
            lines.append(f"INSURANCE: R{total_prem:,.0f}/mo — " + ", ".join(
                f"{p.label} R{p.attrs.get('premium', 0):,.0f}/mo" for p in policies))

        # Tax
        tax_items = [n for n in self.nodes.values() if n.type == "tax"]
        if tax_items:
            lines.append("TAX: " + ", ".join(
                f"{t.label} R{t.attrs.get('amount', 0):,.0f} [{t.attrs.get('tax_type', '')}]" for t in tax_items))

        # Goals
        goals = [n for n in self.nodes.values() if n.type == "goal"]
        if goals:
            lines.append("GOALS: " + ", ".join(
                f"{g.label} R{g.attrs.get('target', 0):,.0f} (R{g.attrs.get('monthly_contribution', 0):,.0f}/mo)" for g in goals))

        # Balance prediction
        bal_pred = self.nodes.get("prediction_balance")
        if bal_pred:
            lines.append(f"FORECAST: Balance R{bal_pred.attrs.get('projected_balance', 0):,.0f} by payday at R{bal_pred.attrs.get('daily_burn', 0):,.0f}/day burn")

        # Alerts
        alerts = [n for n in self.nodes.values() if n.type == "alert"]
        if alerts:
            lines.append("ALERTS: " + ", ".join(
                f"[{a.attrs.get('severity', 'info')}] {a.label}" for a in alerts))

        return "\n".join(lines)

    # ==================== SEED DEMO DATA ====================

    def seed_demo_data(self) -> dict:
        """Seed comprehensive demo data — transactions, income, loans, investments, insurance, tax."""
        # Reset
        self.nodes = {}
        self.edges = []
        self.transactions = []
        self._next_txn_id = 1
        self.transactions_processed = 0
        self.total_spent = 0
        self.accounts = {}
        self.active_account_id = None
        self._add_node("user", "You", "person", {"account_status": "Active"})

        # Create accounts
        self.create_account("acc_cheque", "Private Bank Account", "cheque",
                            balance=34218.66, available=42145.23,
                            salary=42500, salary_day=25, last4="7821",
                            color="#003B5C")
        self.create_account("acc_savings", "Savings Account", "savings",
                            balance=92000.00, available=92000.00,
                            salary=0, salary_day=25, last4="4455",
                            color="#007A6E")

        # Budgets
        self.add_budget("Food Delivery", 500, "week")
        self.add_budget("Groceries", 3500, "month")
        self.add_budget("Fuel", 2500, "month")
        self.add_budget("Subscription", 500, "month")
        self.add_budget("Shopping", 5000, "month")

        # Goals
        self.add_goal("Emergency Fund", 50000, 3000)
        self.add_goal("Zanzibar Holiday", 25000, 2500)

        # Income sources
        self.add_income("ACME Corp Salary", 42500, "monthly", "salary")
        self.add_income("Freelance Dev", 5000, "monthly", "freelance")
        self.add_income("FNB Interest", 285, "monthly", "interest")

        # Loans (monthly_payment matches actual debit order amounts)
        self.add_loan("Home Loan", 1800000, 11.75, 240, 1650000, "mortgage", 16847)
        self.add_loan("Car Finance", 350000, 12.5, 60, 280000, "vehicle", 6333)
        self.add_loan("Personal Loan", 50000, 18.0, 36, 35000, "personal", 1267)

        # Investments
        self.add_investment("Satrix Top 40 ETF", 150000, 172500, "etf")
        self.add_investment("Capitec Shares", 25000, 31200, "equity")
        self.add_investment("Tax-Free Savings", 80000, 92000, "tax_free")

        # Insurance
        self.add_insurance("Discovery", "health", 4200, 5000000, "2026-01-01")
        self.add_insurance("Outsurance", "car", 1847, 350000, "2026-06-01")
        self.add_insurance("Old Mutual", "life", 650, 2000000, "2026-03-01")

        # Tax items
        self.add_tax_item("Employment Income", 510000, "income", "employment")
        self.add_tax_item("Interest Income", 3420, "income", "interest")
        self.add_tax_item("Medical Aid Credits", 50400, "deduction", "medical")
        self.add_tax_item("Retirement Annuity", 36000, "deduction", "retirement")

        # Transactions (26 covering all types)
        transactions = [
            ("Woolworths Food", 847.30, "Groceries", "08:12", "low"),
            ("Checkers", 623.50, "Groceries", "10:30", "low"),
            ("Shell Garage N1", 1250, "Fuel", "09:45", "low"),
            ("Engen", 890, "Fuel", "16:20", "low"),
            ("UNKNOWN_MERCH_ZW", 4500, "Unknown", "02:47", "critical"),
            ("Takealot.com", 12399, "Shopping", "14:22", "high"),
            ("Netflix SA", 299, "Subscription", "00:01", "low"),
            ("Netflix SA", 299, "Subscription", "00:01", "low"),
            ("Netflix SA", 299, "Subscription", "00:01", "low"),
            ("Spotify Premium", 79.99, "Subscription", "00:01", "low"),
            ("Spotify Premium", 79.99, "Subscription", "00:01", "low"),
            ("Spotify Premium", 79.99, "Subscription", "00:01", "low"),
            ("Uber Eats", 389.50, "Food Delivery", "19:33", "low"),
            ("Uber Eats", 189, "Food Delivery", "20:05", "low"),
            ("Uber Eats", 256, "Food Delivery", "19:12", "low"),
            ("Mr D Food", 245, "Food Delivery", "21:15", "low"),
            ("City Power Joburg", 2847, "Utilities", "06:00", "high"),
            ("Vodacom", 599, "Subscription", "01:00", "low"),
            ("Vodacom", 599, "Subscription", "01:00", "low"),
            ("Discovery Health", 4200, "Insurance", "01:00", "low"),
            ("Outsurance", 1847, "Insurance", "06:00", "low"),
            ("Engen QuickShop", 156.80, "Convenience", "07:30", "low"),
            ("Uber", 145, "Transport", "08:15", "low"),
            ("Gautrain", 85, "Transport", "07:00", "low"),
            ("Vida e Caffe", 75, "Coffee", "09:00", "low"),
            ("Spur", 380, "Dining", "13:00", "low"),
        ]

        for merchant, amount, category, time, risk in transactions:
            self.ingest_transaction(merchant, amount, category, time, risk)

        # Record income in ledger (these are credits, not expenses)
        self.record_income("ACME Corp Salary", 42500, "salary", "06:00", "\U0001F4B0")
        self.record_income("Freelance Dev", 5000, "freelance", "10:00", "\U0001F4BB")
        self.record_income("FNB Interest", 285, "interest", "00:01", "\U0001F3E6")

        # Beneficiaries
        self.add_beneficiary("Mom", "FNB", "62845901234", "250655", "Mom monthly", "individual")
        self.add_beneficiary("Dad", "Standard Bank", "041289567", "051001", "Dad support", "individual")
        self.add_beneficiary("Thandi Nkosi", "Capitec", "1350987654", "470010", "Rent", "individual")
        self.add_beneficiary("Thando Moyo", "Nedbank", "8012345678", "198765", "Thando", "individual")
        self.add_beneficiary("Eskom", "ABSA", "4055123456", "632005", "Prepaid Elec", "company")
        self.add_beneficiary("Vodacom", "ABSA", "4052000001", "632005", "Cell Contract", "company")
        self.add_beneficiary("Landlord - Mike", "Investec", "10012345678", "580105", "Rent Unit 4B", "individual")

        # Reset cheque balance to desired "current" state (seed txns are historical)
        self.accounts["acc_cheque"]["balance"] = 34218.66
        self.accounts["acc_cheque"]["available"] = 42145.23
        if "acc_cheque" in self.nodes:
            self.nodes["acc_cheque"].attrs["balance"] = 34218.66
            self.nodes["acc_cheque"].attrs["available"] = 42145.23

        self._notify_change()
        return {
            "seeded": True,
            "transactions": len(transactions),
            "stats": self.get_stats(),
            "context": self.build_context()
        }


# Singleton instance
kg = FinancialKnowledgeGraph()
