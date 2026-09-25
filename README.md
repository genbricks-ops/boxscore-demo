# Boxscore Demo — Commercial Decision Platform

> **Quick Deploy**: `python deploy_to_databricks.py`

A Databricks-native ML platform demo for ticket pricing, demand forecasting, inventory optimization, and yield management — built as a response to the SF Giants Boxscore Data Science & Commercial Optimization RFP.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Databricks App (React + FastAPI)                │
│  Dashboard │ Demand │ Pricing │ Inventory │ Models │ Monitoring   │
│                    + Floating AI Assistant (Genie)                │
├──────────────────────────────────────────────────────────────────┤
│                     FastAPI Backend (REST API)                    │
│  /api/data │ /api/models │ /api/scoring │ /api/genie │ /api/ai   │
├──────────────────────────────────────────────────────────────────┤
│                   Databricks ML Platform                         │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────────┐   │
│  │ Feature  │  │  MLflow   │  │  Model  │  │  Databricks      │   │
│  │ Store    │  │ Registry  │  │ Serving │  │  Workflows       │   │
│  └─────────┘  └──────────┘  └─────────┘  └──────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                Unity Catalog — boxscore                           │
│  raw (8 tables) │ features (3) │ models (3) │ monitoring (2)     │
└──────────────────────────────────────────────────────────────────┘
```

## ML Models

| Model | Algorithm | Target | MLflow Experiment |
|-------|-----------|--------|-------------------|
| Demand Forecast | Prophet + LightGBM | Ticket demand per game | `boxscore_demand_forecast` |
| Price Sensitivity | XGBoost + Hyperopt | Conversion rate / elasticity | `boxscore_price_sensitivity` |
| Inventory Optimizer | Linear Programming | Revenue-maximizing allocation | `boxscore_inventory_optimizer` |
| Revenue Predictor | LightGBM | Total revenue per game | `boxscore_revenue_predictor` |
| Anomaly Detector | Isolation Forest | Demand/price/inventory anomalies | `boxscore_anomaly_detector` |
| Recommendation Engine | Ensemble | Discrete price recommendations | `boxscore_recommendation_engine` |

## Quick Start

### Prerequisites

- **Databricks Workspace**: `https://dbc-65b0e455-bd37.cloud.databricks.com/`
- **Databricks CLI**: `pip install databricks-cli && databricks configure --token`
- **Node.js** 18+ (for frontend build)
- **Python** 3.10+

### Deploy to Databricks

```bash
python deploy_to_databricks.py
```

For a hard redeploy (delete existing app and redeploy):

```bash
python deploy_to_databricks.py --hard-redeploy
```

### Local Development

**Frontend** (port 5173):
```bash
cd frontend
npm install
npm run dev
```

**Backend** (port 8000):
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The frontend dev server proxies `/api/*` requests to the backend.

### Run Notebooks on Databricks

Import the `notebooks/` folder to your Databricks workspace and run in order:

1. `00_setup/01_catalog_setup.py` — Create Unity Catalog tables
2. `00_setup/02_synthetic_data.py` — Generate synthetic data
3. `01_feature_engineering/*` — Build feature tables
4. `02_models/*` — Train and register ML models
5. `03_validation/*` — Validate models (champion/challenger)
6. `04_scoring/*` — Set up batch scoring and serving endpoints
7. `05_monitoring/*` — Configure drift and performance monitoring

## API Documentation

Once running, visit `/docs` for the interactive Swagger UI.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/data/dashboard` | GET | KPI summary |
| `/api/data/demand` | GET | Demand forecast data |
| `/api/data/pricing` | GET | Pricing recommendations |
| `/api/data/inventory` | GET | Inventory status |
| `/api/data/events` | GET | Event details |
| `/api/data/monitoring` | GET | Model performance |
| `/api/models` | GET | MLflow registered models |
| `/api/scoring/demand` | POST | Real-time demand prediction |
| `/api/scoring/pricing` | POST | Real-time price recommendation |
| `/api/scoring/what-if` | POST | Revenue scenario simulation |
| `/api/genie/chat` | POST | Natural language queries |
| `/api/genie/spaces` | GET | Available Genie spaces |

## Project Structure

```
boxscore-demo/
├── notebooks/              # Databricks notebooks (17 files)
│   ├── 00_setup/           # Catalog + synthetic data
│   ├── 01_feature_engineering/  # Feature tables
│   ├── 02_models/          # ML model training
│   ├── 03_validation/      # Champion/challenger
│   ├── 04_scoring/         # Batch + real-time
│   └── 05_monitoring/      # Drift + performance
├── frontend/               # React + TypeScript + MUI
│   └── src/
│       ├── pages/          # 6 app pages
│       └── components/     # Reusable components
├── backend/                # FastAPI
│   └── routers/            # API route handlers
├── build.py                # Build script
├── deploy_to_databricks.py # Deployment script
└── app.yaml                # Databricks app config
```

## Data Schema (Unity Catalog)

**Catalog**: `boxscore`

| Schema | Table | Granularity | Refresh |
|--------|-------|-------------|---------|
| `raw` | `pricing` | Game, Seat | Daily |
| `raw` | `available_inventory` | Game, Seat | Daily |
| `raw` | `page_views` | Game | Daily |
| `raw` | `sales` | Transaction | 15-min |
| `raw` | `event_details` | Game | Static |
| `raw` | `seat_facts` | Seat | Static |
| `raw` | `secondary_listings` | Game, Seat | Daily |
| `raw` | `secondary_sales` | Game, Seat | Daily |
| `features` | `demand_features` | Game, Section, Date | Daily |
| `features` | `pricing_features` | Game, Section, Date | Daily |
| `features` | `inventory_features` | Game, Section, Date | Daily |
| `models` | `demand_predictions` | Game | Daily |
| `models` | `price_recommendations` | Game, Section | Daily |
| `models` | `inventory_allocations` | Game, Section | Daily |
| `monitoring` | `data_quality_log` | Run | Per-check |
| `monitoring` | `model_metrics_log` | Model, Window | Daily |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Databricks CLI not found` | `pip install databricks-cli` |
| `CLI not configured` | `databricks configure --token` |
| `Frontend build fails` | `cd frontend && npm install` |
| `Backend import errors` | `cd backend && pip install -r requirements.txt` |
| `Permission denied on serving endpoint` | Grant SP `CAN_QUERY` permission |
| `Table not found in Unity Catalog` | Run `01_catalog_setup.py` notebook first |
| `Model not found in registry` | Run the model training notebooks first |
