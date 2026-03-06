"""
SentiVest Investec Sandbox API Wrapper
OAuth2 authentication with fallback to demo data.
"""

import aiohttp
import base64
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://openapi.investec.com"
CLIENT_ID = os.getenv("INVESTEC_CLIENT_ID", "yAxzQRFX97vOcyQAwluEU6H6ePxMA5eY")
CLIENT_SECRET = os.getenv("INVESTEC_SECRET", "")
API_KEY = os.getenv("INVESTEC_API_KEY", "")

# Demo fallback data
DEMO_ACCOUNTS = {
    "data": {
        "accounts": [
            {
                "accountId": "acc_cheque",
                "accountNumber": "10012347821",
                "accountName": "Private Bank Account",
                "referenceName": "My Investec Account",
                "productName": "Private Bank Account",
                "kycCompliant": True,
                "profileId": "demo-profile"
            },
            {
                "accountId": "acc_savings",
                "accountNumber": "10012344455",
                "accountName": "Savings Account",
                "referenceName": "My Savings",
                "productName": "Savings Account",
                "kycCompliant": True,
                "profileId": "demo-profile"
            }
        ]
    }
}

DEMO_BALANCE = {
    "data": {
        "accountId": "demo-account-001",
        "currentBalance": 34218.66,
        "availableBalance": 42145.23,
        "currency": "ZAR"
    }
}

DEMO_TRANSACTIONS = {
    "data": {
        "transactions": [
            # Card purchases
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "WOOLWORTHS FOOD", "amount": 847.30, "postedOrder": 1,
             "postingDate": "2025-02-24", "transactionDate": "2025-02-24"},
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "CHECKERS HYPER", "amount": 623.50, "postedOrder": 2,
             "postingDate": "2025-02-23", "transactionDate": "2025-02-23"},
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "SHELL GARAGE N1", "amount": 1250.00, "postedOrder": 3,
             "postingDate": "2025-02-23", "transactionDate": "2025-02-23"},
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "ENGEN", "amount": 890.00, "postedOrder": 4,
             "postingDate": "2025-02-22", "transactionDate": "2025-02-22"},
            # Suspicious / fraud
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "UNKNOWN_MERCH_ZW", "amount": 4500.00, "postedOrder": 5,
             "postingDate": "2025-02-22", "transactionDate": "2025-02-22"},
            # Online purchase
            {"type": "DEBIT", "transactionType": "OnlineBankingPayments", "status": "POSTED",
             "description": "TAKEALOT.COM", "amount": 12399.00, "postedOrder": 6,
             "postingDate": "2025-02-21", "transactionDate": "2025-02-21"},
            # Debit orders
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "NETFLIX SA", "amount": 299.00, "postedOrder": 7,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "SPOTIFY PREMIUM", "amount": 79.99, "postedOrder": 8,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "VODACOM", "amount": 599.00, "postedOrder": 9,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "DISCOVERY HEALTH", "amount": 4200.00, "postedOrder": 10,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "OUTSURANCE", "amount": 1847.00, "postedOrder": 11,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "OLD MUTUAL LIFE", "amount": 650.00, "postedOrder": 12,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            # Food delivery
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "UBER EATS", "amount": 389.50, "postedOrder": 13,
             "postingDate": "2025-02-20", "transactionDate": "2025-02-20"},
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "MR D FOOD", "amount": 245.00, "postedOrder": 14,
             "postingDate": "2025-02-19", "transactionDate": "2025-02-19"},
            # Utilities
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "CITY POWER JOBURG", "amount": 2847.00, "postedOrder": 15,
             "postingDate": "2025-02-05", "transactionDate": "2025-02-05"},
            # ATM
            {"type": "DEBIT", "transactionType": "ATMWithdrawals", "status": "POSTED",
             "description": "INVESTEC ATM SANDTON", "amount": 2000.00, "postedOrder": 16,
             "postingDate": "2025-02-18", "transactionDate": "2025-02-18"},
            # EFT transfer
            {"type": "DEBIT", "transactionType": "InterAccountTransfers", "status": "POSTED",
             "description": "TRANSFER TO SAVINGS", "amount": 3000.00, "postedOrder": 17,
             "postingDate": "2025-02-15", "transactionDate": "2025-02-15"},
            # Loan repayments
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "HOME LOAN REPAYMENT", "amount": 16847.00, "postedOrder": 18,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            {"type": "DEBIT", "transactionType": "DebitOrders", "status": "POSTED",
             "description": "VEHICLE FINANCE", "amount": 6333.00, "postedOrder": 19,
             "postingDate": "2025-02-01", "transactionDate": "2025-02-01"},
            # Salary & income (credits)
            {"type": "CREDIT", "transactionType": "Salary", "status": "POSTED",
             "description": "SALARY - ACME CORP", "amount": 42500.00, "postedOrder": 20,
             "postingDate": "2025-01-25", "transactionDate": "2025-01-25"},
            {"type": "CREDIT", "transactionType": "InterAccountTransfers", "status": "POSTED",
             "description": "FREELANCE PAYMENT", "amount": 5000.00, "postedOrder": 21,
             "postingDate": "2025-02-10", "transactionDate": "2025-02-10"},
            # Interest
            {"type": "CREDIT", "transactionType": "Interest", "status": "POSTED",
             "description": "INTEREST EARNED", "amount": 285.00, "postedOrder": 22,
             "postingDate": "2025-02-28", "transactionDate": "2025-02-28"},
            # Transport
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "UBER TRIP", "amount": 145.00, "postedOrder": 23,
             "postingDate": "2025-02-20", "transactionDate": "2025-02-20"},
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "GAUTRAIN", "amount": 85.00, "postedOrder": 24,
             "postingDate": "2025-02-19", "transactionDate": "2025-02-19"},
            # Reversal
            {"type": "CREDIT", "transactionType": "Reversals", "status": "POSTED",
             "description": "REVERSAL - UNKNOWN_MERCH_ZW", "amount": 4500.00, "postedOrder": 25,
             "postingDate": "2025-02-23", "transactionDate": "2025-02-23"},
            # Contactless
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "POSTED",
             "description": "VIDA E CAFFE TAP", "amount": 75.00, "postedOrder": 26,
             "postingDate": "2025-02-24", "transactionDate": "2025-02-24"},
            # Pending
            {"type": "DEBIT", "transactionType": "CardPurchases", "status": "PENDING",
             "description": "SPUR STEAK RANCH", "amount": 380.00, "postedOrder": 27,
             "postingDate": "2025-02-25", "transactionDate": "2025-02-25"},
        ]
    }
}


class InvestecAPI:
    def __init__(self):
        self.token = None
        self.connected = False

    async def authenticate(self) -> bool:
        """Authenticate with Investec OAuth2."""
        if not CLIENT_SECRET or not API_KEY:
            self.connected = False
            return False
        try:
            credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{BASE_URL}/identity/v2/oauth2/token",
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "x-api-key": API_KEY
                    },
                    data="grant_type=client_credentials",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data.get("access_token")
                        self.connected = True
                        return True
        except Exception:
            pass
        self.connected = False
        return False

    async def _request(self, endpoint: str) -> dict | None:
        if not self.token:
            await self.authenticate()
        if not self.token:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}{endpoint}",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "x-api-key": API_KEY
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception:
            pass
        return None

    async def get_accounts(self) -> dict:
        result = await self._request("/za/pb/v1/accounts")
        return result if result else DEMO_ACCOUNTS

    async def get_balance(self, account_id: str = "demo-account-001") -> dict:
        result = await self._request(f"/za/pb/v1/accounts/{account_id}/balance")
        if result:
            return result
        # Fallback: use live KG balance instead of stale constant
        from knowledge_graph import kg
        return {"data": {
            "accountId": account_id,
            "currentBalance": kg.balance,
            "availableBalance": kg.available,
            "currency": "ZAR"
        }}

    async def get_transactions(self, account_id: str = "demo-account-001") -> dict:
        result = await self._request(f"/za/pb/v1/accounts/{account_id}/transactions")
        return result if result else DEMO_TRANSACTIONS

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "has_token": self.token is not None,
            "base_url": BASE_URL
        }


# Singleton
investec = InvestecAPI()
