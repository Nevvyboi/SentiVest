"""
SentiVest AI Model Layer - Qwen 2.5-3B via Ollama
Structured intent parsing + natural language generation.
Falls back to rules/templates if Ollama unavailable.
"""

import aiohttp
import asyncio
import json
import re

OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "qwen2.5:3b"

INTENT_SYSTEM_PROMPT = (
    "You are SentiVest, a South African banking AI. Extract the user's intent as JSON.\n"
    "Valid intents: balance, spending, budget, alert, subscription, savings, goal, fraud, document, "
    "transfer, loan, loan_eligibility, investment, insurance, tax, pattern, prediction, scenario, "
    "set_budget, set_goal, cancel_subscription, classify_transaction, income, health_score, "
    "compare_months, smart_transfer, start_sim, stop_sim, general_query\n\n"
    "Respond ONLY with valid JSON:\n"
    '{"intent": "<intent>", "entities": {"category": "...", "merchant": "...", "amount": 0, "period": "..."}, "confidence": 0.9}\n'
    "Only include entities that are mentioned. Do NOT add explanations."
)

INTENT_RULES = [
    ("loan_eligibility", ["eligible", "qualify", "loan application", "can i get", "apply for"]),
    ("health_score", ["health score", "financial health", "how am i doing", "financial score", "my score"]),
    ("smart_transfer", ["transfer", "move money", "send money", "move r"]),
    ("compare_months", ["compare month", "last month", "versus last", "month over month"]),
    ("start_sim", ["start sim", "simulate", "run simulation", "auto mode"]),
    ("stop_sim", ["stop sim", "pause sim", "stop auto"]),
    ("set_budget", ["set budget", "create budget", "new budget", "budget limit"]),
    ("set_goal", ["set goal", "create goal", "new goal", "save for"]),
    ("cancel_subscription", ["cancel subscription", "cancel netflix", "unsubscribe", "stop paying"]),
    ("classify_transaction", ["classify", "analyze transaction", "check transaction"]),
    ("fraud", ["fraud", "suspicious", "blocked", "freeze", "stolen", "scam"]),
    ("balance", ["balance", "how much", "money", "account", "available"]),
    ("alert", ["alert", "warning", "danger", "critical"]),
    ("budget", ["budget", "limit", "over budget", "underspent"]),
    ("subscription", ["subscription", "recurring", "netflix", "spotify", "debit order"]),
    ("spending", ["spend", "spent", "spending", "where", "most money", "category"]),
    ("savings", ["save", "saving", "emergency fund"]),
    ("income", ["income", "salary", "earn", "freelance", "bonus", "paid"]),
    ("loan", ["loan", "credit", "debt", "mortgage", "repay", "finance", "owe"]),
    ("investment", ["invest", "portfolio", "stock", "share", "etf", "dividend", "asset"]),
    ("insurance", ["insurance", "premium", "claim", "coverage", "policy", "discovery"]),
    ("tax", ["tax", "sars", "deduction", "capital gains", "tax certificate"]),
    ("transfer", ["transfer", "pay", "send money", "eft", "payment"]),
    ("document", ["statement", "document", "tax certificate", "proof", "download"]),
    ("pattern", ["pattern", "habit", "trend", "behavior"]),
    ("prediction", ["predict", "forecast", "future", "project"]),
    ("scenario", ["what if", "scenario", "cancel", "reduce"]),
    ("goal", ["goal", "target", "progress"]),
]


class SentiVestModel:
    def __init__(self):
        self.available = None
        self.url = OLLAMA_URL

    async def check_availability(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/api/tags", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        self.available = any(MODEL_NAME.split(":")[0] in m for m in models)
                        return self.available
        except Exception:
            pass
        self.available = False
        return False

    # ==================== STRUCTURED INTENT PARSING ====================

    async def generate_structured(self, text: str, context: str = "") -> dict:
        """Parse natural language into structured intent + entities via AI."""
        if self.available is None:
            await self.check_availability()

        if self.available:
            try:
                prompt = f'User said: "{text}"\n\nExtract intent and entities as JSON only.'
                system = INTENT_SYSTEM_PROMPT
                if context:
                    system += f"\n\nUSER'S FINANCIAL STATE:\n{context}"

                payload = {
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 150}
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.url}/api/generate", json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            raw = data.get("response", "").strip()
                            return self._parse_intent_json(raw, text)
            except Exception:
                pass

        return self._rule_based_intent(text)

    def _parse_intent_json(self, raw: str, original_text: str) -> dict:
        """Extract JSON from model output, with fallback."""
        # Try direct parse
        try:
            parsed = json.loads(raw)
            if "intent" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON in response
        json_match = re.search(r'\{[^{}]*"intent"[^{}]*\}', raw)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if "intent" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Try multiline JSON
        json_match = re.search(r'\{[\s\S]*?"intent"[\s\S]*?\}', raw)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                if "intent" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        return self._rule_based_intent(original_text)

    def _rule_based_intent(self, text: str) -> dict:
        """Fallback intent detection using keyword rules."""
        text_lower = text.lower()
        for intent, keywords in INTENT_RULES:
            if any(k in text_lower for k in keywords):
                return {"intent": intent, "entities": {}, "confidence": 0.7}
        return {"intent": "general_query", "entities": {}, "confidence": 0.5}

    # ==================== GENERATION ====================

    async def generate(self, prompt: str, graph_context: str = "", mode: str = "chat",
                       temperature: float = 0.5) -> str:
        if self.available is None:
            await self.check_availability()

        if self.available:
            try:
                return await self._ollama_generate(prompt, graph_context, mode, temperature)
            except Exception:
                pass

        return self._template_response(prompt, mode)

    async def _ollama_generate(self, prompt: str, context: str, mode: str, temp: float) -> str:
        system_prompt = self._build_system_prompt(mode, context)

        temps = {"chat": 0.7, "voice": 0.6, "reasoning": 0.3, "scenario": 0.4, "intent": 0.1}
        max_tokens = {"chat": 400, "voice": 80, "reasoning": 300, "scenario": 350, "intent": 150}

        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temps.get(mode, temp),
                "num_predict": max_tokens.get(mode, 300),
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.url}/api/generate", json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "").strip()
        return self._template_response(prompt, mode)

    def _build_system_prompt(self, mode: str, context: str) -> str:
        base = (
            "You are SentiVest, a personal AI private banker for Investec (South Africa). "
            "You speak like a real human banker — warm, friendly, professional, sometimes witty. "
            "Use Rands (R) for currency. Be specific with real numbers from the user's data. "
            "Use the user's name if you know it. Give brief financial advice when relevant. "
            "You can discuss anything — finances, life, goals, worries — like a trusted advisor. "
            "Never say you're an AI or can't help. Respond as a knowledgeable banker who genuinely cares.\n\n"
        )
        if context:
            base += f"USER'S FINANCIAL STATE:\n{context}\n\n"

        modes = {
            "chat": "Respond conversationally (3-6 sentences). Be helpful and specific with numbers.",
            "voice": "Respond concisely (1-3 sentences) as this will be spoken aloud. No markdown or special characters. Sound natural and human — like a banker chatting with a client. Use contractions (I'll, you're, that's). Be warm but direct.",
            "reasoning": "Explain the classification reasoning step by step. Be specific about risk factors.",
            "scenario": "Explain the scenario results with specific monthly and annual impact in Rands.",
            "intent": INTENT_SYSTEM_PROMPT,
        }
        base += modes.get(mode, modes["chat"])
        return base

    def _template_response(self, prompt: str, mode: str) -> str:
        prompt_lower = prompt.lower()

        templates = {
            "balance": "Your current balance is R34,218.66 with R42,145.23 available. "
                       "At your current burn rate of R1,476/day, you'll have approximately R1,756 by payday on the 25th.",
            "spend": "Your top spending categories: Shopping R12,399 (53%), Insurance R6,047, "
                     "Utilities R2,847, Fuel R1,250. Shopping is significantly over your R5,000 budget.",
            "alert": "You have 2 critical alerts: A blocked transaction from UNKNOWN_MERCH_ZW (R4,500 at 02:47) "
                     "and your Shopping budget is exceeded by R7,399. I've frozen the suspicious transaction.",
            "budget": "2 budgets exceeded: Food Delivery at R634/R500 per week (+R134 over), "
                      "Shopping at R12,399/R5,000 per month (+R7,399 over). Consider reducing Takealot spending.",
            "subscription": "3 active subscriptions detected: Netflix SA R299/mo, Spotify Premium R80/mo, "
                          "Vodacom R599/mo. Total: R978/month (R11,736/year). Consider if all are still needed.",
            "save": "3 ways to save: 1) Cancel Netflix (saves R3,588/year), 2) Reduce food delivery by 30% "
                    "(saves R2,284/year), 3) Set up R3,000/month auto-transfer for your Emergency Fund goal.",
            "fraud": "I blocked a suspicious R4,500 transaction from UNKNOWN_MERCH_ZW at 02:47. "
                     "Unknown merchant, late-night timing, Zimbabwe origin. Card temporarily frozen.",
            "document": "Your February 2025 statement is ready. I also have your tax certificate "
                       "and proof of payment available for download.",
            "task": "4 pending tasks: Review Takealot R12,399 charge (high priority), "
                    "Cancel Netflix trial (medium), Dispute City Power spike (high), Transfer R3,000 to savings (low).",
            "pattern": "Detected patterns: Shopping concentration at 53% of spending, 3 late-night transactions, "
                      "post-salary spending spike with 0.87 correlation.",
            "goal": "Emergency Fund: R50,000 target, saving R3,000/month. 16.7 months to go. "
                   "Zanzibar Holiday: R25,000 target, R2,500/month. 10 months to go.",
            "loan": "Active loans: Home Loan R1,650,000 at 11.75% (R16,847/mo), "
                    "Car Finance R280,000 at 12.5% (R6,333/mo), Personal Loan R35,000 at 18% (R1,267/mo). "
                    "Total monthly repayments: R24,447.",
            "invest": "Portfolio: Satrix Top 40 ETF R172,500 (+15%), Capitec Shares R31,200 (+24.8%), "
                     "Tax-Free Savings R92,000 (+15%). Total: R295,700.",
            "insurance": "3 active policies: Discovery Health R4,200/mo, Outsurance Car R1,847/mo, "
                        "Old Mutual Life R650/mo. Total: R6,697/month (R80,364/year).",
            "tax": "Tax year 2025/2026: Employment income R510,000, Interest R3,420, "
                   "Deductions: Medical aid credits R50,400, Retirement annuity R36,000.",
            "income": "Monthly income: ACME Corp salary R42,500, Side hustle R5,000, "
                     "FNB interest R285. Total: R47,785/month.",
            "eligible": "Based on your income of R47,785/month and existing obligations, "
                       "you could qualify for up to R500,000 at 18% over 60 months. DTI would be ~52%.",
            "health": "Financial health score: 68/100 (B). DTI 51% is stretched, "
                     "savings buffer at 1.1 months. Good insurance coverage. Review spending habits.",
            "compare": "This month's spending is R4,200 higher than last month (+12%). "
                      "Biggest increases: Food Delivery +R1,800, Shopping +R2,100.",
            "transfer": "Transfer complete. R5,000 moved from Private Bank Account to Savings. "
                       "New balances: Cheque R29,218, Savings R97,000.",
            "simulat": "Life simulator running at 1x speed. Watch your transactions flow in real-time. "
                      "Say 'stop simulation' to pause.",
        }

        for key, response in templates.items():
            if key in prompt_lower:
                return response

        return ("I'm SentiVest, your personal financial AI. Your balance is R34,218.66. "
                "I track your transactions, budgets, loans, investments, insurance, and tax. "
                "Ask me anything about your finances.")

    # ==================== CONVENIENCE METHODS ====================

    async def generate_reasoning(self, verdict: dict, transaction: dict, context: str) -> str:
        prompt = (f"Explain why this transaction was classified as {verdict.get('verdict', 'SAFE')}:\n"
                  f"Merchant: {transaction.get('merchant', 'Unknown')}\n"
                  f"Amount: R{transaction.get('amount', 0):,.2f}\n"
                  f"Time: {transaction.get('time', '12:00')}\n"
                  f"Reasoning: {verdict.get('reasoning', '')}")
        return await self.generate(prompt, context, "reasoning")

    async def generate_chat_response(self, message: str, context: str) -> str:
        return await self.generate(message, context, "chat")

    async def generate_voice_response(self, message: str, context: str) -> str:
        return await self.generate(message, context, "voice")

    async def generate_scenario_explanation(self, result: dict, context: str) -> str:
        prompt = f"Explain this scenario: {result.get('recommendation', '')}"
        return await self.generate(prompt, context, "scenario")

    def build_graph_context(self, knowledge_graph) -> str:
        return knowledge_graph.build_context()

    def status(self) -> dict:
        return {
            "model": MODEL_NAME,
            "url": self.url,
            "available": self.available,
            "fallback": "rules + templates"
        }


# Singleton
model = SentiVestModel()
