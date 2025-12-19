# ⚡ SentiVest

**Guardian of Your Investments** | AI-Powered Financial Monitoring for Investec

> Smart alerts, real-time monitoring, and AI-powered insights for your Investec account. Never miss a suspicious transaction again.

🚀 **Ready to use in 2 minutes** - No Investec API keys required! Uses sandbox mode with pre-loaded mock data.

---

## 📸 Screenshots

### Dashboard
<img width="1840" height="916" alt="{D586C76F-56A4-4952-A2AD-F76F0A296B88}" src="https://github.com/user-attachments/assets/c0bd19de-b857-4a54-8795-91aa82e970a5" />


### AI Assistant
<img width="522" height="751" alt="{8A61F8E9-34F7-4C7B-B91D-399B009BEB96}" src="https://github.com/user-attachments/assets/afe9d6ae-cb11-49ed-afbe-acea5bdf0b4d" />


### Testing Suite
<img width="1837" height="918" alt="{50FBC4E6-3B64-40BF-96AD-7C556B6780C7}" src="https://github.com/user-attachments/assets/dc089aaf-3163-4dcc-8fba-3fe5a90f7d11" />


---

## ✨ Features

### 🎯 Smart Alert System
- **6 Alert Rule Types**: Low balance, large transactions, spending spikes, subscriptions, category limits, payday reminders
- **Real-Time Notifications**: WebSocket-powered instant alerts
- **Customizable Rules**: Set thresholds and conditions for each alert type

### 🤖 AI Financial Assistant
- **Powered by Claude AI**: Intelligent conversation about your finances
- **Context-Aware**: Knows your balance, transactions, and spending patterns
- **Natural Language**: Ask questions in plain English
- **Smart Insights**: Get personalized financial advice

### 📊 Live Dashboard
- **Real-Time Updates**: Balance and transactions sync automatically
- **Beautiful UI**: Modern, responsive design
- **Category Analytics**: Spending breakdown by category
- **Transaction History**: Complete transaction log with search

### 🔐 Secure Integration
- **Investec Sandbox**: Pre-configured mock data - **no API keys needed!**
- **OAuth Ready**: Easy switch to real Investec account when ready
- **Read-Only Access**: No ability to make transactions
- **Local Storage**: All data stored locally on your machine
- **Privacy First**: Your financial data never leaves your computer

### 🧪 Professional Testing
- **9 Test Scenarios**: Low balance, large transactions, spending spikes, and more
- **Live Preview**: Split-screen testing with real-time dashboard updates
- **Activity Logging**: Color-coded logs for debugging
- **Success Metrics**: Track test runs and success rates

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Anthropic API Key ([Get one here](https://console.anthropic.com)) - **Optional** for AI assistant

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/sentivest.git
   cd sentivest
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

3. **Configure AI Assistant (Optional)**
   
   To enable the AI chat feature, get your Anthropic API key:
   ```bash
   # Option 1: Environment variable
   export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
   
   # Option 2: Add to aiAgent.py (line 21)
   ```
   
   💡 **Note**: The system works perfectly without AI - you'll still get all alerts, monitoring, and testing features!

4. **Run the application**
   ```bash
   python main.py
   ```
   
   The app uses **Investec Sandbox** with pre-configured mock data - no API keys needed!

5. **Open your browser**
   ```
   Dashboard: http://127.0.0.1:8000
   Testing:   http://127.0.0.1:8000/testing
   ```

---

## 📖 Usage Guide

### Setting Up Alerts

1. **Navigate to Dashboard**: Open http://127.0.0.1:8000
2. **View Active Rules**: Check the "Active Rules" section
3. **Customize Rules**: Modify rule parameters in the code (coming soon: UI configuration)

### Using the AI Assistant

1. **Click AI Button**: Bottom-right corner of dashboard (🤖 icon)
2. **Ask Questions**: Type naturally, e.g.:
   - "What's my current balance?"
   - "How much did I spend this month?"
   - "Show me unusual transactions"
   - "Compare this month to last month"
3. **Get Insights**: AI responds with context-aware financial advice

### Testing the System

1. **Open Testing Dashboard**: http://127.0.0.1:8000/testing
2. **Click Test Cards**: Each card triggers a specific scenario
3. **Watch Live Updates**: Right panel shows real-time dashboard changes
4. **Check Logs**: Bottom section shows detailed activity logs

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- FastAPI - Modern, fast web framework
- SQLAlchemy - Database ORM
- SQLite - Lightweight database
- WebSockets - Real-time updates

**Frontend:**
- Vanilla JavaScript - No framework overhead
- WebSocket Client - Live updates
- Modern CSS - Responsive design
- Font Awesome - Icons

**AI/ML:**
- Anthropic Claude - AI assistant
- Claude Sonnet 4 - Latest model
- Natural language processing

**Banking Integration:**
- Investec API - Official banking API
- OAuth 2.0 - Secure authentication
- Real-time sync - Automatic updates

### Project Structure

```
sentivest/
├── main.py                 # FastAPI application & API endpoints
├── aiAgent.py             # AI assistant (Claude integration)
├── investecApi.py         # Investec API client
├── financial_alarm.db     # SQLite database (auto-created)
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html        # Main dashboard
│   └── testing.html      # Testing dashboard
├── docs/
│   └── images/           # Screenshots (add your images here)
└── README.md             # This file
```

### Database Schema

**Tables:**
- `users` - User accounts
- `accounts` - Investec account details
- `transactions` - Transaction history
- `alert_rules` - Alert configurations
- `alerts` - Generated alerts

---

## 🎯 Alert Rules

### 1. Low Balance Alert
Triggers when account balance falls below threshold.
```python
{
    "threshold": 1000,  # Alert when balance < R1,000
    "enabled": True
}
```

### 2. Large Transaction Alert
Detects unusually large transactions.
```python
{
    "threshold_amount": 5000,  # Alert for transactions > R5,000
    "enabled": True
}
```

### 3. Spending Spike Alert
Identifies unusual spending patterns.
```python
{
    "threshold_multiplier": 2.0,  # Alert when daily spend > 2x average
    "lookback_days": 7
}
```

### 4. New Subscription Alert
Detects recurring payment patterns.
```python
{
    "min_occurrences": 2,  # Consider subscription after 2 occurrences
    "max_days_between": 35
}
```

### 5. Category Limit Alert
Monitors spending by category.
```python
{
    "category": "Restaurants",
    "monthly_limit": 2000  # Alert when category > R2,000/month
}
```

### 6. Payday Alert
Reminds about upcoming payday.
```python
{
    "payday": 25,  # Day of month
    "days_before": 3,  # Alert 3 days before
    "low_balance_threshold": 500
}
```

---

## 🤖 AI Assistant Commands

### Balance Queries
```
"What's my current balance?"
"How much money do I have?"
"Show me my account balance"
```

### Spending Analysis
```
"How much did I spend this month?"
"What are my top spending categories?"
"Analyze my restaurant spending"
"Show me my grocery expenses"
```

### Transaction Search
```
"Find unusual transactions"
"Show me large transactions"
"What did I buy at Woolworths?"
"List all my Uber rides"
```

### Comparisons
```
"Compare this month to last month"
"How does my spending compare to last week?"
"Am I spending more this month?"
```

### Budgeting & Advice
```
"Should I be worried about my spending?"
"Help me create a budget"
"Any financial advice?"
"How can I save more money?"
```

---

## 🔧 Configuration

### Investec Sandbox Mode

**SentiVest uses Investec Sandbox by default** - no API keys required!

The sandbox provides:
- ✅ Mock account data (R 42,145.23 balance)
- ✅ 10 pre-loaded transactions
- ✅ Real-time testing capabilities
- ✅ Full alert system functionality

**To use your real Investec account:**

1. **Create Developer Account**: https://developer.investec.com
2. **Create New App**:
   - Name: SentiVest
   - Redirect URI: http://localhost:8000/callback
   - Scopes: `accounts`, `transactions`
3. **Get Credentials** and update `investecApi.py`:
   ```python
   # In investecApi.py (lines 10-11)
   CLIENT_ID = "your_client_id_here"
   CLIENT_SECRET = "your_client_secret_here"
   
   # Set USE_SANDBOX to False (line 13)
   USE_SANDBOX = False
   ```

### AI Assistant Setup (Optional)

1. **Get Anthropic API Key**: https://console.anthropic.com/settings/keys
2. **Free Tier**: $5 free credits (~100-200 conversations)
3. **Configure**:
   ```python
   # In aiAgent.py (line 21)
   api_key = "sk-ant-api03-your-key-here"
   
   # Or use environment variable:
   export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
   ```

💡 **Without AI key**: All features work except the AI chat assistant. You'll still get alerts, monitoring, dashboard, and testing!

### Database Configuration

Database is auto-created on first run. To reset:
```bash
rm financial_alarm.db
python main.py  # Will recreate fresh database with sandbox data
```

---

## 🧪 Testing

### Run Test Suite

```bash
# Start server
python main.py

# Open testing dashboard
http://127.0.0.1:8000/testing
```

### Available Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| Low Balance | Sets balance to R450 | Low balance alert |
| Large Transaction | Creates R5,000 transaction | Large transaction alert |
| Spending Spike | Creates 5 rapid transactions | Spending spike alert |
| New Subscription | Creates Netflix pattern | Subscription detected |
| Category Limit | R2,500+ restaurant spending | Category limit alert |
| Payday Alert | Simulates payday approach | Payday reminder |
| New Transaction | Creates single transaction | No alert |
| Update Balance | Random balance change | Dashboard updates |
| Sync Data | Full Investec sync | Latest data loaded |

---

## 📊 API Endpoints

### Dashboard & Data

```
GET  /                      - Main dashboard
GET  /testing              - Testing dashboard
GET  /api/dashboard        - Dashboard data (JSON)
POST /api/sync             - Sync with Investec
```

### Alerts

```
GET  /api/alerts           - Get all alerts
POST /api/alerts/evaluate  - Run alert rules
GET  /api/rules            - Get alert rules
```

### AI Assistant

```
POST /api/ai/chat          - Chat with AI
Body: {"message": "What's my balance?"}
```

### Testing

```
POST /api/test/low_balance       - Test low balance alert
POST /api/test/large_transaction - Test large transaction
POST /api/test/spending_spike    - Test spending spike
POST /api/test/subscription      - Test subscription detection
POST /api/test/category_limit    - Test category limit
POST /api/test/payday            - Test payday alert
POST /api/test/transaction       - Add test transaction
POST /api/test/update_balance    - Update balance
```

### WebSocket

```
WS /ws/dashboard          - Real-time dashboard updates
WS /ws/testing            - Real-time testing updates
```

---

## 🐛 Troubleshooting

### Common Issues

**Problem: No data showing on dashboard**
```bash
# Initialize the system
# Open: http://127.0.0.1:8000
# Wait 5-10 seconds for auto-initialization
# Sandbox data will load automatically!

# Or manually trigger:
# Open browser console (F12) and run:
fetch('/api/initialize', {method: 'POST'}).then(() => location.reload());
```

**Problem: AI chat not responding**
```bash
# AI assistant is optional - check if you want to enable it:
echo $ANTHROPIC_API_KEY

# To enable AI chat:
export ANTHROPIC_API_KEY="sk-ant-api03-..."
python main.py
```

**Problem: Want to use real Investec account instead of sandbox**
```python
# In investecApi.py, update:
USE_SANDBOX = False
CLIENT_ID = "your_real_client_id"
CLIENT_SECRET = "your_real_client_secret"

# Then restart server
python main.py
```

**Problem: WebSocket disconnects**
```bash
# Check console for errors (F12 in browser)
# Restart server
python main.py
```

**Problem: Database errors**
```bash
# Reset database (will recreate with sandbox data)
rm financial_alarm.db
python main.py
```

**Problem: Port already in use**
```bash
# Use different port
uvicorn main:app --port 8001

# Or kill existing process
lsof -ti:8000 | xargs kill -9  # Linux/Mac
netstat -ano | findstr :8000   # Windows
```

---

---

## 🙏 Acknowledgments

- **Investec** - For the amazing developer API
- **Anthropic** - For Claude AI and excellent API
- **FastAPI** - For the incredible web framework

---
