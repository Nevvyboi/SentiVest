# SentiVest Frontend

**Single-page application** — Phone mockup (left) + tabbed dashboard (right).

All UI lives in `combined.html` — one self-contained file with HTML, CSS, and JavaScript.

---

## Phone Mockup (Left Panel)

12 pages accessible via bottom navigation and the "More" menu:

| Page | Description |
|---|---|
| **Home** | Bank card carousel (swipe between accounts), quick actions (Talk, Pay, Tasks, Budget), recent transactions |
| **Ledger** | Full transaction history with filters (All / Income / Expenses), running balance |
| **Chat** | Free-form AI chat with knowledge graph context |
| **Budgets** | Budget cards with progress bars, over-limit badges |
| **Alerts** | Fraud alerts and anomaly warnings with severity levels |
| **Documents** | PDF downloads — bank statements, tax certificates, proof of payment |
| **Scanner** | Receipt scanning (mock) with merchant/category extraction |
| **Tasks** | AI-generated to-do list with priority pills and check-off |
| **Report** | Weekly spending breakdown by category with AI insights |
| **Test** | Live transaction classifier — enter merchant/amount/time, get verdict |
| **Profile** | User name editing, AI memory management (facts, preferences), conversation stats |
| **Detail** | Single transaction deep-dive with classification reasoning |

### Phone Components
- **Card Carousel** — iPhone-style horizontal swipe through bank accounts with dot indicators
- **Floating Mic FAB** — Always-visible microphone button for voice commands
- **Voice Overlay** — Full-screen overlay with recording waveform, text input, chat history, quick action chips
- **Toast Notifications** — Animated alerts for transactions, fraud, and system events
- **Payment Flow Cards** — Inline beneficiary list, disambiguation, amount entry, confirmation, success animation
- **Bottom Navigation** — Home, Ledger, Chat, More (with badge count)
- **Slide-up More Menu** — Access to all secondary pages

---

## Dashboard (Right Panel — 4 Tabs)

### Tab 1: Audit Log
Real-time event feed showing every action, transaction, and system event. Color-coded by severity (critical, warning, action, safe, info). Auto-scrolling with timestamps.

### Tab 2: Command Center
- **Health Score Ring** — Animated SVG gauge (0-100), letter grade (A-F), component breakdown bars (DTI, buffer, budgets, insurance, investments, habits)
- **Loan Eligibility Panel** — Amount/type/term inputs with live assessment. Verdict badge (Approved/Conditional/Declined), DTI impact, max affordable, factor list
- **AI Insights Feed** — Proactive insights from knowledge graph analysis. Budget warnings, spending habits, savings rate, concentration alerts
- **Smart Transfer Panel** — Account selector (from/to), amount and reference fields, live transfer execution with balance update
- **Spending Breakdown** — Category bar chart with amounts

### Tab 3: Graph & Simulator
- **Knowledge Graph** — D3.js force-directed graph visualization. Nodes colored by type (merchant, category, loan, income, investment, insurance, tax, budget, goal, alert, pattern, beneficiary). Hover tooltips. Search capability
- **Demo Step Buttons** — Repeatable steps (salary, debit orders, daily spending, food delivery) and one-shot life events (fraud, bonus, emergency, tax refund, salary increase, travel, accident)
- **Simulator Controls** — Start/stop button, speed selector (0.5x-5x), progress bar, month/phase indicator
- **Event Feed** — Real-time transaction and alert events during simulation

### Tab 4: Testing
- **Transaction Classifier** — Enter merchant name, amount (ZAR), time. Get real-time classification with verdict, confidence, reasoning, fraud indicators, and risk tags
- **Voice Command Triggers** — Quick-test buttons for common voice commands
- **Payment Flow Triggers** — Test beneficiary payments, disambiguation, and listing

---

## Voice System

### Speech Recognition
- Web Speech API for browser-based recognition
- Google Speech-to-Text for audio file transcription (16kHz mono WAV)
- Push-to-talk via mic button or text input fallback

### Text-to-Speech
- Premium voice selection with priority list (Google UK English, Microsoft voices)
- Tuned rate (1.15x) and pitch (1.02) for natural delivery
- Text cleanup: R currency expansion, abbreviation handling, markdown stripping

### Dynamic UI Rendering
Voice responses can include interactive UI elements:
- **Beneficiary List** — Selectable cards with avatars, names, bank details
- **Payment Confirmation** — Amount, recipient, reference fields with confirm/cancel
- **Success Animation** — Checkmark with transaction summary

---

## Key CSS Design System

```
Colors:
  --navy: #003B5C     (primary brand, headers, buttons)
  --teal: #007A6E     (accent, interactive elements, links)
  --teal-light: #E8F5F2  (hover states, light backgrounds)
  --red: #B91C1C      (critical alerts, fraud, over-budget)
  --orange: #C2571A   (warnings, flagged items)
  --yellow: #C68A0E   (caution, medium priority)
  --green: #2E7D6F    (safe, completed, positive)

Typography:
  Libre Franklin — UI text (300-800 weights)
  DM Mono — Numbers, amounts, timestamps

Phone Dimensions:
  320px x 660px, border-radius 32px
```

---

## WebSocket Events

The UI connects to `ws://localhost:8000/ws` and handles:

| Event | Source | Description |
|---|---|---|
| `new_transaction` | Classification | New transaction classified |
| `graph_update` | KG | Knowledge graph changed |
| `sim_transaction` | Simulator | Simulated transaction |
| `sim_alert` | Simulator | Fraud/anomaly during simulation |
| `sim_phase` | Simulator | Simulator phase change |
| `sim_insights` | Simulator | Proactive insights generated |
| `health_score` | Simulator | Health score recalculated |
