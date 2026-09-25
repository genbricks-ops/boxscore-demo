# Databricks notebook source
# MAGIC %md
# MAGIC # Revenue Predictor — LightGBM
# MAGIC Predicts total revenue per game using demand forecasts, pricing decisions, inventory position, and event details.

# COMMAND ----------

import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score, mean_absolute_error
import shap
import matplotlib.pyplot as plt
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load & Prepare Data

# COMMAND ----------

demand_features = spark.read.table("boxscore.features.demand_features").toPandas()
pricing_features = spark.read.table("boxscore.features.pricing_features").toPandas()
inventory_features = spark.read.table("boxscore.features.inventory_features").toPandas()
event_details = spark.read.table("boxscore.raw.event_details").toPandas()
sales = spark.read.table("boxscore.raw.sales").toPandas()

game_revenue = sales.groupby("game_id").agg(total_revenue=("revenue", "sum")).reset_index()

game_demand = demand_features.groupby("game_id").agg({
    "page_view_avg_7d": "mean",
    "sales_velocity_24h": "mean",
    "days_to_event": "min",
}).reset_index()

game_pricing = pricing_features.groupby("game_id").agg({
    "current_price": "mean",
    "price_vs_median": "mean",
    "secondary_market_premium": "mean",
}).reset_index()

game_inventory = inventory_features.groupby("game_id").agg({
    "sell_through_rate": "mean",
    "remaining_inventory_pct": "mean",
}).reset_index()

df = game_revenue.merge(game_demand, on="game_id", how="left")
df = df.merge(game_pricing, on="game_id", how="left")
df = df.merge(game_inventory, on="game_id", how="left")
df = df.merge(event_details, on="game_id", how="left")

df["game_date"] = pd.to_datetime(df["game_date"])
df = df.sort_values("game_date").reset_index(drop=True)

print(f"Games with revenue data: {len(df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Feature Selection

# COMMAND ----------

TARGET = "total_revenue"

FEATURE_COLS = [
    "page_view_avg_7d", "sales_velocity_24h", "days_to_event",
    "current_price", "price_vs_median", "secondary_market_premium",
    "sell_through_rate", "remaining_inventory_pct",
    "is_weekend", "is_promotion", "is_bobblehead", "is_fireworks",
    "day_of_week", "month", "opponent_rank", "season_win_pct",
    "temperature_proxy", "is_day_game",
]

available = [c for c in FEATURE_COLS if c in df.columns]
df_clean = df.dropna(subset=[TARGET])
print(f"Features: {len(available)}, Rows: {len(df_clean)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Train/Test Split

# COMMAND ----------

train_df = df_clean[df_clean["game_date"] < "2026-01-01"]
test_df = df_clean[df_clean["game_date"] >= "2026-01-01"]

X_train = train_df[available].fillna(0)
y_train = train_df[TARGET]
X_test = test_df[available].fillna(0)
y_test = test_df[TARGET]

print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Train LightGBM

# COMMAND ----------

params = {
    "objective": "regression",
    "metric": "mae",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "max_depth": 8,
    "min_child_samples": 5,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "n_estimators": 600,
    "verbose": -1,
}

model = lgb.LGBMRegressor(**params)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.early_stopping(50, verbose=False)],
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Evaluation

# COMMAND ----------

train_pred = model.predict(X_train)
test_pred = model.predict(X_test)

metrics = {
    "train_mape": mean_absolute_percentage_error(y_train, train_pred),
    "test_mape": mean_absolute_percentage_error(y_test, test_pred),
    "train_r2": r2_score(y_train, train_pred),
    "test_r2": r2_score(y_test, test_pred),
    "train_rmse": float(np.sqrt(mean_squared_error(y_train, train_pred))),
    "test_rmse": float(np.sqrt(mean_squared_error(y_test, test_pred))),
    "test_mae": mean_absolute_error(y_test, test_pred),
}

for k, v in metrics.items():
    print(f"{k}: {v:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. SHAP Feature Importance

# COMMAND ----------

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

fig_summary, _ = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()

fig_bar, _ = plt.subplots(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.tight_layout()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Predictions vs Actuals

# COMMAND ----------

fig_pva, ax = plt.subplots(figsize=(8, 8))
ax.scatter(y_test, test_pred, alpha=0.6, edgecolors="k", linewidths=0.5)
max_val = max(y_test.max(), max(test_pred))
ax.plot([0, max_val], [0, max_val], "r--", linewidth=2, label="Perfect prediction")
ax.set_xlabel("Actual Revenue ($)")
ax.set_ylabel("Predicted Revenue ($)")
ax.set_title("Revenue Predictor: Predictions vs Actuals")
ax.legend()
plt.tight_layout()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. MLflow Logging & Registration

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_revenue_predictor")

with mlflow.start_run(run_name="lgbm_revenue_v1") as run:
    mlflow.log_params(params)
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("test_size", len(X_test))
    mlflow.log_param("n_features", len(available))

    for k, v in metrics.items():
        mlflow.log_metric(k, v)

    mlflow.lightgbm.log_model(model, artifact_path="lgb_model")

    with tempfile.TemporaryDirectory() as tmpdir:
        for name, fig in [("shap_summary.png", fig_summary), ("shap_bar.png", fig_bar), ("predictions_vs_actuals.png", fig_pva)]:
            path = os.path.join(tmpdir, name)
            fig.savefig(path, dpi=150, bbox_inches="tight")
            mlflow.log_artifact(path, "plots")

        preds = test_df[["game_id", "game_date", TARGET]].copy()
        preds["predicted_revenue"] = test_pred
        preds.to_csv(os.path.join(tmpdir, "test_predictions.csv"), index=False)
        mlflow.log_artifact(os.path.join(tmpdir, "test_predictions.csv"), "predictions")

    run_id = run.info.run_id
    result = mlflow.register_model(f"runs:/{run_id}/lgb_model", "boxscore-revenue-predictor")
    print(f"Registered model version: {result.version}")

plt.close("all")
