import requests
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import HTMLResponse
import os
# ================= CONFIG =================

MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")
DEALS_BOARD_ID = 5027110078
WORK_BOARD_ID = 5027110147

app = FastAPI()

# ================= MONDAY FETCH =================

def fetch_board_data(board_id):
    url = "https://api.monday.com/v2"

    query = f"""
    query {{
      boards(ids: {board_id}) {{
        items_page {{
          items {{
            name
            column_values {{
              column {{
                title
              }}
              text
            }}
          }}
        }}
      }}
    }}
    """

    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json={"query": query}, headers=headers)
    data = response.json()

    items = data["data"]["boards"][0]["items_page"]["items"]

    rows = []
    for item in items:
        row = {"Deal Name": item["name"]}
        for col in item["column_values"]:
            row[col["column"]["title"]] = col["text"]
        rows.append(row)

    return pd.DataFrame(rows)

# ================= DATA CLEANING =================

def clean_deals(df):

    # Clean Deal Value
    df["Masked Deal value"] = (
        df["Masked Deal value"]
        .str.replace(",", "", regex=False)
        .replace("", "0")
        .fillna("0")
    )

    df["Masked Deal value"] = pd.to_numeric(
        df["Masked Deal value"],
        errors="coerce"
    ).fillna(0)

    # Map Probability
    prob_map = {
        "High": 0.8,
        "Medium": 0.5,
        "Low": 0.2
    }

    df["Closure Probability Numeric"] = (
        df["Closure Probability"]
        .map(prob_map)
        .fillna(0.3)
    )

    # Weighted Revenue
    df["Weighted Value"] = (
        df["Masked Deal value"] *
        df["Closure Probability Numeric"]
    )

    return df


def clean_work_orders(df):

    total_projects = len(df)

    completed = len(
        df[df["Execution Status"] == "Completed"]
    )

    ongoing = len(
        df[df["Execution Status"] == "Ongoing"]
    )

    return {
        "Total Projects": total_projects,
        "Completed Projects": completed,
        "Ongoing Projects": ongoing
    }

# ================= REQUEST MODEL =================

class Question(BaseModel):
    question: str

# ================= MAIN ENDPOINT =================

@app.post("/ask")
def ask_question(q: Question):

    deals_df = fetch_board_data(DEALS_BOARD_ID)
    deals_df = clean_deals(deals_df)

    work_df = fetch_board_data(WORK_BOARD_ID)
    work_metrics = clean_work_orders(work_df)

    question = q.question.lower()

    # ================= METRICS =================
    total_pipeline = deals_df["Masked Deal value"].sum()
    weighted_pipeline = deals_df["Weighted Value"].sum()
    total_deals = len(deals_df)

    high_confidence = len(
        deals_df[deals_df["Closure Probability"] == "High"]
    )

    low_confidence = len(
        deals_df[deals_df["Closure Probability"] == "Low"]
    )

    # ================= INTENT BASED RESPONSES =================

    if "weighted" in question or "forecast" in question:
        return {
            "answer": f"Our weighted revenue forecast is {weighted_pipeline:,.0f}."
        }

    if "high confidence" in question:
        return {
            "answer": f"We currently have {high_confidence} high-confidence deals."
        }

    if "low confidence" in question:
        return {
            "answer": f"We have {low_confidence} low-probability deals, which may impact revenue certainty."
        }

    if "operations" in question or "projects" in question:
        return {
            "answer": f"""
🏭 Operations Overview:

• Total Projects: {work_metrics['Total Projects']}
• Ongoing Projects: {work_metrics['Ongoing Projects']}
• Completed Projects: {work_metrics['Completed Projects']}
"""
        }

    # ================= EXECUTIVE SUMMARY =================

    sector_distribution = deals_df.groupby("Sector/service")["Masked Deal value"].sum()
    top_sector = sector_distribution.idxmax() if len(sector_distribution) > 0 else "N/A"
    top_sector_value = sector_distribution.max() if len(sector_distribution) > 0 else 0

    execution_capacity = work_metrics["Ongoing Projects"]
    execution_risk = "Low"

    if total_deals > execution_capacity * 3:
        execution_risk = "High"
    elif total_deals > execution_capacity * 2:
        execution_risk = "Moderate"

    revenue_quality = "Strong"
    if low_confidence > high_confidence:
        revenue_quality = "Risky"

    executive_summary = f"""
🚀 Executive Business Summary

📈 Sales:
• Total Pipeline: {total_pipeline:,.0f}
• Weighted Forecast: {weighted_pipeline:,.0f}
• Total Deals: {total_deals}

🏭 Operations:
• Ongoing Projects: {work_metrics['Ongoing Projects']}
• Completed Projects: {work_metrics['Completed Projects']}

📊 Insights:
• Largest Revenue Sector: {top_sector} ({top_sector_value:,.0f})
• Revenue Quality: {revenue_quality}
• Execution Risk: {execution_risk}
"""

    return {"answer": executive_summary}

    deals_df = fetch_board_data(DEALS_BOARD_ID)
    deals_df = clean_deals(deals_df)

    work_df = fetch_board_data(WORK_BOARD_ID)
    work_metrics = clean_work_orders(work_df)

    question = q.question.lower()

    # ================= METRICS =================
    total_pipeline = deals_df["Masked Deal value"].sum()
    weighted_pipeline = deals_df["Weighted Value"].sum()
    total_deals = len(deals_df)

    high_confidence = len(
        deals_df[deals_df["Closure Probability"] == "High"]
    )

    low_confidence = len(
        deals_df[deals_df["Closure Probability"] == "Low"]
    )

    # Sector concentration
    sector_distribution = deals_df.groupby("Sector/service")["Masked Deal value"].sum()
    top_sector = sector_distribution.idxmax() if len(sector_distribution) > 0 else "N/A"
    top_sector_value = sector_distribution.max() if len(sector_distribution) > 0 else 0

    # Execution risk logic
    execution_capacity = work_metrics["Ongoing Projects"]
    pipeline_pressure = total_deals

    execution_risk = "Low"
    if pipeline_pressure > execution_capacity * 3:
        execution_risk = "High"
    elif pipeline_pressure > execution_capacity * 2:
        execution_risk = "Moderate"

    # Revenue quality
    revenue_quality = "Strong"
    if low_confidence > high_confidence:
        revenue_quality = "Risky"

    # ================= EXECUTIVE RESPONSE =================

    executive_summary = f"""
🚀 Executive Business Summary

📈 Sales Performance:
• Total Pipeline: {total_pipeline:,.0f}
• Weighted Forecast: {weighted_pipeline:,.0f}
• Total Deals: {total_deals}
• High Confidence Deals: {high_confidence}
• Low Confidence Deals: {low_confidence}

🏭 Operations:
• Total Projects: {work_metrics['Total Projects']}
• Ongoing Projects: {work_metrics['Ongoing Projects']}
• Completed Projects: {work_metrics['Completed Projects']}

📊 Strategic Insights:
• Largest Revenue Sector: {top_sector} ({top_sector_value:,.0f})
• Revenue Quality: {revenue_quality}
• Execution Risk Level: {execution_risk}

Overall, the business outlook appears { "stable" if execution_risk == "Low" else "aggressive but capacity constrained" }.
"""

    return {
        "answer": executive_summary
    }

    deals_df = fetch_board_data(DEALS_BOARD_ID)
    deals_df = clean_deals(deals_df)

    work_df = fetch_board_data(WORK_BOARD_ID)
    work_metrics = clean_work_orders(work_df)

    question = q.question.lower()

    # ================= SECTOR DETECTION =================
    sectors = deals_df["Sector/service"].dropna().unique()
    selected_sector = None

    for sector in sectors:
        if str(sector).lower() in question:
            selected_sector = sector
            break

    if selected_sector:
        deals_df = deals_df[
            deals_df["Sector/service"] == selected_sector
        ]
        sector_note = selected_sector
    else:
        sector_note = "All sectors"

    # ================= QUARTER FILTER =================
    if "quarter" in question:
        today = datetime.today()
        current_quarter = (today.month - 1) // 3 + 1

        deals_df["Final Close Date"] = deals_df["Close Date (A)"]
        deals_df["Final Close Date"] = deals_df["Final Close Date"].replace("", None)
        deals_df["Final Close Date"] = deals_df["Final Close Date"].fillna(
            deals_df["Tentative Close Date"]
        )

        deals_df["Final Close Date"] = pd.to_datetime(
            deals_df["Final Close Date"],
            errors="coerce"
        )

        deals_df = deals_df[
            deals_df["Final Close Date"].dt.quarter == current_quarter
        ]

        time_note = f"Q{current_quarter}"
    else:
        time_note = "All time"

    # ================= METRICS =================
    total_pipeline = deals_df["Masked Deal value"].sum()
    weighted_pipeline = deals_df["Weighted Value"].sum()
    total_deals = len(deals_df)
    high_confidence = len(
        deals_df[deals_df["Closure Probability"] == "High"]
    )

    # ================= INTELLIGENT RESPONSE LOGIC =================
    if "high confidence" in question:
        return {
            "answer": f"We currently have {high_confidence} high-confidence deals in {sector_note}."
        }

    if "weighted" in question or "forecast" in question:
        return {
            "answer": f"Our risk-adjusted (weighted) pipeline for {sector_note} is {weighted_pipeline:,.0f}."
        }

    if "operations" in question or "projects" in question:
        return {
            "answer": f"""
            We have {work_metrics['Total Projects']} projects in execution.
            {work_metrics['Completed Projects']} completed and
            {work_metrics['Ongoing Projects']} ongoing.
            """
        }

    if "overview" in question or "business" in question:
        return {
            "answer": f"""
            Business Overview:

            Sales:
            Total Pipeline: {total_pipeline:,.0f}
            Weighted Forecast: {weighted_pipeline:,.0f}
            Total Deals: {total_deals}
            High Confidence Deals: {high_confidence}

            Operations:
            Total Projects: {work_metrics['Total Projects']}
            Completed: {work_metrics['Completed Projects']}
            Ongoing: {work_metrics['Ongoing Projects']}
            """
        }

    # Default fallback
    return {
        "answer": f"""
        For {sector_note} during {time_note},
        total pipeline is {total_pipeline:,.0f}
        with weighted forecast of {weighted_pipeline:,.0f}.
        """
    }

@app.get("/", response_class=HTMLResponse)
def chat_ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Monday BI Agent</title>

    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        body {
            margin: 0;
            font-family: Inter, sans-serif;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            height: 100vh;
            display: flex;
            color: white;
        }

        .app-container {
            display: flex;
            width: 100%;
        }

        .sidebar {
            width: 240px;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(20px);
            padding: 20px;
            border-right: 1px solid rgba(255,255,255,0.05);
            display: flex;
            flex-direction: column;
        }

        .sidebar-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
        }

        .sidebar button {
            margin-bottom: 10px;
            padding: 8px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            background: #334155;
            color: white;
        }

        .sidebar button:hover {
            background: #475569;
        }

        #history {
            margin-top: 15px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            font-size: 13px;
            opacity: 0.7;
        }

        .history-item {
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
        }

        .history-item:hover {
            background: rgba(255,255,255,0.08);
        }

        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .chat-header {
            padding: 20px;
            font-size: 18px;
            font-weight: 600;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }

        .messages {
            flex: 1;
            padding: 25px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .message {
            padding: 14px 18px;
            border-radius: 16px;
            max-width: 70%;
            font-size: 14px;
        }

        .user {
            align-self: flex-end;
            background: #3b82f6;
        }

        .bot {
            align-self: flex-start;
            background: rgba(255,255,255,0.05);
        }

        .input-area {
            padding: 18px;
            display: flex;
            gap: 10px;
            background: rgba(0,0,0,0.4);
        }

        input {
            flex: 1;
            padding: 12px;
            border-radius: 10px;
            border: none;
            background: rgba(255,255,255,0.05);
            color: white;
        }

        button.send-btn {
            padding: 12px 20px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
            background: #3b82f6;
            color: white;
        }

        canvas {
            background: white;
            border-radius: 10px;
            padding: 10px;
            margin-top: 10px;
        }
    </style>
</head>

<body>

<div class="app-container">

    <div class="sidebar">
        <div class="sidebar-title">📊 Controls</div>

        <button onclick="newChat()">🆕 New Chat</button>
        <button onclick="clearHistory()">🗑 Clear History</button>

        <div id="history"></div>
    </div>

    <div class="chat-container">
        <div class="chat-header">
            🚀 Monday Business Intelligence Agent
        </div>

        <div class="messages" id="messages"></div>

        <div class="input-area">
            <input type="text" id="question" placeholder="Ask something..." />
            <button class="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

</div>

<script>
const messagesDiv = document.getElementById("messages");
const historyDiv = document.getElementById("history");

let chats = [];
let currentChatIndex = null;

function addMessageToUI(text, className) {
    const msg = document.createElement("div");
    msg.className = "message " + className;
    msg.innerHTML = text.replace(/\\n/g, "<br>");
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function renderChat(index) {
    messagesDiv.innerHTML = "";
    const chat = chats[index];
    chat.messages.forEach(m => {
        addMessageToUI(m.text, m.role);
    });
    currentChatIndex = index;
}

function newChat() {
    messagesDiv.innerHTML = "";
    currentChatIndex = null;
}

function clearHistory() {
    chats = [];
    historyDiv.innerHTML = "";
    messagesDiv.innerHTML = "";
    currentChatIndex = null;
}

async function sendMessage() {
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;

    input.value = "";

    // If no active chat, create one
    if (currentChatIndex === null) {
        const newChatObj = {
            title: question,
            messages: []
        };
        chats.push(newChatObj);
        currentChatIndex = chats.length - 1;

        const chatIndex = chats.length - 1;

        const historyItem = document.createElement("div");
        historyItem.className = "history-item";
        historyItem.innerText = question;
        historyItem.onclick = () => renderChat(chatIndex);
        historyDiv.appendChild(historyItem);
    }

    // Add user message
    chats[currentChatIndex].messages.push({
        role: "user",
        text: question
    });

    addMessageToUI(question, "user");

    const response = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question })
    });

    const data = await response.json();
    const botReply = data.answer || "No response received.";

    chats[currentChatIndex].messages.push({
        role: "bot",
        text: botReply
    });

    addMessageToUI(botReply, "bot");

    // Chart trigger
    if (question.toLowerCase().includes("sector")) {

    // Save chart message
    chats[currentChatIndex].messages.push({
        role: "chart",
        type: "sector"
    });

    renderChart();
}
}

function renderChart() {
    const canvas = document.createElement("canvas");
    messagesDiv.appendChild(canvas);

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['Energy', 'Infra', 'Defense'],
            datasets: [{
                label: 'Revenue by Sector',
                data: [120000, 80000, 60000],
            }]
        }
    });
}

document.getElementById("question").addEventListener("keypress", function(e) {
    if (e.key === "Enter") {
        sendMessage();
    }
});
</script>

</body>
</html>
"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monday BI Agent</title>
    <body>
    
    <style>
        body {
            margin: 0;
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f172a, #1e293b);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
        }

        .chat-container {
            width: 760px;
            height: 85vh;
            background: rgba(20, 20, 30, 0.85);
            backdrop-filter: blur(20px);
            border-radius: 18px;
            display: flex;
            flex-direction: column;
            box-shadow: 0 0 40px rgba(0,0,0,0.6);
            overflow: hidden;
        }

        .chat-header {
            padding: 20px;
            font-size: 18px;
            font-weight: 600;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            background: linear-gradient(90deg, #6366f1, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .messages {
            flex: 1;
            padding: 25px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .message {
            padding: 14px 18px;
            border-radius: 16px;
            max-width: 70%;
            font-size: 14px;
            line-height: 1.5;
            animation: fadeIn 0.25s ease;
        }

        .user {
            align-self: flex-end;
            background: linear-gradient(135deg, #6366f1, #3b82f6);
            box-shadow: 0 0 20px rgba(99,102,241,0.4);
        }

        .bot {
            align-self: flex-start;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
        }

        .input-area {
            padding: 18px;
            display: flex;
            gap: 10px;
            background: rgba(0,0,0,0.4);
            border-top: 1px solid rgba(255,255,255,0.05);
        }

        input {
            flex: 1;
            padding: 14px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(255,255,255,0.05);
            color: white;
        }

        input:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 12px rgba(99,102,241,0.4);
        }

        button {
            padding: 14px 20px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            background: linear-gradient(135deg, #6366f1, #3b82f6);
            color: white;
            transition: 0.2s ease;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(99,102,241,0.6);
        }

        @keyframes fadeIn {
            from {opacity: 0; transform: translateY(5px);}
            to {opacity: 1; transform: translateY(0);}
        }
    </style>
    </head>
    <body>

        <div class="chat-container">
            <div class="chat-header">
                🚀 Monday Business Intelligence Agent
            </div>

            <div class="messages" id="messages"></div>

            <div class="input-area">
                <input type="text" id="question" placeholder="Ask about pipeline, sector, revenue..." />
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>

        <script>
            const messagesDiv = document.getElementById("messages");

            function addMessage(text, className) {
                const msg = document.createElement("div");
                msg.className = "message " + className;
                msg.innerHTML = text.replace(/\\n/g, "<br>");
                messagesDiv.appendChild(msg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            async function sendMessage() {
                const input = document.getElementById("question");
                const question = input.value.trim();
                if (!question) return;

                addMessage(question, "user");
                input.value = "";

                const typingIndicator = document.createElement("div");
                typingIndicator.className = "typing";
                typingIndicator.innerHTML = "<span>Analyzing data</span><span id='dots'>...</span>";
                messagesDiv.appendChild(typingIndicator);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;

                let interval;

                let dots = 0;
                interval = setInterval(() => {
                    dots = (dots + 1) % 4;
                    const dotsElement = document.getElementById("dots");
                    if (dotsElement) {
                        dotsElement.innerText = ".".repeat(dots);
                    }
                }, 500);

                const response = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: question })
                });

                const data = await response.json();

                clearInterval(interval);
                messagesDiv.removeChild(typingIndicator);

                addMessage(data.answer || data.insight, "bot");
            }

            document.getElementById("question").addEventListener("keypress", function(e) {
                if (e.key === "Enter") {
                    sendMessage();
                }
            });
        </script>

    </body>
    </html>
    """