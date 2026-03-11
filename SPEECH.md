# SentiVest Presentation Speech

**Duration: ~17 minutes (slides + live demo)**

---

## SLIDE 1: Title & Introduction (45 seconds)

Hey everyone, I'm Nevin Tom, I'm a data engineer.

Today I want to show you something I've been building called **SentiVest**. It's basically an AI banking agent that sits on top of a personal financial knowledge graph.

Quick thing before we start, there's a QR code on screen. If you scan it, you can follow along on your phone and swipe through the slides at your own pace.

Cool, let's get into it.

---

## SLIDE 2: Why I Built This (30 seconds)

So I bank with Investec, right? And like most of you, I open my banking app, check my balance, maybe scroll through a few transactions... and then I close it. I don't actually *learn* anything from the experience.

And I kept thinking, **what if my banking app actually understood me?**

Like, not just showing me numbers, but actually connecting the dots. Knowing my habits. Warning me before I blow my budget. Remembering that I told it I'm saving for a house.

That's basically what SentiVest is. I built the whole thing: backend, frontend, AI, the graph. About 10,000 lines of code.

---

## SLIDE 3: "Do you actually understand where your money goes?" (20 seconds)

But let me start with a question.

*[Read the slide slowly]*

"Do you actually understand where your money goes?"

Like, really think about that. Not just your balance, but *where* your money actually flows, *why* it goes there, and what that means for your future.

Most of us have no idea. And honestly, that's not really our fault.

---

## SLIDE 4: The Problem (45 seconds)

It's because our banking apps are just... **passive**. They're basically data viewers. Glorified spreadsheets.

They show you data, but they don't *think*. You see a list of transactions, but nobody taps you on the shoulder and says "hey, you've spent 53% of your income at one store this month."

Fraud detection? It's reactive. You find out after the damage is done. The money's already gone.

And then your spending, your loans, your investments, your insurance, your tax, they all live in **separate silos**. Nothing connects them. No app tells you how your car loan affects your ability to buy a house.

Most people don't even know their debt-to-income ratio. They have no idea what their actual financial health looks like.

And good luck calling your bank at 2am when you're stressed about money. You'll get a chatbot that goes "I didn't understand that, please try again."

---

## SLIDE 5: What If (15 seconds)

So... what if your banking app wasn't really an app at all?

*[Pause]*

What if it was an **agent**?

Something that actually thinks. Connects dots. Remembers who you are. And acts on your behalf before you even have to ask.

---

## SLIDE 6: App vs Chatbot vs Agent (45 seconds)

Let me break down what I mean by "agent," because it's a specific thing.

Look at this table, three columns. Traditional App, Chatbot, AI Agent.

A traditional app just waits for you to click buttons. No memory. No reasoning. You're doing all the driving.

A chatbot is slightly better. You ask it stuff, it gives you scripted answers. But it still doesn't remember you. Every conversation starts from scratch.

An **AI agent** is a completely different animal. It doesn't wait for you, it's watching everything. It has persistent memory, it actually learns who you are over time. It reasons, it spots patterns across your entire financial history. It has autonomous behaviours, like freezing a suspicious card without you asking. And the big one, it's **proactive**. It comes to *you* with warnings, not the other way around.

And check the last two rows. A traditional app stores SQL rows. A chatbot remembers your last message. An agent uses a **Knowledge Graph**, your entire financial life, all connected.

---

## SLIDE 7: What the Agent Does (40 seconds)

So what does this agent actually do day-to-day? It runs a continuous cycle of five behaviours.

It **perceives**. Every transaction flows in real-time through WebSocket. The agent sees it before you even check your phone.

It **classifies**. Each transaction gets scored across six fraud indicators. Safe, Flagged, Alert, or Blocked.

It **warns** you, proactively. Food budget exceeded? Suspicious pattern? Balance getting low? You get a heads-up *without asking*.

It **remembers**. Your name, your goals, what you care about financially. That stuff gets saved to disk. Come back next week, next month, it still knows you.

And it **acts**. Freezes dodgy cards, runs payments, moves money between accounts, creates tasks. All on its own.

This isn't a one-and-done chatbot response. It's a continuous loop of behaviours.

---

## SLIDE 8: Why a Knowledge Graph? (50 seconds)

Now, the brain behind all of this, the thing that actually makes it work, is a **Knowledge Graph**.

Let me show you the difference.

On the left, a traditional database. Flat rows. Transaction ID, merchant, amount, date. That's it. Every row sits there by itself. There's no connection between Woolworths and your food budget, or between your food budget and your savings goal.

On the right, a knowledge graph. Woolworths connects to Groceries, which connects to your Food Budget, which connects to a Monthly Pattern, which connects to a Prediction.

It's not just data, it's a **web of relationships**. And that web is what lets the agent actually reason. You shop at Woolworths, and the graph can tell you: "That pushes your food budget over limit, which drops your savings rate, which pushes your house deposit goal back by two months."

Try doing that with a database. You'd need five separate queries and a bunch of custom logic. The graph just... walks the connections.

---

## SLIDE 9: Key Insight (15 seconds)

So here's the thing.

A database tells you **what happened**. Transaction X, merchant Y, amount Z.

A knowledge graph tells you **why it matters** and **what you should do about it**.

The graph *is* the agent's brain. Without it, you've just got another chatbot. With it, you've got actual intelligence.

---

## SLIDE 10: Three Approaches (30 seconds)

Let me put this in the context of the industry.

Traditional banks use SQL databases. Great for keeping records. But they're static. They don't think.

Fintechs came along and added dashboards and pretty charts. Same data, nicer packaging. They'll show you a pie chart of your spending, but they can't tell you *why* your spending changed or what to do about it.

SentiVest uses a knowledge graph. It doesn't just store your data, it **reasons** about it. It finds patterns you never asked about. It grows with you. It's basically alive.

That's the real difference. Records versus visuals versus *reasoning*.

---

## SLIDE 11: Introducing SentiVest (30 seconds)

Alright so, SentiVest. What does it actually look like?

It's **voice-first**. You talk to it like you'd talk to an actual private banker. Not "press 1 for balance," real natural language.

It's got 37 voice commands with proper multi-turn conversations. Real-time fraud detection across 80 known South African merchants. A financial health score from 0 to 100. Loan eligibility checks. Proactive insights that come to you.

And there's a life simulator that compresses months of financial activity into seconds, so you can literally watch the knowledge graph grow in real-time.

Built for the South African market, plugged into the Investec Open API.

---

## SLIDE 12: Architecture (40 seconds)

Let me quickly walk you through how it's built. Five layers.

At the top, the **Voice and Chat Interface**. That's `voice.py`, 37 handlers that parse what you say, manage multi-turn payment flows, and save your memory to disk.

Below that, the **AI Model Layer**. `model.py`. It takes your words and extracts structured JSON intents, 28 different types. And if the AI model goes down? It automatically falls back to keyword-based rules. Always works.

In the middle, the **Knowledge Graph**. `knowledge_graph.py`, over 2,000 lines. This is the single source of truth. Every balance, every merchant, every pattern lives here. Not in a database, in a connected graph.

Below that, the **Transaction Classifier**. `agent.py`. Scores every transaction across 6 weighted fraud indicators and spits out a verdict.

And at the bottom, **FastAPI**, fully async, running 41 API routes with concurrent WebSocket streams for real-time updates.

---

## SLIDE 13: DEMO (5 seconds)

Alright, enough talking. Let me just show you.

*[Switch to browser, localhost:8000]*

---

## LIVE DEMO (~5-6 minutes)

### Part 1: The Phone UI (1 minute)

*[Show the phone mockup on the left]*

So this is the phone interface. You've got a bank card carousel up here, swipe between accounts, same feel as your iPhone wallet. Below that, quick actions: Talk, Pay, Tasks, Budget. And your recent transactions.

Let me flip through a few pages. Here's the Ledger, full transaction history with filters. Budgets, each category has a progress bar, you can see which ones are blown. Alerts, fraud warnings with severity levels.

### Part 2: Voice Commands (2 minutes)

*[Click the mic button or type in the voice overlay]*

Let me talk to it.

**"What's my balance?"**

*[Wait for response]*

See that? It pulled the live balance straight from the knowledge graph. Real numbers, not some template.

**"Any fraud alerts?"**

*[Wait for response]*

So it knows about a blocked transaction from some unknown merchant in Zimbabwe at 2:47am. Caught it automatically.

**"Where am I spending the most?"**

*[Wait for response]*

It's telling me shopping is at 53% of my spending, way over budget. This isn't just a pie chart, it's actual contextual analysis from the graph.

Now watch this. **"Remember that I'm saving for a house"**

*[Wait for response]*

That fact is now saved to disk. I can restart the whole app, come back next week, it still remembers.

And here's the fun part. **"Pay Mom R500"**

*[Wait for the multi-turn flow]*

Watch, it found "Mom" in my beneficiaries, and now it's asking me to confirm. I'll say yes.

*[Confirm the payment]*

Done. Payment went through, balance updated, and the knowledge graph just recorded that as a new node and edge. Everything connected.

### Part 3: Command Center (1 minute)

*[Click the Command Center tab]*

This is the financial cockpit. See that health score ring, 68 out of 100, B grade. It looks at six things: debt-to-income ratio, savings buffer, budget adherence, insurance coverage, investment diversity, and spending habits.

Let me try a loan check. I'll punch in R500,000, home loan, 20-year term.

*[Enter values and submit]*

Look, it calculated the DTI impact, shows me the max I can actually afford, and gives a verdict with a full factor breakdown.

And these insights down here, the agent generated all of this on its own from the knowledge graph. Budget warnings, spending concentration, savings rate. I never asked for any of it.

### Part 4: Life Simulator (1-2 minutes)

*[Click the Graph & Simulator tab]*

This is the knowledge graph visualization, D3.js force-directed graph. Each colored node is a different type: merchants, categories, loans, investments.

I'm going to fire up the simulator at 2x speed.

*[Click Start]*

Watch. Salary comes in, see the green toast. Now debit orders rolling through: home loan, car finance, insurance. Now daily spending: Woolworths, Shell, Uber Eats.

*[Point at the graph]*

Look at the graph, new nodes popping up in real-time. New edges connecting them. The audit log on the left is streaming every single event.

*[Wait for a life event]*

There, fraud attempt. The agent caught it, classified it as BLOCK, and generated an alert. All automatic, no human involved.

And watch the health score, see the ring gauge updating live.

*[Stop the simulator after 2-3 months]*

That was three months of financial life in about 30 seconds.

---

## SLIDE 14: Voice Demo Recap (skip or 10 seconds)

*[Click through quickly]*

So you just saw real data from the graph, multi-turn payment flows, persistent memory, text-to-speech. All running on 28 intent types.

---

## SLIDE 15: Command Center Recap (skip or 10 seconds)

*[Click through quickly]*

Health score, loan eligibility, proactive insights, smart transfers, all wired through the knowledge graph.

---

## SLIDE 16: Simulator Recap (skip or 10 seconds)

*[Click through quickly]*

Salary, debit orders, daily spending, life events, insights, all compressed into real-time with WebSocket streaming.

---

## SLIDE 17: Challenges (45 seconds)

So, this thing wasn't easy to build. Let me tell you about some of the parts that really made me sweat.

**The frontend is one HTML file.** 3,260 lines, 114 JavaScript functions, zero frameworks. No React, no Vue, just raw vanilla JS trying to keep track of a phone UI, WebSocket streams, a D3 graph, and a dashboard all at once. That was... a decision I made early on. It works, but I won't pretend it was pleasant.

**The fraud scoring** was really fiddly. Six weighted indicators all feeding into a single 0-to-1 score: unknown merchant, late night, high value, foreign origin, rapid succession, round amounts. Getting the weights right so it catches real threats without flagging every Woolworths run as suspicious... that took a lot of trial and error.

**Multi-turn voice payments** were probably the hardest part. When someone says "Pay Mom R500," the agent has to pull out the name, fuzzy-match it against beneficiaries, handle it when there's multiple matches, extract the amount, ask for confirmation, and execute. And that whole flow is regex and a state machine, no ML. Making that handle the way real people actually talk was brutal.

And **the life simulator**, it runs as an async background task firing transactions through WebSocket while the UI, voice commands, and graph are all running at the same time. Let's just say I got very familiar with race conditions.

---

## SLIDE 18: Paradigm Shift (30 seconds)

So let me recap the shift here.

Traditional banking *shows your balance*. SentiVest *tells you when you're going to run out*.

Traditional banking *lists transactions*. SentiVest *classifies and scores every single one*.

Traditional banking gives you a *static dashboard*. SentiVest gives you a *living knowledge graph*.

Traditional banking has *no memory*. SentiVest *remembers your goals and habits across sessions*.

In traditional banking, *you drive*. With SentiVest, *the agent drives*.

Traditional banking is *reactive*. SentiVest is **proactive**.

---

## SLIDE 19: By the Numbers (15 seconds)

Quick numbers. 41 API endpoints. 37 voice commands. 80 known South African merchants. 28 AI intent types. 16 UI pages. 6 fraud indicators. About 10,250 lines of code. One developer.

---

## SLIDE 20: Why Qwen 2.5-3B (30 seconds)

Quick note on the AI model. I'm running Qwen 2.5, 3 billion parameters, locally through Ollama.

Why local? Three reasons. One, it runs on a laptop, no cloud GPU needed. Two, your financial data never leaves the device. Total privacy. Three, no API costs, no rate limits.

The model runs in five different modes with different token budgets. Voice responses are capped at 80 tokens so they sound natural when spoken. Intent parsing gets 150 tokens with low temperature for precision. Chat gets 400 tokens with higher temperature for more conversational responses.

And if Ollama isn't running? The system just falls back to rule-based keyword matching. It always works, no matter what.

---

## SLIDE 21: Knowledge Graph in Detail (30 seconds)

Quick look inside the graph engine. It handles 14 node types: Merchants, Categories, Budgets, Patterns, Predictions, Loans, Investments, Insurance, Tax, Income, Beneficiaries, Accounts, Transfers, and Alerts.

It's 100% in-memory. No database underneath. Zero-latency traversal. When the agent needs context to answer a question, it walks the graph and builds a prompt in microseconds.

And it's self-discovering. It picks up patterns, subscriptions, and anomalies automatically as transactions flow in. You don't set anything up. It just learns.

---

## SLIDE 22: Tech Stack (15 seconds)

Quick tech stack rundown. FastAPI backend, fully async. Qwen 2.5-3B running locally via Ollama. Custom in-memory knowledge graph engine. Bidirectional WebSocket for real-time. Investec Open API for the banking layer. Web Speech API for voice. D3.js for graph visualization. And the whole frontend, no frameworks at all. One HTML file, vanilla JavaScript and CSS.

---

## SLIDE 23: A Note to the Investec API Team (40 seconds)

Since we've got the API team in the room, I want to share some honest feedback from actually building on the Investec Open API.

First of all, **thank you**. The OAuth2 flow is solid, the sandbox is easy to get going with, and having real account and transaction endpoints is what made this whole project possible.

But here's what would've made my life a lot easier:

**Real-time transaction events.** Some kind of webhook or event push. Right now the sandbox is pull-only. I ended up building an entire life simulator just to generate transaction streams. If Investec could push events as transactions happen, agents like SentiVest could react to *actual* bank activity in real-time. That would be huge.

**A transfer and payment API in the sandbox.** Right now it's read-only. I couldn't test transfers or payments against the API at all, so every write operation is simulated on my side. Even a mock endpoint that just returns success would help people prototype payment flows.

**A beneficiary API.** Just basic CRUD for beneficiaries. I had to hardcode 7 demo beneficiaries. An API to list, add, and manage them would let people build real payment agent flows.

**Richer sandbox data.** The demo transactions are always the same. Some rotation or randomization would make testing feel a lot more realistic.

These aren't complaints, they're a wishlist from someone who genuinely *wants* to keep building on this platform.

---

## SLIDE 24: Closing (20 seconds)

*[Slow down. Breathe between lines.]*

Banks give us data.

SentiVest gives us **understanding**.

A personal knowledge graph that grows with you. An AI agent that protects, advises, and acts.

Not a dashboard, a brain.

---

## SLIDE 25: Get Involved & Questions (open)

Thank you.

*[Point to QR code]*

If you want to dig into the code, scan this QR, it goes straight to the GitHub repo. Everything's open source.

If you want to get involved, open an issue, throw in a PR, or just fork it and build something on top. I'd genuinely love to see what this could look like plugged into a real Investec API connection.

You can find me on LinkedIn, linkedin.com/in/nevtom. Always happy to chat about AI, fintech, knowledge graphs, whatever.

Alright, I'm happy to take questions.

---

## TIPS FOR DELIVERY

1. **Pace yourself**: Slides 1-12 should take ~6 minutes. Demo ~6 minutes. Slides 17-25 ~5 minutes.
2. **Pause on impact slides** (3, 5, 9): Let the audience read and absorb. Silence is powerful.
3. **During the demo**: Narrate what's happening. Don't just click silently. Say "watch the graph grow" or "see how the health score updates."
4. **If something breaks during demo**: Say "this is live software, things happen" and move on. The slides recap everything.
5. **Eye contact**: Look at the audience during impact slides. Look at the screen during demo.
6. **Voice**: Speak louder and slower than feels natural. Lecture halls swallow sound.
7. **Hands**: Point at specific things on screen during demo. "See this node here? That's the fraud alert."
8. **Questions you might get:**
   - "Why not use a real database like Neo4j?" *"Custom engine gives me full control, zero overhead, runs in-process. Neo4j would add network latency and deployment complexity for a personal graph."*
   - "Why not use GPT-4 or Claude?" *"Privacy. Financial data should never leave the device. A local 3B model gives enough intelligence for structured tasks. And it's free."*
   - "Is this connected to a real bank?" *"Yes, it integrates with Investec's Open API via OAuth2. The demo uses realistic seed data, but the API layer is production-ready."*
   - "How big does the graph get?" *"The graph tracks its own memory size. After a few months of simulation, it's typically a few hundred KB, lightweight enough for any device."*
   - "Could this work for other banks?" *"The architecture is bank-agnostic. Swap out the Investec API wrapper and seed data, and it works with any bank that has an API."*
