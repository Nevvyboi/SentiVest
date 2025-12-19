import requests
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import json

class InvestecAPI:
    
    def __init__(self):
        self.clientId = "yAxzQRFX97vOcyQAwluEU6H6ePxMA5eY"
        self.clientSecret = "4dY0PjEYqoBrZ99r"
        self.apiKey = "eUF4elFSRlg5N3ZPY3lRQXdsdUVVNkg2ZVB4TUE1ZVk6YVc1MlpYTjBaWFYwWlcxRmRHaGpHUkJ0WVdOamIzVnVaSE50WTJGdVkwdDJlQT09"
        
        self.authUrl = "https://openapisandbox.investec.com/identity/v2/oauth2/token"
        self.baseUrl = "https://openapisandbox.investec.com"
        
        self.accessToken = None
        self.tokenExpiresAt = None
    
    def getAccessToken(self) -> str:
        try:
            authString = f"{self.clientId}:{self.clientSecret}"
            authBytes = authString.encode("ascii")
            base64Auth = base64.b64encode(authBytes).decode("ascii")
            
            headers = {
                "Authorization": f"Basic {base64Auth}",
                "x-api-key": self.apiKey,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
            
            data = {
                "grant_type": "client_credentials"
            }
            
            response = requests.post(self.authUrl, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            tokenData = response.json()
            self.accessToken = tokenData["access_token"]
            
            expiresIn = tokenData.get("expires_in", 3600)
            self.tokenExpiresAt = datetime.now(timezone.utc) + timedelta(seconds=expiresIn)
            
            print(f"✅ Investec API authenticated successfully")
            return self.accessToken
            
        except Exception as e:
            print(f"❌ Investec authentication failed: {e}")
            raise
    
    def _ensureAuthenticated(self):
        """Ensuring we have a valid access token"""
        if not self.accessToken or not self.tokenExpiresAt:
            self.getAccessToken()
        elif datetime.now(timezone.utc) >= self.tokenExpiresAt - timedelta(minutes=5):
            # Refresh token 5 minutes before expiry
            self.getAccessToken()
    
    def _callApi(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        self._ensureAuthenticated()
        
        url = f"{self.baseUrl}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.accessToken}",
            "x-api-key": self.apiKey,
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def getAccounts(self) -> List[Dict]:
        """
        Get all accounts
        """
        try:
            data = self._callApi("/za/pb/v1/accounts")
            accounts = data.get("data", {}).get("accounts", [])
            
            print(f"✅ Retrieved {len(accounts)} accounts from Investec")
            return accounts
            
        except Exception as e:
            print(f"❌ Failed to get accounts: {e}")
            return []
    
    def getAccountBalance(self, accountId: str) -> Optional[Dict]:
        """
        Get balance for specific account
        """
        try:
            data = self._callApi(f"/za/pb/v1/accounts/{accountId}/balance")
            balance = data.get("data", {})
            
            print(f"✅ Retrieved balance for account {accountId}")
            return balance
            
        except Exception as e:
            print(f"❌ Failed to get balance: {e}")
            return None
    
    def getTransactions(
        self, 
        accountId: str, 
        fromDate: Optional[str] = None,
        toDate: Optional[str] = None
    ) -> List[Dict]:
        """
        Get transactions for an account with pagination support
        Dates in format: YYYY-MM-DD
        """
        try:
            if not toDate:
                toDate = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            if not fromDate:
                fromDate = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
            
            endpoint = f"/za/pb/v1/accounts/{accountId}/transactions"
            
            page = 1
            allTransactions = []
            
            while True:
                params = {
                    "fromDate": fromDate,
                    "toDate": toDate,
                    "page": page
                }
                
                data = self._callApi(endpoint, params=params)
                
                transactions = data.get("data", {}).get("transactions", [])
                meta = data.get("meta", {})
                totalPages = int(meta.get("totalPages", 1) or 1)
                
                allTransactions.extend(transactions)
                
                if page >= totalPages:
                    break
                
                page += 1
            
            print(f"✅ Retrieved {len(allTransactions)} transactions for account {accountId}")
            return allTransactions
            
        except Exception as e:
            print(f"❌ Failed to get transactions: {e}")
            return []
    
    def getBeneficiaries(self) -> List[Dict]:
        """Get all beneficiaries"""
        try:
            data = self._callApi("/za/pb/v1/accounts/beneficiaries")
            beneficiaries = data.get("data", {}).get("beneficiaries", [])
            
            print(f"✅ Retrieved {len(beneficiaries)} beneficiaries")
            return beneficiaries
            
        except Exception as e:
            print(f"❌ Failed to get beneficiaries: {e}")
            return []
    
    def getAllData(self) -> Dict[str, Any]:
        """
        Get all account data in one call
        """
        accountsData = []
        
        accounts = self.getAccounts()
        
        for account in accounts:
            accountId = account.get("accountId")
            
            balance = self.getAccountBalance(accountId)
            
            transactions = self.getTransactions(accountId)
            
            accountsData.append({
                "account": account,
                "balance": balance,
                "transactions": transactions
            })
        
        return {
            "accounts": accountsData,
            "retrievedAt": datetime.now(timezone.utc).isoformat()
        }


class InvestecDataTransformer:
    
    @staticmethod
    def transformAccount(investecAccount: Dict, balanceData: Dict) -> Dict:
        return {
            "accountId": investecAccount.get("accountId"),
            "accountNumber": investecAccount.get("accountNumber"),
            "accountName": investecAccount.get("accountName"),
            "productName": investecAccount.get("productName"),
            "currentBalance": float(balanceData.get("currentBalance", 0)),
            "availableBalance": float(balanceData.get("availableBalance", 0)),
            "currency": balanceData.get("currency", "ZAR")
        }
    
    @staticmethod
    def transformTransaction(investecTxn: Dict) -> Dict:
        amount = float(investecTxn.get("amount", 0))
        
        return {
            "transactionId": investecTxn.get("transactionId"),
            "accountId": investecTxn.get("accountId"),
            "transactionType": investecTxn.get("type"),
            "status": investecTxn.get("status"),
            "description": investecTxn.get("description", ""),
            "merchant": investecTxn.get("description", "Unknown"),
            "amount": amount,
            "date": investecTxn.get("transactionDate"),
            "postedDate": investecTxn.get("postedDate"),
            "category": InvestecDataTransformer._categorizeTransaction(investecTxn),
            "cardNumber": investecTxn.get("cardNumber"),
            "reference": investecTxn.get("reference", "")
        }
    
    @staticmethod
    def _categorizeTransaction(txn: Dict) -> str:
        description = txn.get("description", "").lower()
        
        categories = {
            "Groceries": ["checkers", "woolworths", "pick n pay", "spar", "shoprite", "makro"],
            "Restaurants": ["restaurant", "nandos", "spur", "steers", "ocean basket", "wimpy"],
            "Fast Food": ["mcdonald", "burger king", "kfc", "steers", "debonairs", "roman's pizza"],
            "Transport": ["uber", "bolt", "fuel", "petrol", "shell", "engen", "bp", "caltex", "sasol"],
            "Entertainment": ["cinema", "movies", "netflix", "showmax", "dstv", "spotify", "apple music"],
            "Shopping": ["woolworths", "edgars", "truworths", "mr price", "takealot", "game", "makro"],
            "Utilities": ["electricity", "water", "municipality", "eskom", "city power"],
            "Telecommunications": ["vodacom", "mtn", "cell c", "telkom", "data", "airtime"],
            "Health": ["pharmacy", "clicks", "dischem", "doctor", "hospital", "medical"],
            "Travel": ["flight", "airline", "hotel", "booking", "airbnb"],
            "Salary": ["salary", "wages", "payment", "payroll"],
            "Transfer": ["transfer", "payment", "eft"],
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in description:
                    return category
        
        if float(txn.get("amount", 0)) > 0:
            return "Income"
        
        return "Other"


def createInvestecClient() -> Optional[InvestecAPI]:
    """
    Create and authenticate Investec API client
    """
    try:
        client = InvestecAPI()
        client.getAccessToken()
        return client
    except Exception as e:
        print(f"❌ Failed to create Investec client: {e}")
        return None