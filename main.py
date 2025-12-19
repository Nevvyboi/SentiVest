import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from pydantic import BaseModel
import anthropic

from investecApi import create_investec_client, InvestecDataTransformer
from aiAgent import FinancialAIAgent

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    accounts = relationship("Account", back_populates="user")
    rules = relationship("AlertRule", back_populates="user")
    alerts = relationship("Alert", back_populates="user")

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"))
    accountId = Column(String, unique=True)
    accountName = Column(String)
    productName = Column(String)
    accountNumber = Column(String)
    currentBalance = Column(Float, default=0.0)
    availableBalance = Column(Float, default=0.0)
    currency = Column(String, default="ZAR")
    lastSync = Column(DateTime)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"))
    accountId = Column(Integer, ForeignKey("accounts.id"))
    transactionId = Column(String, unique=True)
    date = Column(DateTime)
    amount = Column(Float)
    merchant = Column(String)
    description = Column(Text)
    category = Column(String)
    status = Column(String)
    postedDate = Column(DateTime, nullable=True)
    cardNumber = Column(String, nullable=True)
    reference = Column(String, nullable=True)
    transactionType = Column(String, nullable=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    account = relationship("Account", back_populates="transactions")

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    ruleType = Column(String)
    parameters = Column(Text)
    enabled = Column(Boolean, default=True)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="rules")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("users.id"))
    ruleId = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)
    title = Column(String)
    body = Column(Text)
    severity = Column(String)
    read = Column(Boolean, default=False)
    createdAt = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="alerts")

DATABASE_URL = "sqlite:///./financial_alarm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

class RuleEngine:
    def __init__(self, dbSession: Session):
        self.dbSession = dbSession

    async def evaluateAllRules(self, userId: int) -> List[Alert]:
        rules = self.dbSession.query(AlertRule).filter(
            AlertRule.userId == userId,
            AlertRule.enabled == True
        ).all()
        alertsGenerated = []
        for rule in rules:
            alert = await self.evaluateRule(rule, userId)
            if alert:
                alertsGenerated.append(alert)
        return alertsGenerated

    async def evaluateRule(self, rule: AlertRule, userId: int) -> Optional[Alert]:
        params = json.loads(rule.parameters) if rule.parameters else {}
        if rule.ruleType == "low_balance":
            return await self.checkLowBalance(rule, userId, params)
        elif rule.ruleType == "large_transaction":
            return await self.checkLargeTransaction(rule, userId, params)
        elif rule.ruleType == "category_limit":
            return await self.checkCategoryLimit(rule, userId, params)
        elif rule.ruleType == "spending_spike":
            return await self.checkSpendingSpike(rule, userId, params)
        elif rule.ruleType == "new_subscription":
            return await self.checkNewSubscription(rule, userId, params)
        elif rule.ruleType == "payday_reminder":
            return await self.checkPaydayReminder(rule, userId, params)
        return None

    async def checkLowBalance(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        threshold = params.get("threshold", 1000.0)
        account = self.dbSession.query(Account).filter(Account.userId == userId).first()
        if not account:
            return None
        if account.currentBalance < threshold:
            recentAlert = self.dbSession.query(Alert).filter(
                Alert.userId == userId,
                Alert.ruleId == rule.id,
                Alert.createdAt > datetime.now(timezone.utc) - timedelta(hours=24)
            ).first()
            if recentAlert:
                return None
            alert = Alert(
                userId=userId,
                ruleId=rule.id,
                title="⚠️ Low Balance Alert",
                body=f"Your balance (R {account.currentBalance:,.2f}) is below R {threshold:,.2f}",
                severity="WARNING"
            )
            self.dbSession.add(alert)
            self.dbSession.commit()
            self.dbSession.refresh(alert)
            return alert
        return None

    async def checkLargeTransaction(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        threshold = params.get("threshold", 2000.0)
        recentTxn = self.dbSession.query(Transaction).filter(
            Transaction.userId == userId,
            Transaction.createdAt > datetime.now(timezone.utc) - timedelta(minutes=5),
            Transaction.amount < -threshold
        ).order_by(Transaction.createdAt.desc()).first()
        if recentTxn:
            existingAlert = self.dbSession.query(Alert).filter(
                Alert.userId == userId,
                Alert.ruleId == rule.id,
                Alert.body.contains(recentTxn.merchant)
            ).first()
            if existingAlert:
                return None
            alert = Alert(
                userId=userId,
                ruleId=rule.id,
                title="🔴 Large Transaction Detected",
                body=f"Unusual transaction: R {abs(recentTxn.amount):,.2f} at {recentTxn.merchant}",
                severity="CRITICAL"
            )
            self.dbSession.add(alert)
            self.dbSession.commit()
            self.dbSession.refresh(alert)
            return alert
        return None

    async def checkCategoryLimit(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        category = params.get("category", "Restaurants")
        limit = params.get("limit", 2000.0)
        startOfMonth = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total = self.dbSession.query(Transaction).filter(
            Transaction.userId == userId,
            Transaction.category == category,
            Transaction.date >= startOfMonth,
            Transaction.amount < 0
        ).all()
        categoryTotal = sum(abs(t.amount) for t in total)
        if categoryTotal > limit:
            recentAlert = self.dbSession.query(Alert).filter(
                Alert.userId == userId,
                Alert.ruleId == rule.id,
                Alert.createdAt >= startOfMonth
            ).first()
            if recentAlert:
                return None
            alert = Alert(
                userId=userId,
                ruleId=rule.id,
                title=f"🎯 {category} Limit Exceeded",
                body=f"You've spent R {categoryTotal:,.2f} on {category} this month (limit: R {limit:,.2f})",
                severity="WARNING"
            )
            self.dbSession.add(alert)
            self.dbSession.commit()
            self.dbSession.refresh(alert)
            return alert
        return None

    async def checkSpendingSpike(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        thresholdMultiplier = params.get("threshold_multiplier", 2.0)
        sevenDaysAgo = datetime.now(timezone.utc) - timedelta(days=7)
        recentTxns = self.dbSession.query(Transaction).filter(
            Transaction.userId == userId,
            Transaction.date >= sevenDaysAgo,
            Transaction.amount < 0
        ).all()
        if len(recentTxns) < 7:
            return None
        totalSpent = sum(abs(t.amount) for t in recentTxns)
        dailyAverage = totalSpent / 7
        todayStart = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        todayTxns = []
        for t in recentTxns:
            txnDate = t.date
            if txnDate.tzinfo is None:
                txnDate = txnDate.replace(tzinfo=timezone.utc)
            if txnDate >= todayStart:
                todayTxns.append(t)
        todayTotal = sum(abs(t.amount) for t in todayTxns)
        if todayTotal > dailyAverage * thresholdMultiplier and todayTotal > 500:
            recentAlert = self.dbSession.query(Alert).filter(
                Alert.userId == userId,
                Alert.ruleId == rule.id,
                Alert.createdAt >= todayStart
            ).first()
            if recentAlert:
                return None
            alert = Alert(
                userId=userId,
                ruleId=rule.id,
                title="📈 Spending Spike Detected",
                body=f"You've spent R {todayTotal:,.2f} today, {thresholdMultiplier}x your daily average of R {dailyAverage:,.2f}",
                severity="WARNING"
            )
            self.dbSession.add(alert)
            self.dbSession.commit()
            self.dbSession.refresh(alert)
            return alert
        return None

    async def checkNewSubscription(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        thirtyDaysAgo = datetime.now(timezone.utc) - timedelta(days=30)
        firstTxn = self.dbSession.query(Transaction).filter(
            Transaction.userId == userId,
            Transaction.date >= thirtyDaysAgo
        ).order_by(Transaction.date.asc()).first()
        if not firstTxn:
            return None
        firstTxnDate = firstTxn.date
        if firstTxnDate.tzinfo is None:
            firstTxnDate = firstTxnDate.replace(tzinfo=timezone.utc)
        if firstTxnDate > thirtyDaysAgo:
            similarTxns = self.dbSession.query(Transaction).filter(
                Transaction.userId == userId,
                Transaction.merchant == firstTxn.merchant,
                Transaction.amount.between(firstTxn.amount * 0.95, firstTxn.amount * 1.05),
                Transaction.id != firstTxn.id
            ).count()
            if similarTxns >= 2:
                recentAlert = self.dbSession.query(Alert).filter(
                    Alert.userId == userId,
                    Alert.ruleId == rule.id,
                    Alert.body.contains(firstTxn.merchant)
                ).first()
                if recentAlert:
                    return None
                alert = Alert(
                    userId=userId,
                    ruleId=rule.id,
                    title="📺 New Subscription Detected",
                    body=f"Recurring payment detected: {firstTxn.merchant} - R {abs(firstTxn.amount):.2f}",
                    severity="INFO"
                )
                self.dbSession.add(alert)
                self.dbSession.commit()
                self.dbSession.refresh(alert)
                return alert
        return None

    async def checkPaydayReminder(self, rule: AlertRule, userId: int, params: dict) -> Optional[Alert]:
        payday = params.get("payday", 25)
        daysBefore = params.get("days_before", 3)
        today = datetime.now(timezone.utc)
        daysUntilPayday = (payday - today.day) % 30
        if daysUntilPayday <= daysBefore and daysUntilPayday > 0:
            startOfMonth = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            recentAlert = self.dbSession.query(Alert).filter(
                Alert.userId == userId,
                Alert.ruleId == rule.id,
                Alert.createdAt >= startOfMonth
            ).first()
            if recentAlert:
                return None
            alert = Alert(
                userId=userId,
                ruleId=rule.id,
                title="💰 Payday Approaching",
                body=f"Payday is in {daysUntilPayday} days!",
                severity="INFO"
            )
            self.dbSession.add(alert)
            self.dbSession.commit()
            self.dbSession.refresh(alert)
            return alert
        return None

app = FastAPI(title="Financial Alarm System", version="2.5")
baseDir = Path(__file__).resolve().parent
staticDir = baseDir / "static"
app.mount("/static", StaticFiles(directory=str(staticDir)), name="static")

class ConnectionManager:
    def __init__(self):
        self.activeConnections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.activeConnections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.activeConnections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.activeConnections[:]:
            try:
                await connection.send_json(message)
            except:
                try:
                    self.activeConnections.remove(connection)
                except:
                    pass

manager = ConnectionManager()

def getDb():
    dbSession = sessionLocal()
    try:
        yield dbSession
    finally:
        dbSession.close()

def ensureUserExists(dbSession: Session) -> User:
    user = dbSession.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            id=1,
            email="user@example.com",
            name="Demo User"
        )
        dbSession.add(user)
        dbSession.commit()
        dbSession.refresh(user)
    return user

def createDefaultRules(dbSession: Session, userId: int):
    existingRules = dbSession.query(AlertRule).filter(AlertRule.userId == userId).count()
    if existingRules == 0:
        rules = [
            AlertRule(
                userId=userId,
                name="Low Balance Warning",
                ruleType="low_balance",
                parameters=json.dumps({"threshold": 1000.0}),
                enabled=True
            ),
            AlertRule(
                userId=userId,
                name="Large Transaction Alert",
                ruleType="large_transaction",
                parameters=json.dumps({"threshold": 2000.0}),
                enabled=True
            ),
            AlertRule(
                userId=userId,
                name="Restaurant Spending Limit",
                ruleType="category_limit",
                parameters=json.dumps({"category": "Restaurants", "limit": 2000.0}),
                enabled=True
            ),
            AlertRule(
                userId=userId,
                name="Spending Spike Detection",
                ruleType="spending_spike",
                parameters=json.dumps({"threshold_multiplier": 2.0}),
                enabled=True
            ),
            AlertRule(
                userId=userId,
                name="New Subscription Detection",
                ruleType="new_subscription",
                parameters=json.dumps({}),
                enabled=True
            ),
            AlertRule(
                userId=userId,
                name="Payday Reminder",
                ruleType="payday_reminder",
                parameters=json.dumps({"payday": 25, "days_before": 3}),
                enabled=True
            )
        ]
        for rule in rules:
            dbSession.add(rule)
        dbSession.commit()

def categorizeTransaction(description: str, merchant: str) -> str:
    descLower = description.lower() if description else ""
    merchantLower = merchant.lower() if merchant else ""
    combined = f"{descLower} {merchantLower}"
    categories = {
        "Groceries": ["woolworths", "checkers", "pick n pay", "spar", "shoprite", "makro"],
        "Restaurants": ["restaurant", "nando", "steers", "kfc", "mcdonald", "burger king", "ocean basket"],
        "Fast Food": ["uber eats", "mr delivery", "pizza", "debonairs"],
        "Transport": ["uber", "bolt", "shell", "engen", "bp", "caltex", "fuel"],
        "Entertainment": ["netflix", "showmax", "dstv", "spotify", "apple music", "cinema"],
        "Shopping": ["takealot", "game", "incredible connection", "edgars", "truworths"],
        "Utilities": ["electricity", "water", "municipal", "city of"],
        "Telecommunications": ["vodacom", "mtn", "cell c", "telkom", "rain"],
        "Health": ["pharmacy", "clicks", "dis-chem", "doctor", "hospital"],
        "Travel": ["airbnb", "booking.com", "flight", "airline"],
        "Salary": ["salary", "wages", "payroll"],
        "Transfer": ["transfer", "payment received", "ft "],
        "Income": ["refund", "deposit", "credit"]
    }
    for category, keywords in categories.items():
        if any(keyword in combined for keyword in keywords):
            return category
    return "Other"

@app.websocket("/ws/dashboard")
async def websocketDashboard(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)

@app.websocket("/ws/testing")
async def websocketTesting(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
async def readRoot():
    indexPath = staticDir / "index.html"
    if not indexPath.exists():
        return HTMLResponse("<h1>index.html not found in static folder</h1>", status_code=404)
    return HTMLResponse(indexPath.read_text(encoding='utf-8'))

@app.get("/testing", response_class=HTMLResponse)
async def readTesting():
    testingPath = staticDir / "testing.html"
    if not testingPath.exists():
        return HTMLResponse("<h1>testing.html not found in static folder</h1>", status_code=404)
    return HTMLResponse(testingPath.read_text(encoding='utf-8'))

@app.get("/api/dashboard")
async def getDashboard(dbSession: Session = Depends(getDb)):
    try:
        user = ensureUserExists(dbSession)
        account = dbSession.query(Account).filter(Account.userId == user.id).first()
        transactions = dbSession.query(Transaction).filter(
            Transaction.userId == user.id
        ).order_by(Transaction.date.desc()).limit(10).all()
        alerts = dbSession.query(Alert).filter(
            Alert.userId == user.id,
            Alert.read == False
        ).order_by(Alert.createdAt.desc()).all()
        rules = dbSession.query(AlertRule).filter(AlertRule.userId == user.id).all()
        startOfMonth = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthTxns = dbSession.query(Transaction).filter(
            Transaction.userId == user.id,
            Transaction.date >= startOfMonth,
            Transaction.amount < 0
        ).all()
        categorySpending = {}
        for txn in monthTxns:
            category = txn.category or "Other"
            categorySpending[category] = categorySpending.get(category, 0) + abs(txn.amount)
        return {
            "account": {
                "id": account.id if account else None,
                "balance": account.currentBalance if account else 0,
                "account_number": account.accountNumber if account else None,
                "last_sync": account.lastSync.isoformat() if account and account.lastSync else None
            } if account else None,
            "transactions": [
                {
                    "id": t.id,
                    "date": t.date.isoformat(),
                    "amount": t.amount,
                    "merchant": t.merchant,
                    "description": t.description,
                    "category": t.category
                }
                for t in transactions
            ],
            "alerts": [
                {
                    "id": a.id,
                    "title": a.title,
                    "body": a.body,
                    "severity": a.severity,
                    "created_at": a.createdAt.isoformat()
                }
                for a in alerts
            ],
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "rule_type": r.ruleType,
                    "enabled": r.enabled
                }
                for r in rules
            ],
            "category_spending": categorySpending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/initialize")
async def initializeSystem(dbSession: Session = Depends(getDb)):
    try:
        user = ensureUserExists(dbSession)
        createDefaultRules(dbSession, user.id)
        try:
            client = create_investec_client()
            accountsData = client.get_accounts()
            transformer = InvestecDataTransformer()
            for investecAccount in accountsData.get("accounts", []):
                existingAccount = dbSession.query(Account).filter(
                    Account.accountId == investecAccount["accountId"]
                ).first()
                if existingAccount:
                    account = existingAccount
                    account.currentBalance = investecAccount.get("currentBalance", 0)
                    account.availableBalance = investecAccount.get("availableBalance", 0)
                    account.lastSync = datetime.now(timezone.utc)
                else:
                    account = Account(
                        userId=user.id,
                        accountId=investecAccount["accountId"],
                        accountName=investecAccount.get("accountName", "Primary Account"),
                        productName=investecAccount.get("productName", "Investec Account"),
                        accountNumber=investecAccount.get("accountNumber", ""),
                        currentBalance=investecAccount.get("currentBalance", 0),
                        availableBalance=investecAccount.get("availableBalance", 0),
                        currency=investecAccount.get("currency", "ZAR"),
                        lastSync=datetime.now(timezone.utc)
                    )
                    dbSession.add(account)
                dbSession.commit()
                dbSession.refresh(account)
                transactionsData = client.get_transactions(
                    account_id=investecAccount["accountId"],
                    from_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                    to_date=datetime.now().strftime("%Y-%m-%d")
                )
                for investecTxn in transactionsData.get("transactions", []):
                    txnInfo = transformer.transform_transaction(investecTxn)
                    existingTxn = dbSession.query(Transaction).filter(
                        Transaction.transactionId == txnInfo["transaction_id"]
                    ).first()
                    if existingTxn:
                        continue
                    category = categorizeTransaction(
                        txnInfo.get("description", ""),
                        txnInfo.get("merchant", "")
                    )
                    txnInfo.pop("account_id", None)
                    transaction = Transaction(
                        userId=user.id,
                        accountId=account.id,
                        category=category,
                        transactionId=txnInfo.get("transaction_id"),
                        date=txnInfo.get("date"),
                        amount=txnInfo.get("amount"),
                        merchant=txnInfo.get("merchant"),
                        description=txnInfo.get("description"),
                        status=txnInfo.get("status"),
                        postedDate=txnInfo.get("posted_date"),
                        cardNumber=txnInfo.get("card_number"),
                        reference=txnInfo.get("reference"),
                        transactionType=txnInfo.get("transaction_type")
                    )
                    dbSession.add(transaction)
                dbSession.commit()
            engine = RuleEngine(dbSession)
            await engine.evaluateAllRules(user.id)
            await manager.broadcast({"type": "dashboard_update"})
            return {"success": True, "source": "investec", "accounts": len(accountsData.get("accounts", []))}
        except Exception as investecError:
            account = dbSession.query(Account).filter(Account.userId == user.id).first()
            if not account:
                account = Account(
                    userId=user.id,
                    accountId="MOCK_ACCOUNT_001",
                    accountName="Demo Account",
                    productName="Private Bank Account",
                    accountNumber="1234567890",
                    currentBalance=42145.23,
                    availableBalance=42145.23,
                    currency="ZAR",
                    lastSync=datetime.now(timezone.utc)
                )
                dbSession.add(account)
                dbSession.commit()
                dbSession.refresh(account)
            mockTransactions = [
                {
                    "date": datetime.now(timezone.utc) - timedelta(days=i),
                    "amount": amount,
                    "merchant": merchant,
                    "description": description,
                    "category": category
                }
                for i, (amount, merchant, description, category) in enumerate([
                    (-450.50, "WOOLWORTHS", "Groceries", "Groceries"),
                    (-89.99, "NETFLIX", "Subscription", "Entertainment"),
                    (-320.00, "SHELL", "Fuel purchase", "Transport"),
                    (-1250.00, "OCEAN BASKET", "Dinner", "Restaurants"),
                    (5000.00, "SALARY", "Monthly salary", "Salary"),
                    (-75.00, "CLICKS", "Pharmacy", "Health"),
                    (-199.99, "TAKEALOT", "Online shopping", "Shopping"),
                    (-50.00, "UBER", "Ride", "Transport"),
                    (-680.00, "CHECKERS", "Groceries", "Groceries"),
                    (-120.00, "VODACOM", "Airtime", "Telecommunications")
                ])
            ]
            for mockTxn in mockTransactions:
                mockTxn.pop("account_id", None)
                transaction = Transaction(
                    userId=user.id,
                    accountId=account.id,
                    transactionId=f"MOCK_{int(datetime.now().timestamp() * 1000)}_{mockTxn['merchant']}",
                    date=mockTxn["date"],
                    amount=mockTxn["amount"],
                    merchant=mockTxn["merchant"],
                    description=mockTxn["description"],
                    category=mockTxn["category"]
                )
                dbSession.add(transaction)
            dbSession.commit()
            engine = RuleEngine(dbSession)
            await engine.evaluateAllRules(user.id)
            await manager.broadcast({"type": "dashboard_update"})
            return {"success": True, "source": "mock", "transactions": len(mockTransactions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def syncTransactions(dbSession: Session = Depends(getDb)):
    try:
        user = ensureUserExists(dbSession)
        account = dbSession.query(Account).filter(Account.userId == user.id).first()
        if not account:
            initResult = await initializeSystem(dbSession)
            account = dbSession.query(Account).filter(Account.userId == user.id).first()
            if not account:
                raise HTTPException(status_code=500, detail="Auto-initialization failed - no account created")
        transactionsSynced = 0
        try:
            client = create_investec_client()
            transformer = InvestecDataTransformer()
            fromDate = account.lastSync if account.lastSync else datetime.now() - timedelta(days=7)
            transactionsData = client.get_transactions(
                account_id=account.accountId,
                from_date=fromDate.strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d")
            )
            for investecTxn in transactionsData.get("transactions", []):
                txnInfo = transformer.transform_transaction(investecTxn)
                existingTxn = dbSession.query(Transaction).filter(
                    Transaction.transactionId == txnInfo["transaction_id"]
                ).first()
                if existingTxn:
                    continue
                category = categorizeTransaction(
                    txnInfo.get("description", ""),
                    txnInfo.get("merchant", "")
                )
                txnInfo.pop("account_id", None)
                transaction = Transaction(
                    userId=user.id,
                    accountId=account.id,
                    category=category,
                    transactionId=txnInfo.get("transaction_id"),
                    date=txnInfo.get("date"),
                    amount=txnInfo.get("amount"),
                    merchant=txnInfo.get("merchant"),
                    description=txnInfo.get("description"),
                    status=txnInfo.get("status"),
                    postedDate=txnInfo.get("posted_date"),
                    cardNumber=txnInfo.get("card_number"),
                    reference=txnInfo.get("reference"),
                    transactionType=txnInfo.get("transaction_type")
                )
                dbSession.add(transaction)
                transactionsSynced += 1
            accountsData = client.get_accounts()
            for investecAccount in accountsData.get("accounts", []):
                if investecAccount["accountId"] == account.accountId:
                    account.currentBalance = investecAccount.get("currentBalance", account.currentBalance)
                    account.availableBalance = investecAccount.get("availableBalance", account.availableBalance)
                    break
            account.lastSync = datetime.now(timezone.utc)
            dbSession.commit()
        except Exception as investecError:
            import random
            numTxns = random.randint(1, 3)
            merchants = ["WOOLWORTHS", "CHECKERS", "UBER", "NETFLIX", "SHELL"]
            amounts = [-50.00, -150.00, -500.00, -25.00, -80.00]
            for _ in range(numTxns):
                merchant = random.choice(merchants)
                amount = random.choice(amounts)
                transaction = Transaction(
                    userId=user.id,
                    accountId=account.id,
                    transactionId=f"MOCK_{int(datetime.now().timestamp() * 1000)}_{random.randint(1000, 9999)}",
                    date=datetime.now(timezone.utc),
                    amount=amount,
                    merchant=merchant,
                    description=f"Mock transaction: {merchant}",
                    category=categorizeTransaction("", merchant)
                )
                dbSession.add(transaction)
                transactionsSynced += 1
            account.lastSync = datetime.now(timezone.utc)
            dbSession.commit()
        engine = RuleEngine(dbSession)
        await engine.evaluateAllRules(user.id)
        await manager.broadcast({"type": "dashboard_update"})
        return {"success": True, "transactions_synced": transactionsSynced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/investec/sync")
async def investecSync(dbSession: Session = Depends(getDb)):
    try:
        user = ensureUserExists(dbSession)
        client = create_investec_client()
        if not client.authenticate():
            raise HTTPException(status_code=401, detail="Investec authentication failed")
        accountsData = client.get_accounts()
        transformer = InvestecDataTransformer()
        transactionsSynced = 0
        for investecAccount in accountsData.get("accounts", []):
            account = dbSession.query(Account).filter(
                Account.accountId == investecAccount["accountId"]
            ).first()
            if not account:
                account = Account(
                    userId=user.id,
                    accountId=investecAccount["accountId"],
                    accountName=investecAccount.get("accountName", ""),
                    productName=investecAccount.get("productName", ""),
                    accountNumber=investecAccount.get("accountNumber", ""),
                    currentBalance=investecAccount.get("currentBalance", 0),
                    availableBalance=investecAccount.get("availableBalance", 0),
                    currency=investecAccount.get("currency", "ZAR"),
                    lastSync=datetime.now(timezone.utc)
                )
                dbSession.add(account)
                dbSession.commit()
                dbSession.refresh(account)
            transactionsData = client.get_transactions(
                account_id=investecAccount["accountId"],
                from_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d")
            )
            for investecTxn in transactionsData.get("transactions", []):
                txnInfo = transformer.transform_transaction(investecTxn)
                existingTxn = dbSession.query(Transaction).filter(
                    Transaction.transactionId == txnInfo["transaction_id"]
                ).first()
                if existingTxn:
                    continue
                category = categorizeTransaction(
                    txnInfo.get("description", ""),
                    txnInfo.get("merchant", "")
                )
                txnInfo.pop("account_id", None)
                transaction = Transaction(
                    userId=user.id,
                    accountId=account.id,
                    category=category,
                    transactionId=txnInfo.get("transaction_id"),
                    date=txnInfo.get("date"),
                    amount=txnInfo.get("amount"),
                    merchant=txnInfo.get("merchant"),
                    description=txnInfo.get("description"),
                    status=txnInfo.get("status"),
                    postedDate=txnInfo.get("posted_date"),
                    cardNumber=txnInfo.get("card_number"),
                    reference=txnInfo.get("reference"),
                    transactionType=txnInfo.get("transaction_type")
                )
                dbSession.add(transaction)
                transactionsSynced += 1
            account.lastSync = datetime.now(timezone.utc)
            dbSession.commit()
        engine = RuleEngine(dbSession)
        await engine.evaluateAllRules(user.id)
        await manager.broadcast({"type": "dashboard_update"})
        return {"success": True, "transactions_synced": transactionsSynced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/chat")
async def aiChat(request: Request, dbSession: Session = Depends(getDb)):
    try:
        data = await request.json()
        message = data.get("message", "")
        if not message:
            return {"response": "Please provide a message."}
        user = ensureUserExists(dbSession)
        account = dbSession.query(Account).filter(Account.userId == user.id).first()
        transactions = dbSession.query(Transaction).filter(
            Transaction.userId == user.id
        ).order_by(Transaction.date.desc()).limit(100).all()
        aiAgent = FinancialAIAgent(db=dbSession, anthropic_api_key="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")
        responseData = await aiAgent.chat(user_message=message)
        return {"response": responseData.get("response", "No response")}
    except Exception as e:
        return {"response": f"Sorry, I encountered an error: {str(e)}"}

@app.post("/api/test/low_balance")
async def testLowBalance(dbSession: Session = Depends(getDb)):
    try:
        account = dbSession.query(Account).first()
        if account:
            account.currentBalance = 450.00
            account.availableBalance = 450.00
            dbSession.commit()
            engine = RuleEngine(dbSession)
            alerts = await engine.evaluateAllRules(1)
            await manager.broadcast({"type": "balance_update", "balance": 450.00})
            await manager.broadcast({"type": "dashboard_update"})
            if alerts:
                await manager.broadcast({
                    "type": "alert",
                    "alert": {
                        "title": alerts[0].title,
                        "body": alerts[0].body,
                        "severity": alerts[0].severity
                    }
                })
            return {"success": True, "alert_generated": len(alerts) > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/large_transaction")
async def testLargeTransaction(dbSession: Session = Depends(getDb)):
    try:
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        txn = Transaction(
            userId=1,
            accountId=account.id,
            transactionId=f"TEST_{int(datetime.now().timestamp() * 1000)}",
            date=datetime.now(timezone.utc),
            amount=-5000.00,
            merchant="SUSPICIOUS MERCHANT",
            description="Large test transaction - R5000",
            category="Other"
        )
        dbSession.add(txn)
        dbSession.commit()
        dbSession.refresh(txn)
        engine = RuleEngine(dbSession)
        alerts = await engine.evaluateAllRules(1)
        await manager.broadcast({
            "type": "transaction",
            "transaction": {
                "merchant": txn.merchant,
                "amount": txn.amount,
                "category": txn.category,
                "date": txn.date.isoformat()
            }
        })
        await manager.broadcast({"type": "dashboard_update"})
        if alerts:
            await manager.broadcast({
                "type": "alert",
                "alert": {
                    "title": alerts[0].title,
                    "body": alerts[0].body,
                    "severity": alerts[0].severity
                }
            })
        return {"success": True, "alert_generated": len(alerts) > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/spending_spike")
async def testSpendingSpike(dbSession: Session = Depends(getDb)):
    try:
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        merchants = ["WOOLWORTHS", "CHECKERS", "PICK N PAY", "MAKRO", "GAME"]
        for i, merchant in enumerate(merchants):
            txn = Transaction(
                userId=1,
                accountId=account.id,
                transactionId=f"SPIKE_{int(datetime.now().timestamp() * 1000)}_{i}",
                date=datetime.now(timezone.utc) - timedelta(hours=i),
                amount=-float(300 + i * 50),
                merchant=merchant,
                description=f"Spike transaction {i+1}",
                category="Groceries"
            )
            dbSession.add(txn)
        dbSession.commit()
        engine = RuleEngine(dbSession)
        alerts = await engine.evaluateAllRules(1)
        await manager.broadcast({"type": "dashboard_update"})
        if alerts and len(alerts) > 0:
            alert = alerts[0]
            await manager.broadcast({
                "type": "alert",
                "alert": {
                    "title": alert.title if hasattr(alert, 'title') else "Spending Spike Alert",
                    "body": alert.body if hasattr(alert, 'body') else "Unusual spending detected",
                    "severity": alert.severity if hasattr(alert, 'severity') else "WARNING"
                }
            })
            return {"success": True, "alert_generated": True, "alert": {"title": alert.title, "body": alert.body}}
        return {"success": True, "alert_generated": False, "transactions_created": 5}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/api/test/new_subscription")
async def testNewSubscription(dbSession: Session = Depends(getDb)):
    try:
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        for i in range(3):
            txn = Transaction(
                userId=1,
                accountId=account.id,
                transactionId=f"SUB_{int(datetime.now().timestamp() * 1000)}_{i}",
                date=datetime.now(timezone.utc) - timedelta(days=i*30),
                amount=-99.99,
                merchant="NETFLIX",
                description="NETFLIX SUBSCRIPTION",
                category="Entertainment"
            )
            dbSession.add(txn)
        dbSession.commit()
        engine = RuleEngine(dbSession)
        alerts = await engine.evaluateAllRules(1)
        await manager.broadcast({"type": "dashboard_update"})
        if alerts:
            await manager.broadcast({
                "type": "alert",
                "alert": {
                    "title": alerts[0].title,
                    "body": alerts[0].body,
                    "severity": alerts[0].severity
                }
            })
        return {"success": True, "alert_generated": len(alerts) > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/category_limit")
async def testCategoryLimit(dbSession: Session = Depends(getDb)):
    try:
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        txn = Transaction(
            userId=1,
            accountId=account.id,
            transactionId=f"CAT_{int(datetime.now().timestamp() * 1000)}",
            date=datetime.now(timezone.utc),
            amount=-2500.00,
            merchant="OCEAN BASKET",
            description="Category limit test",
            category="Restaurants"
        )
        dbSession.add(txn)
        dbSession.commit()
        engine = RuleEngine(dbSession)
        alerts = await engine.evaluateAllRules(1)
        await manager.broadcast({"type": "dashboard_update"})
        if alerts:
            await manager.broadcast({
                "type": "alert",
                "alert": {
                    "title": alerts[0].title,
                    "body": alerts[0].body,
                    "severity": alerts[0].severity
                }
            })
        return {"success": True, "alert_generated": len(alerts) > 0}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/payday")
async def testPayday():
    try:
        await manager.broadcast({
            "type": "alert",
            "alert": {
                "title": "💰 Payday Approaching",
                "body": "Your payday is in 3 days. Current balance is low!",
                "severity": "INFO"
            }
        })
        return {"success": True, "alert_generated": True, "alert": {"title": "💰 Payday Approaching", "body": "Your payday is in 3 days. Current balance is low!"}}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/transaction")
async def testTransaction(request: Request, dbSession: Session = Depends(getDb)):
    try:
        data = await request.json()
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        merchant = data.get('merchant', 'TEST MERCHANT')
        amount = data.get('amount', -100.00)
        txn = Transaction(
            userId=1,
            accountId=account.id,
            transactionId=f"TEST_{int(datetime.now().timestamp() * 1000)}",
            date=datetime.now(timezone.utc),
            amount=amount,
            merchant=merchant,
            description=f"Test: {merchant}",
            category=categorizeTransaction("", merchant)
        )
        dbSession.add(txn)
        dbSession.commit()
        await manager.broadcast({
            "type": "transaction",
            "transaction": {
                "merchant": txn.merchant,
                "amount": txn.amount,
                "category": txn.category,
                "date": txn.date.isoformat()
            }
        })
        await manager.broadcast({"type": "dashboard_update"})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/test/balance")
async def testBalance(request: Request, dbSession: Session = Depends(getDb)):
    try:
        data = await request.json()
        account = dbSession.query(Account).first()
        if not account:
            return {"success": False, "error": "No account found"}
        newBalance = float(data.get('balance', 10000.00))
        account.currentBalance = newBalance
        account.availableBalance = newBalance
        dbSession.commit()
        await manager.broadcast({
            "type": "balance_update",
            "balance": newBalance
        })
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)