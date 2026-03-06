# 🏦 SentiVest

**🤖 AI Private Banking Agent with a Personal Financial Knowledge Graph**

SentiVest is an autonomous AI banking agent built for the South African market. It goes beyond traditional banking dashboards by combining a personal financial knowledge graph with real-time transaction classification, voice-first interaction, and proactive financial intelligence.

> 💡 Banks give you data. SentiVest gives you understanding.

---

## ⚡ What Makes This Different

| Traditional Banking | SentiVest |
|---|---|
| 📊 Shows balance | 🔮 Predicts when you'll run out |
| 📋 Lists transactions | 🛡️ Classifies and scores every one |
| 🖥️ Static dashboard | 🧬 Living knowledge graph |
| 🚫 No memory | 🧠 Remembers your goals and habits |
| 👤 You drive | 🤖 The agent drives |
| ⏳ Reactive | ⚡ **Proactive** |

---

## 🏗️ Architecture

```
🎙️ Voice / Chat Interface        35+ handlers, multi-turn flows, persistent memory
          |
  🧠 AI Model Layer              Qwen 2.5-3B (Ollama) + rule-based fallback
          |
  🕸️ Knowledge Graph             Accounts, merchants, loans, investments, insurance, tax
          |
  🛡️ Transaction Classifier      100+ merchants, 6 fraud indicators, SAFE/FLAG/ALERT/BLOCK
          |
  ⚙️ Infrastructure              FastAPI (async) + WebSocket + Investec API (OAuth2)
```

---

## ✨ Features

### 🤖 Core Agent Capabilities
- 🛡️ **Transaction Classification** — Real-time fraud detection with weighted scoring across 100+ known merchants and 6 fraud indicators
- 🕸️ **Knowledge Graph** — Personal financial graph connecting accounts, merchants, categories, loans, investments, insurance, tax, budgets, goals, and patterns
- 🎙️ **Voice Intelligence** — 35+ voice command handlers with persistent memory, multi-turn payment flows, and natural banker-like conversation
- 💡 **Proactive Insights** — Budget warnings, spending habit detection, savings rate analysis, and low balance alerts without being asked

### 💰 Financial Tools
- 💚 **Financial Health Score** — 0-100 score (A-F grade) analyzing DTI, savings buffer, budget adherence, insurance coverage, investment diversity, and spending habits
- 🏦 **Loan Eligibility** — DTI-based assessment with verdict (Approved/Conditional/Declined), factor analysis, and max affordable calculation
- 🔄 **Smart Transfer** — Inter-account transfers with full audit trail in the knowledge graph
- 💳 **Beneficiary Payments** — Fuzzy beneficiary matching, disambiguation, multi-step confirmation flow

### 🎮 Life Simulator
- ⏩ Compressed real-life financial simulation (months in seconds, 0.25x-5x speed)
- 📅 Monthly cycle: Salary → Debit orders → Daily spending → Life events → Insights
- 🎲 Life events: Fraud attempts, bonuses, medical emergencies, tax refunds, salary increases, international trips, car accidents
- 📡 Real-time WebSocket event streaming with graph visualization

### 📱 UI
- 📱 **Phone Mockup** — iPhone-style card carousel, 12 pages (Home, Ledger, Chat, Budgets, Alerts, Documents, Scanner, Tasks, Report, Test, Profile)
- 🎛️ **Command Center** — Health score ring gauge, loan eligibility panel, AI insights feed, smart transfer, spending breakdown
- 🕸️ **Knowledge Graph Visualization** — D3.js interactive graph with demo step controls and simulator
- 📋 **Audit Log** — Real-time event feed with color-coded severity

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| ⚙️ Backend | FastAPI (Python, async) |
| 🧠 AI Model | Qwen 2.5-3B via Ollama |
| 🕸️ Knowledge Graph | Custom in-memory graph engine |
| 📡 Real-time | WebSocket |
| 🏦 Banking API | Investec Open API (OAuth2) |
| 🎙️ Voice | Web Speech API + Google STT |
| 📊 Visualization | D3.js |
| 🖥️ Frontend | Single-page HTML/JS/CSS |

---

## 🚀 Quick Start

### Prerequisites
- 🐍 Python 3.10+
- 🦙 [Ollama](https://ollama.ai) (optional — falls back to rule-based responses)

### Setup

```bash
# Clone
git clone https://github.com/Nevvyboi/SentiVest.git
cd SentiVest

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Pull AI model
ollama pull qwen2.5:3b

# Run
python main.py 8000
```

🌐 Open `http://localhost:8000` in your browser.

### 🔐 Environment Variables (optional)

Create a `.env` file:
```
INVESTEC_CLIENT_ID=your_client_id
INVESTEC_CLIENT_SECRET=your_secret
INVESTEC_API_KEY=your_api_key
```

Without these, the app uses realistic demo data.

---

## 📁 Project Structure

```
SentiVest/
  main.py              # ⚙️  FastAPI server, 28+ API routes, WebSocket
  knowledge_graph.py   # 🕸️  Personal financial knowledge graph engine
  voice.py             # 🎙️  35+ voice command handlers, payment flows, memory
  model.py             # 🧠  AI model integration (Ollama Qwen 2.5-3B + fallback)
  agent.py             # 🛡️  Transaction classifier (100+ merchants, fraud scoring)
  simulator.py         # 🎮  Life simulator, health score, loan eligibility
  kg_routes.py         # 🔗  Knowledge graph API routes
  investec_api.py      # 🏦  Investec Open API wrapper (OAuth2)
  test_all.py          # 🧪  71+ tests
  static/
    combined.html      # 📱  Single-page app (phone + dashboard)
  presentation.html    # 🎤  Project presentation slides
```

📖 See individual READMEs for detailed documentation:
- [`static/README.md`](static/README.md) — 📱 Frontend UI documentation

---

## 🔌 API Overview

| Endpoint | Description |
|---|---|
| `POST /api/classify` | 🛡️ Classify transaction (SAFE/FLAG/ALERT/BLOCK) |
| `POST /api/voice` | 🎙️ Process voice command |
| `POST /api/chat` | 💬 AI chat with KG context |
| `GET /api/health` | 💚 Financial health score (0-100) |
| `POST /api/loan/eligibility` | 🏦 Loan eligibility assessment |
| `POST /api/transfer` | 🔄 Smart inter-account transfer |
| `GET /api/insights` | 💡 Proactive AI insights |
| `GET /api/transactions` | 📋 Filtered transaction history |
| `GET /api/budgets` | 📊 Budget status |
| `GET /api/alerts` | 🚨 Active alerts |
| `POST /api/simulator/start` | 🎮 Start life simulator |
| `WS /ws` | 📡 Real-time event stream |

Full API: 28+ main routes + 15+ knowledge graph routes.

---

## 📈 By The Numbers

| Metric | Count |
|---|---|
| 🔌 API Endpoints | 28+ main + 15+ KG |
| 🎙️ Voice Commands | 35+ |
| 🏪 Known Merchants | 100+ |
| 🧠 AI Intent Types | 25+ |
| 📱 UI Pages | 12 |
| 🚩 Fraud Indicators | 6 |
| 🧪 Tests | 71+ |
| ✨ Total Features | 200+ |

---

## 🧪 Testing

```bash
python -m pytest test_all.py -v
```

---

## 🎤 Presentation

Open `presentation.html` in a browser for the full project presentation (20 slides, keyboard/touch navigation, presenter notes).

🎮 Controls: `Space`/`Arrow` = navigate, `F` = fullscreen, `N` = speaker notes.

---

## 📄 License

MIT
