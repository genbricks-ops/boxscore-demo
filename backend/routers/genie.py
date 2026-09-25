import uuid
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/genie", tags=["genie"])

GENIE_SPACES = [
    {
        "key": "pricing",
        "name": "Boxscore Pricing Analytics",
        "description": "Ask questions about ticket pricing, elasticity, and revenue optimization",
        "sample_questions": [
            "What is the average ticket price by section this season?",
            "Which games had the highest price premium on the secondary market?",
            "Show me price changes for Field Club seats in the last 30 days",
            "What is the price elasticity for Bleacher seats on weekends?",
        ],
    },
    {
        "key": "demand",
        "name": "Boxscore Demand Forecasting",
        "description": "Explore demand patterns, page views, and attendance forecasts",
        "sample_questions": [
            "What are the top 5 highest-demand games remaining this season?",
            "How does demand compare for Dodgers vs Padres games?",
            "Show me the page view trend for the next 10 home games",
            "What is the average sell-through rate by day of week?",
        ],
    },
    {
        "key": "inventory",
        "name": "Boxscore Inventory & Operations",
        "description": "Monitor seat inventory, allocations, and availability",
        "sample_questions": [
            "Which sections have the lowest sell-through this month?",
            "How many seats are currently masked across all sections?",
            "What is the total unsold inventory for this weekend's games?",
            "Show me secondary market listing volume vs primary availability",
        ],
    },
]

MOCK_RESPONSES = {
    "average ticket price": {
        "answer": "The average ticket price across all sections for the 2026 season is **$78.42**. "
                  "Premium sections (Field Club, Suite Level, Gotham Club) average $406.67, while value sections "
                  "(Bleachers, Arcade, Gallery) average $27.67.",
        "sql": "SELECT section_name, ROUND(AVG(price), 2) as avg_price, COUNT(*) as transactions\n"
               "FROM boxscore.raw.sales s\n"
               "JOIN boxscore.raw.seat_facts sf ON s.seat_id = sf.seat_id\n"
               "WHERE s.sale_date >= '2026-01-01'\n"
               "GROUP BY section_name\n"
               "ORDER BY avg_price DESC",
        "data": [
            {"section": "Suite Level", "avg_price": 450.00, "transactions": 4200},
            {"section": "Gotham Club", "avg_price": 420.00, "transactions": 1800},
            {"section": "Field Club", "avg_price": 350.00, "transactions": 8400},
            {"section": "Club Level Infield", "avg_price": 180.00, "transactions": 9600},
            {"section": "Club Level Outfield", "avg_price": 120.00, "transactions": 7200},
            {"section": "Lower Box Infield", "avg_price": 95.00, "transactions": 12300},
            {"section": "Lower Box Outfield", "avg_price": 65.00, "transactions": 10800},
            {"section": "View Reserve Infield", "avg_price": 55.00, "transactions": 14400},
            {"section": "View Reserve Outfield", "avg_price": 40.00, "transactions": 12600},
            {"section": "Bleachers", "avg_price": 30.00, "transactions": 16200},
            {"section": "Arcade", "avg_price": 28.00, "transactions": 9600},
            {"section": "Gallery", "avg_price": 25.00, "transactions": 7800},
        ],
    },
    "highest demand": {
        "answer": "The top 5 highest-demand remaining games are:\n\n"
                  "1. **Sep 26 vs Dodgers** — Forecast: 41,100 (Fireworks Friday)\n"
                  "2. **Oct 3 vs Dodgers** — Forecast: 40,800 (Season Finale Weekend)\n"
                  "3. **Sep 27 vs Dodgers** — Forecast: 39,500 (Bobblehead Night)\n"
                  "4. **Sep 20 vs Padres** — Forecast: 37,200 (Orange Friday)\n"
                  "5. **Oct 1 vs Diamondbacks** — Forecast: 35,800 (Fan Appreciation)",
        "sql": "SELECT e.game_date, e.opponent, dp.forecast_demand, e.promotion\n"
               "FROM boxscore.models.demand_predictions dp\n"
               "JOIN boxscore.raw.event_details e ON dp.game_id = e.game_id\n"
               "WHERE e.game_date > CURRENT_DATE()\n"
               "ORDER BY dp.forecast_demand DESC\n"
               "LIMIT 5",
        "data": [
            {"game_date": "2026-09-26", "opponent": "Los Angeles Dodgers", "forecast": 41100, "promotion": "Fireworks Friday"},
            {"game_date": "2026-10-03", "opponent": "Los Angeles Dodgers", "forecast": 40800, "promotion": None},
            {"game_date": "2026-09-27", "opponent": "Los Angeles Dodgers", "forecast": 39500, "promotion": "Bobblehead Night"},
            {"game_date": "2026-09-20", "opponent": "San Diego Padres", "forecast": 37200, "promotion": "Orange Friday"},
            {"game_date": "2026-10-01", "opponent": "Arizona Diamondbacks", "forecast": 35800, "promotion": "Fan Appreciation"},
        ],
    },
    "sell-through": {
        "answer": "Sell-through rates by day of week:\n\n"
                  "| Day | Avg Sell-Through | Avg Revenue |\n"
                  "|-----|-----------------|-------------|\n"
                  "| Friday | 91.2% | $2.85M |\n"
                  "| Saturday | 94.5% | $3.12M |\n"
                  "| Sunday | 87.8% | $2.45M |\n"
                  "| Tuesday | 72.3% | $1.89M |\n"
                  "| Wednesday | 74.1% | $1.95M |\n\n"
                  "Weekend games (Fri–Sun) sell through **91.2%** on average vs **73.2%** for weekday games.",
        "sql": "SELECT DAYOFWEEK(e.game_date) as dow,\n"
               "       ROUND(AVG(i.sold / i.capacity), 3) as avg_sell_through,\n"
               "       ROUND(AVG(s.total_revenue), 0) as avg_revenue\n"
               "FROM boxscore.raw.available_inventory i\n"
               "JOIN boxscore.raw.event_details e ON i.game_id = e.game_id\n"
               "JOIN (SELECT game_id, SUM(price) as total_revenue FROM boxscore.raw.sales GROUP BY game_id) s\n"
               "  ON e.game_id = s.game_id\n"
               "GROUP BY DAYOFWEEK(e.game_date)\n"
               "ORDER BY avg_sell_through DESC",
        "data": [],
    },
}


class ChatRequest(BaseModel):
    question: str
    space_key: str = "pricing"
    conversation_id: Optional[str] = None


@router.get("/spaces")
async def get_spaces():
    return {"spaces": GENIE_SPACES}


@router.post("/chat")
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())[:8]
    question_lower = req.question.lower()

    response = None
    for keyword, mock in MOCK_RESPONSES.items():
        if keyword in question_lower:
            response = mock
            break

    if not response:
        response = {
            "answer": (
                f"Based on the Boxscore data, here's what I found for your question: *\"{req.question}\"*\n\n"
                "The analysis shows that the current pricing strategy is performing within expected parameters. "
                "Key metrics indicate a **4.7% revenue lift** since implementing the latest model recommendations, "
                "with overall sell-through trending at **82.3%** across all sections.\n\n"
                "Would you like me to drill deeper into a specific section or time period?"
            ),
            "sql": f"-- Generated SQL for: {req.question}\n"
                   "SELECT *\nFROM boxscore.raw.sales s\n"
                   "JOIN boxscore.raw.event_details e ON s.game_id = e.game_id\n"
                   "WHERE e.game_date >= '2026-01-01'\nLIMIT 100",
            "data": [],
        }

    return {
        "conversation_id": conversation_id,
        "question": req.question,
        "answer": response["answer"],
        "sql_query": response["sql"],
        "data": response.get("data", []),
        "space": req.space_key,
        "model": "Genie + SQL Warehouse",
    }
