# Databricks notebook source
# MAGIC %md
# MAGIC # Demand Forecasting — Prophet + LightGBM Ensemble
# MAGIC Predicts ticket demand at game level using time-series decomposition (Prophet) combined with gradient boosting (LightGBM) for residual features.

# COMMAND ----------

import mlflow
import mlflow.lightgbm
import mlflow.pyfunc
import numpy as np
import pandas as pd
import lightgbm as lgb
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import TimeSeriesSplit
import shap
import matplotlib.pyplot as plt
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Data

# COMMAND ----------

demand_features = spark.read.table("boxscore.features.demand_features").toPandas()
event_details = spark.read.table("boxscore.raw.event_details").toPandas()

df = demand_features.merge(event_details, on="game_id", how="left")
df["game_date"] = pd.to_datetime(df["game_date"])
df = df.sort_values("game_date").reset_index(drop=True)

print(f"Total records: {len(df)}")
print(f"Date range: {df['game_date'].min()} to {df['game_date'].max()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Feature Engineering

# COMMAND ----------

TARGET = "ticket_demand"

PROPHET_COL = "ds"
PROPHET_TARGET = "y"

FEATURE_COLS = [
    "page_view_avg_7d", "page_view_avg_14d", "page_view_avg_30d",
    "sales_velocity_24h", "sales_velocity_48h", "sales_velocity_72h",
    "days_to_event", "opponent_historical_draw",
    "day_of_week", "month",
    "is_weekend", "is_promotion", "is_bobblehead", "is_fireworks",
    "season_win_pct", "opponent_rank",
    "temperature_proxy", "is_day_game",
]

available_features = [c for c in FEATURE_COLS if c in df.columns]
print(f"Using {len(available_features)} features: {available_features}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Train/Test Split (Time-Based)

# COMMAND ----------

train_mask = df["game_date"] < "2026-01-01"
test_mask = df["game_date"] >= "2026-01-01"

train_df = df[train_mask].copy()
test_df = df[test_mask].copy()

print(f"Train: {len(train_df)} games (through 2025)")
print(f"Test:  {len(test_df)} games (2026)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Prophet Baseline

# COMMAND ----------

prophet_train = train_df[["game_date", TARGET]].rename(columns={"game_date": "ds", TARGET: "y"})

prophet_model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.05,
)
prophet_model.fit(prophet_train)

prophet_future_train = prophet_model.predict(prophet_train[["ds"]])
train_df["prophet_prediction"] = prophet_future_train["yhat"].values

prophet_future_test = prophet_model.predict(test_df[["game_date"]].rename(columns={"game_date": "ds"}))
test_df["prophet_prediction"] = prophet_future_test["yhat"].values

train_df["prophet_residual"] = train_df[TARGET] - train_df["prophet_prediction"]
test_df["prophet_residual"] = test_df[TARGET] - test_df["prophet_prediction"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. LightGBM on Residuals

# COMMAND ----------

lgb_features = available_features + ["prophet_prediction"]

X_train = train_df[lgb_features].fillna(0)
y_train = train_df["prophet_residual"]

X_test = test_df[lgb_features].fillna(0)
y_test = test_df["prophet_residual"]

lgb_params = {
    "objective": "regression",
    "metric": "mae",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": 6,
    "min_child_samples": 10,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "n_estimators": 500,
    "verbose": -1,
}

lgb_model = lgb.LGBMRegressor(**lgb_params)
lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    callbacks=[lgb.early_stopping(50, verbose=False)],
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Ensemble Predictions & Metrics

# COMMAND ----------

train_pred_residual = lgb_model.predict(X_train)
test_pred_residual = lgb_model.predict(X_test)

train_pred = train_df["prophet_prediction"] + train_pred_residual
test_pred = test_df["prophet_prediction"] + test_pred_residual

y_true_train = train_df[TARGET]
y_true_test = test_df[TARGET]

metrics = {
    "train_mape": mean_absolute_percentage_error(y_true_train, train_pred),
    "test_mape": mean_absolute_percentage_error(y_true_test, test_pred),
    "train_rmse": float(np.sqrt(mean_squared_error(y_true_train, train_pred))),
    "test_rmse": float(np.sqrt(mean_squared_error(y_true_test, test_pred))),
    "train_mae": mean_absolute_error(y_true_train, train_pred),
    "test_mae": mean_absolute_error(y_true_test, test_pred),
}

for k, v in metrics.items():
    print(f"{k}: {v:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Walk-Forward Cross-Validation

# COMMAND ----------

tscv = TimeSeriesSplit(n_splits=5)
cv_scores = []

for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
    X_tr, X_val = X_train.iloc[tr_idx], X_train.iloc[val_idx]
    y_tr, y_val = y_train.iloc[tr_idx], y_train.iloc[val_idx]

    cv_model = lgb.LGBMRegressor(**lgb_params)
    cv_model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50, verbose=False)])

    val_pred = cv_model.predict(X_val)
    fold_prophet = train_df.iloc[val_idx]["prophet_prediction"].values
    ensemble_pred = fold_prophet + val_pred
    actual = train_df.iloc[val_idx][TARGET].values

    fold_mape = mean_absolute_percentage_error(actual, ensemble_pred)
    cv_scores.append(fold_mape)
    print(f"Fold {fold + 1} MAPE: {fold_mape:.4f}")

metrics["cv_mean_mape"] = float(np.mean(cv_scores))
metrics["cv_std_mape"] = float(np.std(cv_scores))
print(f"\nCV Mean MAPE: {metrics['cv_mean_mape']:.4f} ± {metrics['cv_std_mape']:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. SHAP Explainability

# COMMAND ----------

explainer = shap.TreeExplainer(lgb_model)
shap_values = explainer.shap_values(X_test)

fig_summary, ax_summary = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()

fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.tight_layout()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. MLflow Logging & Model Registration

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_demand_forecast")

with mlflow.start_run(run_name="prophet_lgbm_ensemble_v1") as run:
    mlflow.log_params(lgb_params)
    mlflow.log_params({
        "prophet_yearly_seasonality": True,
        "prophet_weekly_seasonality": True,
        "prophet_changepoint_prior_scale": 0.05,
        "train_size": len(train_df),
        "test_size": len(test_df),
        "n_features": len(lgb_features),
        "cv_folds": 5,
    })

    for k, v in metrics.items():
        mlflow.log_metric(k, v)

    mlflow.lightgbm.log_model(lgb_model, artifact_path="lgb_model")

    with tempfile.TemporaryDirectory() as tmpdir:
        summary_path = os.path.join(tmpdir, "shap_summary.png")
        fig_summary.savefig(summary_path, dpi=150, bbox_inches="tight")
        mlflow.log_artifact(summary_path, "shap")

        bar_path = os.path.join(tmpdir, "shap_bar.png")
        fig_bar.savefig(bar_path, dpi=150, bbox_inches="tight")
        mlflow.log_artifact(bar_path, "shap")

        preds_df = test_df[["game_id", "game_date", TARGET]].copy()
        preds_df["predicted"] = test_pred
        preds_df["residual"] = preds_df[TARGET] - preds_df["predicted"]
        preds_path = os.path.join(tmpdir, "test_predictions.csv")
        preds_df.to_csv(preds_path, index=False)
        mlflow.log_artifact(preds_path, "predictions")

    run_id = run.info.run_id
    model_uri = f"runs:/{run_id}/lgb_model"
    result = mlflow.register_model(model_uri, "boxscore-demand-forecast")
    print(f"Registered model version: {result.version}")

plt.close("all")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Write Predictions to Unity Catalog

# COMMAND ----------

predictions_df = test_df[["game_id", "game_date"]].copy()
predictions_df["predicted_demand"] = test_pred
predictions_df["model_version"] = result.version
predictions_df["prediction_date"] = pd.Timestamp.now()

spark_preds = spark.createDataFrame(predictions_df)
spark_preds.write.mode("overwrite").saveAsTable("boxscore.models.demand_predictions")

print(f"Wrote {len(predictions_df)} predictions to boxscore.models.demand_predictions")
