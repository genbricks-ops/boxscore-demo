# Instructions for Claude Code

## Deploying This Application

**IMPORTANT**: This project includes a custom deployment script specifically designed for Databricks Apps deployment.

When the user asks to "deploy" or "deploy the app" or "deploy to Databricks", you MUST use the existing `deploy_to_databricks.py` script that is included in this project.

### How to Deploy

Run the deployment script:

```bash
python deploy_to_databricks.py
```

Or for a hard redeploy (delete and redeploy):

```bash
python deploy_to_databricks.py --hard-redeploy
```

### DO NOT

- Do NOT try to deploy using other methods
- Do NOT write new deployment scripts
- Do NOT use generic deployment approaches

### What the Script Does

The `deploy_to_databricks.py` script:
1. Checks Databricks CLI installation and configuration
2. Auto-detects workspace URL and user email
3. Builds the React frontend
4. Packages the backend (excluding venv, tests, etc.)
5. Imports to Databricks workspace
6. Deploys the app
7. Shows the app URL

### Prerequisites

The user needs:
- Databricks CLI installed: `pip install databricks-cli`
- Databricks CLI configured: `databricks configure --token`

If the CLI is not configured, the script will guide the user through the setup process.

## Project Structure

- `notebooks/` — Databricks notebooks for ML pipeline (run on workspace, not locally)
- `frontend/` — React + TypeScript + MUI app
- `backend/` — FastAPI serving the app + APIs
- `build.py` — Builds frontend and packages for deploy
- `deploy_to_databricks.py` — Deploys to Databricks workspace

## Databricks Workspace

- Workspace: `https://dbc-65b0e455-bd37.cloud.databricks.com/`
- Catalog: `boxscore` (Unity Catalog)
- Schemas: `raw`, `features`, `models`, `monitoring`
