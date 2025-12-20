import anthropic
import json
import os
from typing import Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session


class FinancialAIAgent:
    def __init__(self, db: Session, anthropicApiKey: str = None):
        """Initialize with database session and API key"""
        self.db = db
        
        # IMPORTANT: Clear any proxy environment variables that might interfere
        proxyVars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                     'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy']
        for var in proxyVars:
            if var in os.environ:
                del os.environ[var]
        
        apiKey = anthropicApiKey if anthropicApiKey else "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"
        
        # Initialize client with ONLY the api_key parameter
        # Don't pass anything else to avoid proxy issues
        try:
            # Method 1: Direct initialization
            self.client = anthropic.Anthropic(api_key=apiKey)
            print("✅ Anthropic client initialized successfully")
        except TypeError as e:
            if "proxies" in str(e):
                print("⚠️ Proxy error detected, using workaround...")
                # Method 2: Use the Client class directly without httpx
                try:
                    from anthropic import Anthropic
                    self.client = Anthropic(api_key=apiKey)
                    print("✅ Anthropic client initialized with workaround")
                except Exception as e2:
                    print(f"❌ Failed to initialize: {e2}")
                    raise Exception(f"Cannot initialize Anthropic client. Please update anthropic library: pip install --upgrade anthropic --break-system-packages")
            else:
                raise
        except Exception as e:
            print(f"❌ Error initializing Anthropic client: {e}")
            raise Exception(f"Cannot initialize Anthropic client: {e}")
        
        self.model = "claude-sonnet-4-20250514"
    
    async def chat(self, userMessage: str) -> Dict:
        """
        Returns: {"response": "AI response text", "success": True}
        """
        try:
            # Get financial context from database
            context = self._getFinancialContext()
            
            # Create system prompt with context
            systemPrompt = f"""You are a helpful financial assistant for a South African user.

{context}

Guidelines:
- Use South African Rands (R) for currency
- Be conversational and friendly
- Provide actionable insights based on the data
- Keep responses concise but informative
- Reference actual numbers from the data when relevant

Always base your responses on the financial data provided above."""

            # Call Claude API - using minimal parameters
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=systemPrompt,
                messages=[
                    {
                        "role": "user",
                        "content": userMessage
                    }
                ]
            )
            
            # Extract text response
            textResponse = ""
            for block in response.content:
                if hasattr(block, "text"):
                    textResponse += block.text
            
            return {
                "response": textResponse,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "response": f"I encountered an error: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _getFinancialContext(self) -> str:
        """Get financial context from database"""
        try:
            # Import here to avoid circular imports
            from main import Account, Transaction
            
            # Get account
            account = self.db.query(Account).first()
            
            if not account:
                return "No account data available."
            
            # Get recent transactions
            transactions = self.db.query(Transaction).order_by(
                Transaction.date.desc()
            ).limit(20).all()
            
            # Build context string
            context = f"Current Account Balance: R {account.currentBalance:,.2f}\n\n"
            
            if transactions:
                # Calculate totals
                debits = [t for t in transactions if t.amount < 0]
                credits = [t for t in transactions if t.amount > 0]
                
                totalSpent = sum(abs(t.amount) for t in debits)
                totalIncome = sum(t.amount for t in credits)
                
                context += f"Recent Activity ({len(transactions)} transactions):\n"
                context += f"- Total Spent: R {totalSpent:,.2f}\n"
                context += f"- Total Income: R {totalIncome:,.2f}\n\n"
                
                # Category breakdown
                categories = {}
                for t in debits:
                    cat = t.category or "Other"
                    categories[cat] = categories.get(cat, 0) + abs(t.amount)
                
                if categories:
                    context += "Spending by Category:\n"
                    sortedCats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
                    for cat, amount in sortedCats[:5]:
                        context += f"- {cat}: R {amount:,.2f}\n"
                    context += "\n"
                
                # Recent transactions
                context += "Recent Transactions:\n"
                for t in transactions[:10]:
                    sign = "+" if t.amount >= 0 else ""
                    dateStr = t.date.strftime("%Y-%m-%d") if hasattr(t.date, 'strftime') else str(t.date)
                    context += f"- {t.merchant}: {sign}R {t.amount:,.2f} ({dateStr})\n"
            
            return context
            
        except Exception as e:
            print(f"❌ Error getting context: {e}")
            return "Financial data temporarily unavailable."