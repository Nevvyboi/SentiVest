"""
SentiVest - AI Banking Agent with Personal Financial Knowledge Graph
FastAPI application with WebSocket broadcasting.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json
import io
import os
import tempfile
from datetime import datetime
import random

# Ensure ffmpeg is in PATH for pydub audio conversion
import glob as _glob
_ffmpeg_dirs = _glob.glob(os.path.join(os.path.expanduser("~"),
    "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg*/bin"))
for _d in _ffmpeg_dirs:
    if _d not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")

from knowledge_graph import kg
from kg_routes import kg_router
from model import model
from investec_api import investec
from simulator import simulator, calculate_health_score, assess_loan_eligibility, execute_transfer, _generate_insights
import agent
import voice


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def log_event(event_type: str, text: str, data: dict = None):
    """Broadcast audit log event via WebSocket."""
    event = {
        "type": event_type,
        "text": text,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "data": data or {}
    }
    await manager.broadcast(event)


async def broadcast_graph_update():
    """Send full graph visualization + stats + balance + accounts via WS for real-time rendering."""
    graph_data = kg.visualize()
    stats = kg.get_stats()
    bal = kg.get_balance()
    accounts = kg.list_accounts()
    await manager.broadcast({
        "type": "graph_update",
        "graph": graph_data,
        "stats": stats,
        "balance": bal,
        "accounts": accounts,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })


_event_loop = None


def _on_graph_change():
    """Sync callback that schedules async broadcast."""
    global _event_loop
    if _event_loop and _event_loop.is_running():
        _event_loop.create_task(broadcast_graph_update())


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _event_loop
    _event_loop = asyncio.get_event_loop()
    await investec.authenticate()
    await model.check_availability()
    kg.on_change = _on_graph_change
    kg.seed_demo_data()
    await log_event("system", "SentiVest initialized")
    model_info = "AI ready" if model.available else "AI offline (template mode)"
    await log_event("system", model_info)
    yield


app = FastAPI(title="SentiVest", version="1.0.0", lifespan=lifespan)

# Mount KG routes
app.include_router(kg_router, prefix="/api/kg")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== Page Routes ====================

@app.get("/")
async def serve_index():
    return FileResponse("static/combined.html")



# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Echo or handle incoming messages
            try:
                msg = json.loads(data)
                await log_event("info", f"WS received: {msg.get('type', 'unknown')}")
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ==================== Investec API ====================

@app.get("/api/investec/accounts")
async def get_accounts():
    result = await investec.get_accounts()
    await log_event("info", "Fetched Investec accounts")
    return result

@app.get("/api/investec/balance")
async def get_balance(account_id: str = None):
    bal = kg.get_balance(account_id)
    result = {"data": {
        "accountId": bal.get("accountId", "demo-account-001"),
        "accountName": bal.get("accountName", ""),
        "currentBalance": bal["currentBalance"],
        "availableBalance": bal["availableBalance"],
        "currency": bal["currency"]
    }}
    await log_event("info", f"Balance: R{bal['currentBalance']:,.2f}")
    return result

@app.get("/api/investec/transactions")
async def get_investec_transactions():
    result = await investec.get_transactions()
    await log_event("info", "Fetched Investec transactions")
    return result


# ==================== Transaction Classification ====================

@app.post("/api/classify")
async def classify_transaction(body: dict = Body(...)):
    merchant = body.get("merchant", "Unknown")
    amount = float(body.get("amount", 0))
    time = body.get("time", "12:00")

    verdict = agent.classify(merchant, amount, time)
    await log_event(
        "critical" if verdict["verdict"] == "BLOCK" else
        "warning" if verdict["verdict"] == "FLAG" else
        "action" if verdict["verdict"] == "ALERT" else "safe",
        f"[{verdict['verdict']}] {merchant} R{amount:,.2f} ({verdict['confidence']*100:.0f}%)"
    )

    # Generate AI reasoning if model available
    ctx = model.build_graph_context(kg)
    explanation = await model.generate_reasoning(verdict, body, ctx)

    # Budget check from KG
    category = verdict.get("category", "Unknown")
    budget_status = None
    budgets = kg.get_budgets()
    for b in budgets:
        if b["category"].lower() == category.lower():
            budget_status = b
            break

    return {
        **verdict,
        "ai_reasoning": explanation,
        "budget_check": budget_status,
        "graph_stats": kg.get_stats()
    }


# ==================== Transactions ====================

@app.get("/api/transactions")
async def get_transactions(direction: str = None, category: str = None, limit: int = None):
    txns = kg.get_transactions(direction=direction, category=category, limit=limit)
    return {"transactions": txns, "summary": kg.get_ledger_summary()}

@app.get("/api/ledger")
async def get_ledger(direction: str = None, category: str = None):
    txns = kg.get_transactions(direction=direction, category=category)
    return {"transactions": txns, "summary": kg.get_ledger_summary(), "balance": kg.get_balance()}


# ==================== Budgets ====================

@app.get("/api/budgets")
async def get_budgets():
    icon_map = {
        "Food Delivery": "🍔", "Groceries": "🛒", "Fuel": "⛽",
        "Subscription": "📱", "Shopping": "🛍️", "Coffee": "☕",
    }
    budgets = kg.get_budgets()
    for b in budgets:
        b["icon"] = icon_map.get(b.get("category", ""), "💳")
    return {"budgets": budgets}

@app.post("/api/budgets")
async def create_budget(body: dict = Body(...)):
    category = body.get("category", "")
    limit_amount = float(body.get("limit", 0))
    period = body.get("period", "month")
    result = kg.add_budget(category, limit_amount, period)
    await log_event("action", f"Budget created: {category} R{limit_amount:,.2f}/{period}")
    return result


# ==================== Alerts ====================

@app.get("/api/alerts")
async def get_alerts():
    alerts = kg.get_alerts()
    return {"alerts": alerts}


# ==================== Documents ====================

@app.get("/api/documents")
async def get_documents():
    docs = [
        {"id": 1, "type": "Statement", "title": "February 2025 Statement", "period": "01 Feb - 28 Feb",
         "size": "2.4 MB", "date": "01 Mar 2025", "icon": "📄"},
        {"id": 2, "type": "Statement", "title": "January 2025 Statement", "period": "01 Jan - 31 Jan",
         "size": "1.8 MB", "date": "01 Feb 2025", "icon": "📄"},
        {"id": 3, "type": "Tax Certificate", "title": "2024 Tax Year Certificate", "period": "Mar 2024 - Feb 2025",
         "size": "890 KB", "date": "15 Feb 2025", "icon": "🧾"},
        {"id": 4, "type": "Proof of Payment", "title": "Discovery Health - Feb", "period": "February 2025",
         "size": "145 KB", "date": "01 Feb 2025", "icon": "✅"},
        {"id": 5, "type": "Account Confirmation", "title": "Account Confirmation Letter", "period": "Current",
         "size": "320 KB", "date": "20 Feb 2025", "icon": "🏦"},
    ]
    return {"documents": docs}

@app.post("/api/documents/{doc_id}/fetch")
async def fetch_document(doc_id: int):
    await log_event("info", f"Document {doc_id} prepared for download")
    return {"status": "ready", "download_url": f"/api/documents/{doc_id}/download", "message": "Document ready for download"}


@app.get("/api/documents/{doc_id}/download")
async def download_document(doc_id: int):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    stats = kg.get_stats()
    demo_date = stats.get("demo_date", "March 2025")
    balance = stats.get("balance", 34218.66)
    total_spent = stats.get("total_spent", 0)

    # Gather typed nodes from KG (Node objects with .type, .attrs, .label, .id)
    merchant_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "merchant"]
    category_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "category"]
    alert_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "alert"]
    pattern_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "pattern"]
    income_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "income"]
    tax_nodes = [(nid, n) for nid, n in kg.nodes.items() if n.type == "tax"]

    # Document metadata
    docs_meta = {
        1: ("February 2025 Statement", "01 Feb - 28 Feb 2025"),
        2: ("January 2025 Statement", "01 Jan - 31 Jan 2025"),
        3: ("2024 Tax Year Certificate", "Mar 2024 - Feb 2025"),
        4: ("Proof of Payment - Discovery Health", "February 2025"),
        5: ("Account Confirmation Letter", "Current"),
    }
    title, period = docs_meta.get(doc_id, (f"Document {doc_id}", "Current"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=40, rightMargin=40)
    styles = getSampleStyleSheet()
    story = []

    # Header style
    h_style = ParagraphStyle("InvHeader", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#003B46"), spaceAfter=4)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#666666"), spaceAfter=16)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#003B46"), spaceBefore=16, spaceAfter=8)
    normal = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=13)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#999999"))

    # Bank header
    story.append(Paragraph("INVESTEC", h_style))
    story.append(Paragraph("Private Banking | SentiVest AI Agent", sub_style))
    story.append(Paragraph(f"<b>{title}</b>", ParagraphStyle("DocTitle", parent=styles["Heading1"], fontSize=15, spaceAfter=4)))
    story.append(Paragraph(f"Period: {period} &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", sub_style))
    story.append(Spacer(1, 8))

    # Account summary
    story.append(Paragraph("Account Summary", section_style))
    summary_data = [
        ["Account Holder", "Demo User (SentiVest)"],
        ["Account Type", "Investec Private Bank Account"],
        ["Current Balance", f"R {balance:,.2f}"],
        ["Total Spent", f"R {total_spent:,.2f}"],
        ["Transactions Processed", str(stats.get("transactions_processed", 0))],
        ["Patterns Detected", str(stats.get("patterns_detected", 0))],
        ["Active Alerts", str(stats.get("alerts_active", 0))],
        ["AI Demo Month", demo_date],
    ]
    t = Table(summary_data, colWidths=[160, 320])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#003B46")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    if doc_id in (1, 2):
        # Statement: show transactions by merchant
        story.append(Paragraph("Transaction Details", section_style))
        if merchant_nodes:
            txn_data = [["Merchant", "Category", "Total Amount", "Txn Count", "Status"]]
            for nid, n in sorted(merchant_nodes, key=lambda x: x[1].attrs.get("total_amount", 0), reverse=True):
                cat = "—"
                for e in kg.edges:
                    if e.source == nid and e.target in kg.nodes and kg.nodes[e.target].type == "category":
                        cat = kg.nodes[e.target].label
                        break
                txn_data.append([
                    n.label[:30],
                    cat,
                    f"R {n.attrs.get('total_amount', 0):,.2f}",
                    str(n.attrs.get("txn_count", 0)),
                    "Active"
                ])
            t2 = Table(txn_data, colWidths=[130, 90, 100, 60, 60])
            t2.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B46")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t2)
        else:
            story.append(Paragraph("No transactions recorded yet. Run demo scenarios to populate.", normal))

        # Spending by category
        story.append(Paragraph("Spending by Category", section_style))
        if category_nodes:
            cat_data = [["Category", "Total Spent", "Transaction Count"]]
            for nid, n in sorted(category_nodes, key=lambda x: x[1].attrs.get("total_amount", 0), reverse=True):
                cat_data.append([n.label, f"R {n.attrs.get('total_amount', 0):,.2f}", str(n.attrs.get("txn_count", 0))])
            t3 = Table(cat_data, colWidths=[160, 140, 120])
            t3.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B46")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F9FA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t3)

    elif doc_id == 3:
        # Tax certificate
        story.append(Paragraph("Tax-Related Information", section_style))
        tax_items = [["Item", "Amount"]]
        total_income = sum(n.attrs.get("amount", 0) for _, n in income_nodes)
        tax_items.append(["Total Income (Recorded)", f"R {total_income:,.2f}"])
        tax_items.append(["Total Expenditure", f"R {total_spent:,.2f}"])
        for nid, n in tax_nodes:
            tax_items.append([n.label, f"R {n.attrs.get('amount', 0):,.2f}"])
        if len(tax_items) == 3:
            tax_items.append(["Estimated Tax (SARS)", f"R {total_income * 0.25:,.2f}"])
        t4 = Table(tax_items, colWidths=[280, 160])
        t4.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t4)

    elif doc_id == 4:
        # Proof of payment
        story.append(Paragraph("Payment Confirmation", section_style))
        story.append(Paragraph("This confirms payment of the following:", normal))
        story.append(Spacer(1, 8))
        pop_data = [
            ["Beneficiary", "Discovery Health"],
            ["Reference", "DH-MED-2025-0241"],
            ["Amount", "R 4,250.00"],
            ["Date", "01 Feb 2025"],
            ["Status", "PAID"],
        ]
        t5 = Table(pop_data, colWidths=[160, 320])
        t5.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t5)

    elif doc_id == 5:
        # Account confirmation
        story.append(Paragraph("Account Confirmation", section_style))
        story.append(Paragraph(
            "This letter confirms that the below-named individual holds an active account with Investec Private Bank.", normal))
        story.append(Spacer(1, 8))
        acc_data = [
            ["Account Holder", "Demo User"],
            ["Account Number", "10-XX-XXXX-7821"],
            ["Branch Code", "580105"],
            ["Account Type", "Private Bank Account"],
            ["Status", "Active"],
            ["Date Opened", "15 Jan 2020"],
        ]
        t6 = Table(acc_data, colWidths=[160, 320])
        t6.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t6)

    # Alerts section (for all doc types)
    if alert_nodes:
        story.append(Paragraph("AI Agent Alerts", section_style))
        alert_data = [["Alert", "Severity", "Details"]]
        for nid, n in alert_nodes[:10]:
            alert_data.append([
                n.label[:40],
                n.attrs.get("severity", "info").upper(),
                n.attrs.get("description", "")[:60]
            ])
        t_alerts = Table(alert_data, colWidths=[160, 80, 200])
        t_alerts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B91C1C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DEE2E6")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_alerts)

    # Patterns section
    if pattern_nodes:
        story.append(Paragraph("Detected Patterns", section_style))
        for nid, n in pattern_nodes:
            story.append(Paragraph(f"<b>{n.label}</b>: {n.attrs.get('description', '')}", normal))

    # Footer
    story.append(Spacer(1, 24))
    story.append(Paragraph("This document was generated by SentiVest AI Banking Agent. For demo purposes only.", small))
    story.append(Paragraph(f"Knowledge Graph: {stats.get('total_nodes', 0)} nodes, {stats.get('total_edges', 0)} edges | Generated {datetime.now().strftime('%d %b %Y %H:%M:%S')}", small))

    doc.build(story)
    buf.seek(0)

    filename = f"SentiVest_{title.replace(' ', '_')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ==================== Tasks ====================

DEMO_TASKS = [
    {"id": 1, "text": "Review Takealot R12,399 charge", "priority": "high", "done": False,
     "due": "Today", "source": "AI Agent"},
    {"id": 2, "text": "Cancel Netflix trial if unused", "priority": "medium", "done": False,
     "due": "This week", "source": "Pattern Detection"},
    {"id": 3, "text": "Dispute City Power R2,847 spike", "priority": "high", "done": False,
     "due": "Today", "source": "Anomaly Detection"},
    {"id": 4, "text": "Transfer R3,000 to savings", "priority": "low", "done": False,
     "due": "Payday", "source": "Goal Tracker"},
]

@app.get("/api/tasks")
async def get_tasks():
    return {"tasks": DEMO_TASKS}

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, body: dict = Body(...)):
    for task in DEMO_TASKS:
        if task["id"] == task_id:
            task.update(body)
            await log_event("action", f"Task updated: {task['text']} -> {'done' if task.get('done') else 'pending'}")
            return task
    return {"error": "Task not found"}

@app.post("/api/tasks")
async def create_task(body: dict = Body(...)):
    new_task = {
        "id": len(DEMO_TASKS) + 1,
        "text": body.get("text", "New task"),
        "priority": body.get("priority", "medium"),
        "done": False,
        "due": body.get("due", "This week"),
        "source": body.get("source", "Manual")
    }
    DEMO_TASKS.append(new_task)
    await log_event("action", f"Task created: {new_task['text']}")
    return new_task


# ==================== Voice ====================

@app.post("/api/voice")
async def handle_voice(body: dict = Body(...)):
    text = body.get("text", "")
    result = await voice.route(text)
    cmd = result.get("command", "unknown")
    await log_event("process", f"Voice: '{text}' -> {cmd}")
    # If an action modified the KG, broadcast graph update
    action = result.get("action")
    if action and action.get("type") in ("kg_updated", "card_frozen", "account_switched"):
        await manager.broadcast({
            "type": "graph_update", "graph": kg.visualize(),
            "stats": kg.get_stats(), "accounts": kg.list_accounts(),
            "balance": kg.get_balance(),
        })
    return result


@app.get("/api/voice/history")
async def get_voice_history():
    return {"history": voice.get_history()}


@app.post("/api/voice/clear")
async def clear_voice_history():
    voice.clear_history()
    return {"status": "ok"}


@app.get("/api/voice/memory")
async def get_voice_memory():
    return {
        "facts": voice._memory["facts"],
        "preferences": voice._memory["preferences"],
        "summary": voice._memory["summary"],
        "conversation_count": len(voice._memory["conversations"]),
    }


@app.post("/api/voice/memory/update")
async def update_voice_memory(req: Request):
    data = await req.json()
    if "facts" in data:
        voice._memory["facts"] = data["facts"]
    if "preferences" in data:
        voice._memory["preferences"] = data["preferences"]
    voice._save_memory()
    return {"ok": True, "facts": len(voice._memory["facts"])}


@app.get("/api/beneficiaries")
async def get_beneficiaries():
    return {"beneficiaries": kg.get_beneficiaries()}

@app.get("/api/beneficiaries/search")
async def search_beneficiaries(q: str = ""):
    if not q:
        return {"matches": kg.get_beneficiaries()}
    return {"matches": kg.find_beneficiary(q)}

@app.post("/api/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio from browser MediaRecorder using Google STT."""
    import speech_recognition as sr
    from pydub import AudioSegment

    audio_data = await audio.read()
    fname = audio.filename or "recording.wav"
    header_hex = audio_data[:16].hex(' ') if len(audio_data) >= 16 else "too short"
    print(f"[Transcribe] Received {len(audio_data)} bytes, file={fname}, header: {header_hex}")

    ext = fname.rsplit('.', 1)[-1] if '.' in fname else 'wav'
    wav_path = None

    try:
        # If already WAV, use directly; otherwise convert via pydub/ffmpeg
        if ext == 'wav' and audio_data[:4] == b'RIFF':
            # Browser sent raw WAV — may need resampling to 16kHz for STT
            from pydub import AudioSegment
            import io
            audio_seg = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
            audio_seg = audio_seg.set_frame_rate(16000).set_channels(1)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_seg.export(tmp.name, format="wav")
                wav_path = tmp.name
            duration_ms = len(audio_seg)
            dbfs = audio_seg.dBFS
            print(f"[Transcribe] WAV direct: {duration_ms}ms, resampled 16kHz, dBFS={dbfs:.1f}")
        else:
            # Non-WAV: save and convert via ffmpeg
            from pydub import AudioSegment
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                tmp.write(audio_data)
                src_path = tmp.name
            audio_seg = AudioSegment.from_file(src_path)
            audio_seg = audio_seg.set_frame_rate(16000).set_channels(1)
            wav_path = src_path.rsplit('.', 1)[0] + ".wav"
            audio_seg.export(wav_path, format="wav")
            duration_ms = len(audio_seg)
            dbfs = audio_seg.dBFS
            print(f"[Transcribe] Converted {ext}→wav: {duration_ms}ms, dBFS={dbfs:.1f}")
            try: os.unlink(src_path)
            except: pass

        if dbfs < -50:
            print(f"[Transcribe] WARNING: Audio very quiet (dBFS={dbfs:.1f})")
        if duration_ms < 500:
            return {"text": "", "success": False, "error": "Recording too short"}

        # Transcribe with Google STT
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        with sr.AudioFile(wav_path) as source:
            audio_rec = recognizer.record(source)
        text = recognizer.recognize_google(audio_rec, language="en-ZA")
        print(f"[Transcribe] Result: '{text}'")
        return {"text": text, "success": True}
    except sr.UnknownValueError:
        print(f"[Transcribe] No speech detected")
        return {"text": "", "success": False, "error": "No speech detected — try speaking louder or longer"}
    except sr.RequestError as e:
        print(f"[Transcribe] STT service error: {e}")
        return {"text": "", "success": False, "error": f"STT service error: {str(e)}"}
    except Exception as e:
        print(f"[Transcribe] Error: {e}")
        return {"text": "", "success": False, "error": str(e)}
    finally:
        if wav_path:
            try: os.unlink(wav_path)
            except: pass


# ==================== Chat ====================

@app.post("/api/chat")
async def handle_chat(body: dict = Body(...)):
    text = body.get("text", body.get("message", ""))
    ctx = model.build_graph_context(kg)

    # First query the KG
    kg_result = kg.query(text)

    # Then generate AI response
    ai_response = await model.generate_chat_response(text, ctx)

    # Use KG result text if AI is using templates (more specific)
    response_text = kg_result.get("text", ai_response)

    await log_event("process", f"Chat: '{text[:50]}...' -> {kg_result.get('intent', 'unknown')}")

    return {
        "response": response_text,
        "intent": kg_result.get("intent", "unknown"),
        "data": kg_result.get("data", {}),
        "ai_response": ai_response
    }


# ==================== Receipt Scanner ====================

SCAN_RESULTS = [
    {"merchant": "Woolworths Food", "category": "Groceries", "amount": 348.50,
     "items": ["Milk 2L", "Bread", "Chicken Breast", "Avocados x3", "Rice 2kg"],
     "budget_status": "within", "match_status": "matched"},
    {"merchant": "Vida e Caffè", "category": "Coffee", "amount": 89.00,
     "items": ["Flat White", "Almond Croissant"],
     "budget_status": "over", "match_status": "new"},
    {"merchant": "Dis-Chem", "category": "Health", "amount": 456.30,
     "items": ["Vitamins", "Sunscreen SPF50", "First Aid Kit"],
     "budget_status": "within", "match_status": "new"},
]

@app.post("/api/scan")
async def scan_receipt():
    result = random.choice(SCAN_RESULTS)
    await log_event("process", f"Receipt scanned: {result['merchant']} R{result['amount']:,.2f}")
    return result


# ==================== Status ====================

@app.get("/api/status")
async def get_status():
    return {
        "api": investec.status(),
        "model": model.status(),
        "graph": kg.get_stats(),
        "websocket": {"connections": len(manager.connections)}
    }


# ==================== Model Status ====================

@app.get("/api/model/status")
async def model_status():
    return model.status()


# ==================== Demo Steps ====================

DEMO_STEPS = {
    "monthly_cycle": [
        {"id": "salary", "title": "Receive Salary", "icon": "💰",
         "description": "Monthly salary from ACME Corp", "repeatable": True},
        {"id": "debit_orders", "title": "Debit Orders Run", "icon": "🏦",
         "description": "Insurance, loans, telecom processed", "repeatable": True},
        {"id": "daily_spending", "title": "Daily Spending", "icon": "🛒",
         "description": "Groceries, fuel, coffee, transport", "repeatable": True},
        {"id": "food_delivery", "title": "Food Delivery", "icon": "🍔",
         "description": "Uber Eats, Mr D — habit grows", "repeatable": True},
    ],
    "life_events": [
        {"id": "suspicious", "title": "Suspicious Transaction", "icon": "🚨",
         "description": "Unknown merchant at 2:47 AM", "repeatable": False},
        {"id": "bonus", "title": "Bonus Season", "icon": "🎉",
         "description": "13th cheque or performance bonus", "repeatable": False},
        {"id": "emergency", "title": "Emergency Expense", "icon": "🚑",
         "description": "Burst pipe or medical emergency", "repeatable": False},
        {"id": "tax_refund", "title": "Tax Refund", "icon": "🧾",
         "description": "SARS refund hits your account", "repeatable": False},
        {"id": "salary_increase", "title": "Promotion", "icon": "📈",
         "description": "Salary R42,500 → R55,000", "repeatable": False},
        {"id": "international_trip", "title": "International Trip", "icon": "✈️",
         "description": "Forex transactions in EUR/GBP", "repeatable": False},
        {"id": "car_accident", "title": "Car Accident", "icon": "🚗",
         "description": "Insurance claim + excess payment", "repeatable": False},
    ],
    "setup": [
        {"id": "budgets", "title": "Set Budgets", "icon": "📊",
         "description": "Create spending limits", "repeatable": False},
        {"id": "investments", "title": "Investment Portfolio", "icon": "📈",
         "description": "ETFs, shares, tax-free savings", "repeatable": False},
        {"id": "goals", "title": "Financial Goals", "icon": "🎯",
         "description": "Emergency fund & holiday savings", "repeatable": False},
    ]
}

# ==================== Data Generation ====================

DAILY_SPENDING_POOLS = {
    "groceries": [("Woolworths Food", "Groceries", "🛒"), ("Checkers", "Groceries", "🛒"),
                  ("Pick n Pay", "Groceries", "🛒"), ("Shoprite", "Groceries", "🛒"),
                  ("Spar", "Groceries", "🛒"), ("Food Lovers", "Groceries", "🛒")],
    "fuel": [("Shell Garage N1", "Fuel", "⛽"), ("Engen", "Fuel", "⛽"),
             ("BP Sandton", "Fuel", "⛽"), ("Caltex", "Fuel", "⛽")],
    "coffee": [("Vida e Caffe", "Coffee", "☕"), ("Starbucks", "Coffee", "☕")],
    "health": [("Dis-Chem", "Health", "💊"), ("Clicks", "Health", "💊")],
    "transport": [("Uber", "Transport", "🚕"), ("Bolt", "Transport", "🚕"),
                  ("Gautrain", "Transport", "🚄")],
    "dining": [("Spur", "Dining", "🍽️"), ("Ocean Basket", "Dining", "🍽️"),
               ("Wimpy", "Dining", "🍽️")],
}

FOOD_DELIVERY_POOL = [("Uber Eats", "🍔"), ("Mr D Food", "🍕"), ("KFC", "🍗"),
                      ("Nandos", "🍗"), ("Debonairs", "🍕"), ("Steers", "🍔")]


def _gen_daily_spending(month: int):
    random.seed(month * 7 + 42)
    txns = []
    for _ in range(random.randint(2, 3)):
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["groceries"])
        txns.append((m, round(random.uniform(450, 1200), 2), c,
                     f"{random.randint(7,11):02d}:{random.randint(0,59):02d}", icon))
    for _ in range(random.randint(1, 2)):
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["fuel"])
        txns.append((m, round(random.uniform(800, 1400), 2), c,
                     f"{random.randint(7,17):02d}:{random.randint(0,59):02d}", icon))
    for _ in range(random.randint(1, 3)):
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["coffee"])
        txns.append((m, round(random.uniform(55, 110), 2), c,
                     f"0{random.randint(7,9)}:{random.randint(0,59):02d}", icon))
    if random.random() > 0.4:
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["health"])
        txns.append((m, round(random.uniform(150, 600), 2), c, "11:15", icon))
    for _ in range(random.randint(1, 2)):
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["transport"])
        txns.append((m, round(random.uniform(60, 200), 2), c,
                     f"{random.randint(7,18):02d}:{random.randint(0,59):02d}", icon))
    if random.random() > 0.5:
        m, c, icon = random.choice(DAILY_SPENDING_POOLS["dining"])
        txns.append((m, round(random.uniform(200, 500), 2), c, "13:00", icon))
    return txns


def _gen_food_delivery(month: int):
    random.seed(month * 13 + 99)
    count = min(4 + month, 10)
    txns = []
    for _ in range(count):
        m, icon = random.choice(FOOD_DELIVERY_POOL)
        amt = round(random.uniform(150, 400) * (1 + month * 0.05), 2)
        txns.append((m, amt, "Food Delivery",
                     f"{random.randint(18,22):02d}:{random.randint(0,59):02d}", icon))
    return txns


def _gen_freelance_amount(month: int) -> float:
    random.seed(month * 31 + 7)
    return round(random.uniform(3000, 8000), 2)


@app.get("/api/demo/steps")
async def get_demo_steps():
    return {"steps": DEMO_STEPS, "demo_info": kg.get_demo_info()}


@app.get("/api/demo/info")
async def demo_info():
    return kg.get_demo_info()


@app.post("/api/demo/reset")
async def demo_reset():
    """Reset KG and all demo state."""
    kg.reset()
    if hasattr(kg, '_salary_current'):
        del kg._salary_current
    await log_event("system", "Knowledge graph reset — starting fresh (Month 0)")
    return {"status": "reset", "stats": kg.get_stats(), "demo_info": kg.get_demo_info()}


@app.post("/api/demo/step")
async def demo_step(body: dict = Body(...)):
    """Execute a demo step. Repeatable steps advance month and vary data."""
    step_id = body.get("step", "")
    current_month = kg.demo_month

    # ===== REPEATABLE MONTHLY CYCLE =====

    if step_id == "salary":
        press = kg.step_counts["salary"]
        kg.step_counts["salary"] += 1
        salary_amount = getattr(kg, '_salary_current', 42500)
        freelance = _gen_freelance_amount(press) if press >= 1 else 5000
        interest = round(285 + press * 12, 2)

        kg.add_income("ACME Corp Salary", salary_amount, "monthly", "salary")
        kg.add_income("Freelance Dev", freelance, "monthly", "freelance")
        kg.add_income("FNB Interest", interest, "monthly", "interest")

        # Record income in transaction ledger (also updates kg.balance)
        kg.record_income("ACME Corp Salary", salary_amount, "salary", "06:00", "💰")
        kg.record_income("Freelance Dev", freelance, "freelance", "10:00", "💻")
        kg.record_income("FNB Interest", interest, "interest", "00:01", "🏦")

        kg.salary_history.append({"month": current_month, "source": "ACME Corp Salary", "amount": salary_amount})
        if press >= 1:
            kg.salary_history.append({"month": current_month, "source": "Freelance Dev", "amount": freelance})

        kg.nodes["user"].attrs["balance"] = kg.balance
        kg.nodes["user"].attrs["available"] = kg.available

        kg._detect_recurring_income()
        kg.advance_month()

        await log_event("safe", f"Month {press + 1}: Salary R{salary_amount:,.2f}")
        if press >= 1:
            await log_event("info", f"Freelance: R{freelance:,.2f} (varies monthly)")
        if press >= 2:
            await log_event("process", "AI pattern detected: Recurring salary income")

        return {"step": step_id, "press": press + 1,
                "message": f"Month {press + 1} income — R{salary_amount + freelance + interest:,.2f}",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "💰", "text": f"Month {press + 1}: Salary R{salary_amount:,.0f}" +
                             (f" + Freelance R{freelance:,.0f}" if press >= 1 else ""), "type": "safe"},
                    "txns": [
                        {"merchant": "ACME Corp Salary", "amount": -salary_amount, "category": "Income",
                         "time": "06:00", "icon": "💰", "verdict": "SAFE"},
                        {"merchant": "Freelance Dev", "amount": -freelance, "category": "Income",
                         "time": "10:00", "icon": "💻", "verdict": "SAFE"},
                        {"merchant": "FNB Interest", "amount": -interest, "category": "Income",
                         "time": "00:01", "icon": "🏦", "verdict": "SAFE"},
                    ],
                    "balance": total_income
                }}

    elif step_id == "debit_orders":
        press = kg.step_counts["debit_orders"]
        kg.step_counts["debit_orders"] += 1

        debits = [
            ("Discovery Health", 4200, "Insurance", "🏥"),
            ("Outsurance", 1847, "Insurance", "🛡️"),
            ("Old Mutual", 650, "Insurance", "🛡️"),
            ("Home Loan", 16847, "Loan Repayment", "🏠"),
            ("Car Finance", 6333, "Loan Repayment", "🚗"),
            ("Vodacom", 599, "Telecom", "📱"),
        ]

        if press == 0:
            kg.add_insurance("Discovery", "health", 4200, 5000000)
            kg.add_insurance("Outsurance", "car", 1847, 350000)
            kg.add_insurance("Old Mutual", "life", 650, 2000000)
            kg.add_loan("Home Loan", 1800000, 11.75, 240, 1650000, "mortgage")
            kg.add_loan("Car Finance", 350000, 12.5, 60, 280000, "vehicle")
            kg.add_loan("Personal Loan", 50000, 18.0, 36, 35000, "personal")

        for m, a, c, icon in debits:
            kg.ingest_transaction(m, a, c, "01:00", "low", month=current_month)
            kg.debit_order_history.append({"month": current_month, "merchant": m, "amount": a})

        total = sum(a for _, a, _, _ in debits)
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance

        kg._detect_debit_order_pattern()

        await log_event("action", f"Month {press + 1}: Debit orders R{total:,.0f}")
        if press >= 1:
            await log_event("info", f"Subscription detection: {len(debits)} consistent charges")

        return {"step": step_id, "press": press + 1,
                "message": f"Month {press + 1}: {len(debits)} debits — R{total:,.0f}",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🏦", "text": f"Debit orders: R{total:,.0f} (month {press + 1})", "type": "info"},
                    "txns": [{"merchant": m, "amount": a, "category": c, "time": "01:00",
                             "icon": icon, "verdict": "SAFE"} for m, a, c, icon in debits],
                    "balance": -total
                }}

    elif step_id == "daily_spending":
        press = kg.step_counts["daily_spending"]
        kg.step_counts["daily_spending"] += 1

        txns = _gen_daily_spending(press)
        for m, a, c, t, icon in txns:
            kg.ingest_transaction(m, a, c, t, "low", month=current_month)

        total = sum(a for _, a, _, _, _ in txns)
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance

        await log_event("safe", f"Month {press + 1}: {len(txns)} transactions — R{total:,.2f}")

        return {"step": step_id, "press": press + 1,
                "message": f"Month {press + 1}: R{total:,.2f} across {len(txns)} merchants",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🛒", "text": f"{len(txns)} transactions — R{total:,.0f} (month {press + 1})", "type": "info"},
                    "txns": [{"merchant": m, "amount": a, "category": c, "time": t,
                             "icon": icon, "verdict": "SAFE"} for m, a, c, t, icon in txns],
                    "balance": 0  # balance updates come via WebSocket from KG
                }}

    elif step_id == "food_delivery":
        press = kg.step_counts["food_delivery"]
        kg.step_counts["food_delivery"] += 1

        txns = _gen_food_delivery(press)
        for m, a, c, t, icon in txns:
            kg.ingest_transaction(m, a, c, t, "low", month=current_month)

        total = sum(a for _, a, _, _, _ in txns)
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance

        await log_event("warning", f"Month {press + 1}: {len(txns)} food orders — R{total:,.2f}")
        if press >= 2:
            await log_event("process", f"Escalation: food orders increasing ({4 + press - 1} → {len(txns)})")

        return {"step": step_id, "press": press + 1,
                "message": f"Month {press + 1}: {len(txns)} food orders — R{total:,.2f}",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🍔", "text": f"{len(txns)} orders — R{total:,.0f} (escalating!)", "type": "warning"},
                    "txns": [{"merchant": m, "amount": a, "category": c, "time": t,
                             "icon": icon, "verdict": "SAFE"} for m, a, c, t, icon in txns],
                    "balance": 0
                }}

    # ===== ONE-SHOT LIFE EVENTS =====

    elif step_id == "suspicious":
        kg.ingest_transaction("UNKNOWN_MERCH_ZW", 4500, "Unknown", "02:47", "critical")
        alert_id = "alert_fraud_unknown_merch_zw"
        kg._add_node(alert_id, "Suspicious Transaction Blocked", "alert", {
            "severity": "critical", "merchant": "UNKNOWN_MERCH_ZW",
            "amount": 4500, "time": "02:47",
            "reason": "Unknown merchant, late-night, Zimbabwe origin"
        })
        kg._add_edge("user", alert_id, "ALERTED_BY")
        kg._notify_change()
        await log_event("critical", "BLOCKED: UNKNOWN_MERCH_ZW R4,500 at 02:47 — card frozen")
        await log_event("warning", "Anomaly score: 0.85 — unknown merchant + late night + foreign")
        return {"step": step_id, "message": "Suspicious transaction blocked — card frozen",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🚨", "text": "BLOCKED: Unknown merchant R4,500 — card frozen!", "type": "critical", "duration": 5000},
                    "txns": [{"merchant": "UNKNOWN_MERCH_ZW", "amount": 4500, "category": "Unknown",
                             "time": "02:47", "icon": "🚨", "verdict": "BLOCK"}],
                    "balance": 0, "cardFrozen": True, "page": "alerts"
                }}

    elif step_id == "bonus":
        bonus_amount = 42500
        kg.add_income("ACME Corp Bonus", bonus_amount, "annually", "bonus")
        kg.record_income("ACME Corp Bonus", bonus_amount, "bonus", "06:00", "🎉")
        kg.nodes["user"].attrs["balance"] = kg.balance
        kg.ingest_transaction("Canal Walk Shopping", 3500, "Shopping", "14:00", "low")
        kg.ingest_transaction("Woolworths Food", 2100, "Groceries", "16:30", "low")
        kg._notify_change()
        await log_event("safe", f"13th cheque received: R{bonus_amount:,.2f}")
        await log_event("warning", "Post-bonus spending spike detected: R5,600 in first 24hrs")
        return {"step": step_id, "message": f"Bonus R{bonus_amount:,.2f} — spending spike detected",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🎉", "text": f"13th cheque: R{bonus_amount:,.0f}!", "type": "safe", "duration": 4000},
                    "txns": [
                        {"merchant": "ACME Corp Bonus", "amount": -bonus_amount, "category": "Income",
                         "time": "06:00", "icon": "🎉", "verdict": "SAFE"},
                        {"merchant": "Canal Walk Shopping", "amount": 3500, "category": "Shopping",
                         "time": "14:00", "icon": "🛍️", "verdict": "SAFE"},
                        {"merchant": "Woolworths Food", "amount": 2100, "category": "Groceries",
                         "time": "16:30", "icon": "🛒", "verdict": "SAFE"},
                    ],
                    "balance": 0
                }}

    elif step_id == "emergency":
        random.seed(kg.demo_month + 77)
        is_medical = random.random() > 0.5
        if is_medical:
            merchant, amount, desc = "Netcare Hospital", 8500, "Medical emergency"
            icon_emoji = "🏥"
        else:
            merchant, amount, desc = "PlumbCo Emergency", 15000, "Burst pipe repair"
            icon_emoji = "🔧"
        kg.ingest_transaction(merchant, amount, "Emergency", "09:30", "high")
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance
        alert_id = f"alert_emergency_{merchant.lower().replace(' ', '_')}"
        kg._add_node(alert_id, f"Emergency: {desc}", "alert", {
            "severity": "warning", "amount": amount, "type": "emergency",
            "impact": f"Balance dropped by R{amount:,.0f}"
        })
        kg._add_edge("user", alert_id, "ALERTED_BY")
        kg._notify_change()
        await log_event("critical", f"Emergency: {desc} — R{amount:,.0f}")
        await log_event("warning", f"Balance impact: -R{amount:,.0f}")
        return {"step": step_id, "message": f"{desc}: R{amount:,.0f}",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": icon_emoji, "text": f"{desc}: R{amount:,.0f}", "type": "critical", "duration": 5000},
                    "txns": [{"merchant": merchant, "amount": amount, "category": "Emergency",
                             "time": "09:30", "icon": icon_emoji, "verdict": "ALERT"}],
                    "balance": -amount, "page": "alerts"
                }}

    elif step_id == "tax_refund":
        refund = 12400
        kg.add_income("SARS Tax Refund", refund, "annually", "tax_refund")
        kg.record_income("SARS Tax Refund", refund, "tax_refund", "10:00", "🧾")
        kg.nodes["user"].attrs["balance"] = kg.balance
        kg.add_tax_item("SARS Refund 2025", refund, "refund", "tax_refund")
        kg._notify_change()
        await log_event("safe", f"SARS tax refund: R{refund:,.2f}")
        await log_event("info", "AI suggests: Transfer R10,000 to emergency fund")
        return {"step": step_id, "message": f"Tax refund R{refund:,.2f} received",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🧾", "text": f"SARS refund: R{refund:,.0f}!", "type": "safe"},
                    "txns": [{"merchant": "SARS Tax Refund", "amount": -refund, "category": "Income",
                             "time": "10:00", "icon": "🧾", "verdict": "SAFE"}],
                    "balance": refund
                }}

    elif step_id == "salary_increase":
        old_salary = getattr(kg, '_salary_current', 42500)
        new_salary = 55000
        kg._salary_current = new_salary
        kg.salary = new_salary
        kg.nodes["user"].attrs["salary"] = new_salary
        iid = "income_acme_corp_salary"
        if iid in kg.nodes:
            kg.nodes[iid].attrs["amount"] = new_salary
            kg.nodes[iid].attrs["annual"] = new_salary * 12
            kg.nodes[iid].attrs["previous_amount"] = old_salary
        kg._notify_change()
        increase = new_salary - old_salary
        await log_event("safe", f"Promotion! Salary R{old_salary:,.0f} → R{new_salary:,.0f}")
        await log_event("info", f"Extra R{increase:,.0f}/month — AI recommends: R8K savings, R4.5K lifestyle")
        return {"step": step_id, "message": f"Salary increased to R{new_salary:,.0f} (+R{increase:,.0f})",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "📈", "text": f"Promotion! R{old_salary:,.0f} → R{new_salary:,.0f}", "type": "safe", "duration": 4000},
                    "txns": [], "balance": 0
                }}

    elif step_id == "international_trip":
        forex_txns = [
            ("Amsterdam Hotel", 3200, "Travel", "14:00", "🏨"),
            ("Schiphol Duty Free", 1800, "Shopping", "08:30", "🛍️"),
            ("Paris Restaurant", 950, "Dining", "20:00", "🍷"),
            ("Uber Paris", 280, "Transport", "22:15", "🚕"),
            ("London Hostel", 2400, "Travel", "16:00", "🏨"),
            ("Heathrow Shopping", 1500, "Shopping", "09:00", "🛍️"),
        ]
        for m, a, c, t, icon in forex_txns:
            kg.ingest_transaction(m, a, c, t, "low")
        kg._add_node("forex_eur_zar", "EUR/ZAR", "forex", {"rate": 20.15, "transactions": 4})
        kg._add_node("forex_gbp_zar", "GBP/ZAR", "forex", {"rate": 23.80, "transactions": 2})
        kg._add_edge("user", "forex_eur_zar", "TRADED")
        kg._add_edge("user", "forex_gbp_zar", "TRADED")
        total = sum(a for _, a, _, _, _ in forex_txns)
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance
        kg._notify_change()
        await log_event("info", f"International trip: {len(forex_txns)} forex transactions — R{total:,.0f}")
        await log_event("warning", "Multiple currencies detected: EUR, GBP — anomaly alerts may fire")
        return {"step": step_id, "message": f"Trip: {len(forex_txns)} transactions in EUR/GBP — R{total:,.0f}",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "✈️", "text": f"Trip spending: R{total:,.0f} across EUR/GBP", "type": "info"},
                    "txns": [{"merchant": m, "amount": a, "category": c, "time": t,
                             "icon": icon, "verdict": "SAFE"} for m, a, c, t, icon in forex_txns],
                    "balance": 0
                }}

    elif step_id == "car_accident":
        excess = 5000
        repair_estimate = 45000
        kg.ingest_transaction("Outsurance Excess", excess, "Insurance", "10:00", "high")
        claim_id = "insurance_claim_car"
        kg._add_node(claim_id, "Car Insurance Claim", "insurance", {
            "type": "claim", "status": "submitted", "excess_paid": excess,
            "repair_estimate": repair_estimate, "provider": "Outsurance",
            "date": kg.get_demo_date_str()
        })
        kg._add_edge("user", claim_id, "FILED_CLAIM")
        if "insurance_outsurance_car" in kg.nodes:
            kg._add_edge(claim_id, "insurance_outsurance_car", "CLAIM_AGAINST")
        # balance already updated by ingest_transaction
        kg.nodes["user"].attrs["balance"] = kg.balance
        kg._notify_change()
        await log_event("critical", f"Car accident: Excess R{excess:,.0f} paid, claim R{repair_estimate:,.0f}")
        await log_event("info", "Outsurance claim filed — 5-7 business days for assessment")
        return {"step": step_id, "message": f"Accident: R{excess:,.0f} excess, R{repair_estimate:,.0f} claim",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🚗", "text": f"Accident: Excess R{excess:,.0f}, claim R{repair_estimate:,.0f}", "type": "critical", "duration": 5000},
                    "txns": [{"merchant": "Outsurance Excess", "amount": excess, "category": "Insurance",
                             "time": "10:00", "icon": "🚗", "verdict": "ALERT"}],
                    "balance": -excess, "page": "alerts"
                }}

    # ===== SETUP STEPS =====

    elif step_id == "budgets":
        kg.add_budget("Food Delivery", 500, "week")
        kg.add_budget("Groceries", 3500, "month")
        kg.add_budget("Fuel", 2500, "month")
        kg.add_budget("Shopping", 5000, "month")
        kg.add_budget("Coffee", 300, "month")
        alerts = []
        for b in kg.get_budgets():
            if b["status"] == "OVER":
                alerts.append(f"{b['category']} R{b['spent']:,.0f}/R{b['limit']:,.0f}")
        await log_event("action", "5 budgets created — spending limits active")
        if alerts:
            await log_event("warning", f"Already over budget: {', '.join(alerts)}")
        return {"step": step_id, "message": f"5 budgets set — {len(alerts)} exceeded",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "📊", "text": "5 budgets created", "type": "safe"},
                    "txns": [], "balance": 0, "page": "budgets", "refreshBudgets": True
                }}

    elif step_id == "investments":
        kg.add_investment("Satrix Top 40 ETF", 150000, 172500, "etf")
        kg.add_investment("Capitec Shares", 25000, 31200, "equity")
        kg.add_investment("Tax-Free Savings", 80000, 92000, "tax_free")
        kg.add_tax_item("Employment Income", 510000, "income", "employment")
        kg.add_tax_item("Interest Income", 3420, "income", "interest")
        kg.add_tax_item("Medical Aid Credits", 50400, "deduction", "medical")
        kg.add_tax_item("Retirement Annuity", 36000, "deduction", "retirement")
        await log_event("info", "Portfolio: R295,700 across 3 positions (+R40,700 gains)")
        return {"step": step_id, "message": "Investment portfolio and tax data mapped",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "📈", "text": "Portfolio: R295,700 (+R40,700 gains)", "type": "safe"},
                    "txns": [], "balance": 0
                }}

    elif step_id == "goals":
        kg.add_goal("Emergency Fund", 50000, 3000)
        kg.add_goal("Zanzibar Holiday", 25000, 2500)
        kg.ingest_transaction("Takealot.com", 12399, "Shopping", "14:22", "high")
        await log_event("action", "Goal: Emergency Fund R50,000 (17mo at R3,000/mo)")
        await log_event("action", "Goal: Zanzibar Holiday R25,000 (10mo at R2,500/mo)")
        return {"step": step_id, "message": "Goals set with AI timeline predictions",
                "stats": kg.get_stats(), "demo_info": kg.get_demo_info(),
                "phone_data": {
                    "toast": {"icon": "🎯", "text": "Goals set — Emergency Fund 17mo, Holiday 10mo", "type": "info"},
                    "txns": [{"merchant": "Takealot.com", "amount": 12399, "category": "Shopping",
                             "time": "14:22", "icon": "🛍️", "verdict": "FLAG"}],
                    "balance": -12399
                }}

    return {"error": f"Unknown step: {step_id}"}


# ==================== Simulator ====================

async def _simulator_event(event_type: str, data: dict):
    """Handle events from the life simulator — broadcast to all WS clients."""
    if event_type == "transaction":
        toast = data.get("toast")
        if toast:
            await log_event(
                "critical" if data.get("verdict") == "BLOCK" else
                "warning" if data.get("verdict") in ("ALERT", "FLAG") else "safe",
                toast
            )
        await broadcast_graph_update()

    elif event_type == "alert":
        await log_event("critical", data.get("toast", "Alert triggered"))
        await manager.broadcast({
            "type": "sim_alert",
            "alert": data,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
        await broadcast_graph_update()

    elif event_type == "phase":
        phase = data.get("phase", "")
        day = data.get("day", 0)
        month_str = data.get("month", kg.get_demo_date_str())
        await log_event("process", f"Sim: {phase.replace('_', ' ').title()} (Day {day}, {month_str})")
        await manager.broadcast({
            "type": "sim_phase",
            "phase": phase, "day": day, "month": month_str,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    elif event_type == "insights":
        insights = data.get("insights", [])
        for insight in insights:
            sev = insight.get("severity", "info")
            log_type = "critical" if sev == "critical" else "warning" if sev == "warning" else "info"
            await log_event(log_type, f"AI Insight: {insight['title']} - {insight['body']}")
        await manager.broadcast({
            "type": "sim_insights",
            "insights": insights,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })

    elif event_type == "health_score":
        await manager.broadcast({
            "type": "health_score",
            "health": data,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        })


# Wire up simulator events
simulator.on_event = _simulator_event


@app.post("/api/simulator/start")
async def sim_start(body: dict = Body({})):
    speed = float(body.get("speed", 1.0))
    result = await simulator.start(speed)
    await log_event("system", f"Life simulator started (speed: {speed}x)")
    return result


@app.post("/api/simulator/stop")
async def sim_stop():
    result = await simulator.stop()
    await log_event("system", f"Simulator stopped after {result['months_simulated']} months")
    return result


@app.post("/api/simulator/speed")
async def sim_speed(body: dict = Body(...)):
    speed = float(body.get("speed", 1.0))
    result = simulator.set_speed(speed)
    return result


@app.get("/api/simulator/status")
async def sim_status():
    return simulator.status()


# ==================== Financial Health ====================

@app.get("/api/health")
async def get_health_score():
    return calculate_health_score()


# ==================== Loan Eligibility ====================

@app.post("/api/loan/eligibility")
async def check_loan_eligibility(body: dict = Body(...)):
    amount = float(body.get("amount", 100000))
    term = int(body.get("term_months", 60))
    loan_type = body.get("loan_type", "personal")
    result = assess_loan_eligibility(amount, term, loan_type)
    verdict = result["verdict"]
    await log_event(
        "safe" if verdict == "APPROVED" else "warning" if verdict == "CONDITIONAL" else "critical",
        f"Loan check: R{amount:,.0f} {loan_type} -> {verdict} (DTI {result['new_dti']:.0f}%)"
    )
    return result


# ==================== Smart Transfer ====================

@app.post("/api/transfer")
async def smart_transfer(body: dict = Body(...)):
    from_id = body.get("from", body.get("from_id", kg.active_account_id))
    to_id = body.get("to", body.get("to_id", ""))
    amount = float(body.get("amount", 0))
    reference = body.get("reference", "")

    # Resolve account names to IDs
    for acct in kg.list_accounts():
        if acct["name"].lower() in (to_id or "").lower() or acct["type"].lower() in (to_id or "").lower():
            to_id = acct["id"]
            break
        if acct["name"].lower() in (from_id or "").lower() or acct["type"].lower() in (from_id or "").lower():
            from_id = acct["id"]

    result = execute_transfer(from_id, to_id, amount, reference)
    if result["success"]:
        await log_event("safe", result["message"])
        await broadcast_graph_update()
    else:
        await log_event("warning", f"Transfer failed: {result.get('error', 'Unknown')}")
    return result


# ==================== Proactive Insights ====================

@app.get("/api/insights")
async def get_insights():
    return {"insights": _generate_insights()}


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    import sys

    host = "0.0.0.0"
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    # HTTP on localhost — getUserMedia works (localhost is a secure context)
    # HTTPS with self-signed certs can cause Brave/Chrome to silently mute mic streams
    use_https = "--https" in sys.argv
    cert_file = os.path.join(os.path.dirname(__file__), "cert.pem")
    key_file = os.path.join(os.path.dirname(__file__), "key.pem")

    if use_https and os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"\n  HTTPS enabled — open https://localhost:{port}\n")
        uvicorn.run("main:app", host=host, port=port, reload=True,
                     ssl_certfile=cert_file, ssl_keyfile=key_file)
    else:
        print(f"\n  HTTP mode — open http://localhost:{port}")
        print(f"  (Mic works on localhost — it's a secure context)\n")
        uvicorn.run("main:app", host=host, port=port, reload=True)
