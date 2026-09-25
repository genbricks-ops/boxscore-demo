# Databricks notebook source
# MAGIC %md
# MAGIC # Price Sensitivity Model — XGBoost with Hyperopt
# MAGIC Estimates price elasticity and willingness-to-pay per section/game type. Uses conversion rate as target.

# COMMAND ----------

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
from hyperopt.pyll import scope
import shap
import matplotlib.pyplot as plt
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Data

# COMMAND ----------

pricing_features = spark.read.table("boxscore.features.pricing_features").toPandas()
demand_features = spark.read.table("boxscore.features.demand_features").toPandas()
seat_facts = spark.read.table("boxscore.raw.seat_facts").toPandas()

df = pricing_features.merge(demand_features, on=["game_id", "as_of_date"], how="left", suffixes=("", "_demand"))
df = df.merge(
    seat_facts[["section_id", "seat_quality_score", "distance_to_home_plate", "is_aisle"]].drop_duplicates("section_id"),
    on="section_id", how="left"
)

df["game_date"] = pd.to_datetime(df["game_date"])
df = df.sort_values("game_date").reset_index(drop=True)
print(f"Records: {len(df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Feature Selection

# COMMAND ----------

TARGET = "conversion_rate"

FEATURE_COLS = [
    "current_price", "price_vs_median", "price_rank_in_section",
    "secondary_market_premium", "price_change_count_7d", "competitor_pricing_index",
    "days_to_event", "page_view_avg_7d", "sales_velocity_24h",
    "seat_quality_score", "distance_to_home_plate", "is_aisle",
    "is_weekend", "is_promotion", "opponent_rank", "season_win_pct",
    "sell_through_rate", "remaining_inventory_pct",
]

available = [c for c in FEATURE_COLS if c in df.columns]
df_clean = df.dropna(subset=[TARGET])
print(f"Using {len(available)} features on {len(df_clean)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Train/Test Split

# COMMAND ----------

split_date = "2026-01-01"
train_df = df_clean[df_clean["game_date"] < split_date]
test_df = df_clean[df_clean["game_date"] >= split_date]

X_train = train_df[available].fillna(0)
y_train = train_df[TARGET]
X_test = test_df[available].fillna(0)
y_test = test_df[TARGET]

print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Hyperopt Tuning

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_price_sensitivity")

search_space = {
    "max_depth": scope.int(hp.quniform("max_depth", 3, 10, 1)),
    "learning_rate": hp.loguniform("learning_rate", np.log(0.01), np.log(0.3)),
    "n_estimators": scope.int(hp.quniform("n_estimators", 100, 800, 50)),
    "min_child_weight": hp.quniform("min_child_weight", 1, 10, 1),
    "subsample": hp.uniform("subsample", 0.6, 1.0),
    "colsample_bytree": hp.uniform("colsample_bytree", 0.6, 1.0),
    "reg_alpha": hp.loguniform("reg_alpha", np.log(1e-3), np.log(10)),
    "reg_lambda": hp.loguniform("reg_lambda", np.log(1e-3), np.log(10)),
    "gamma": hp.uniform("gamma", 0, 5),
}

def objective(params):
    params["max_depth"] = int(params["max_depth"])
    params["n_estimators"] = int(params["n_estimators"])
    params["min_child_weight"] = int(params["min_child_weight"])

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        verbosity=0,
        **params,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    preds = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    return {"loss": rmse, "status": STATUS_OK, "model": model}

trials = Trials()
best = fmin(fn=objective, space=search_space, algo=tpe.suggest, max_evals=30, trials=trials)

best_trial = sorted(trials.results, key=lambda x: x["loss"])[0]
best_model = best_trial["model"]
print(f"Best RMSE: {best_trial['loss']:.6f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Final Evaluation

# COMMAND ----------

test_pred = best_model.predict(X_test)

metrics = {
    "test_rmse": float(np.sqrt(mean_squared_error(y_test, test_pred))),
    "test_r2": r2_score(y_test, test_pred),
    "test_mae": mean_absolute_error(y_test, test_pred),
}

for k, v in metrics.items():
    print(f"{k}: {v:.6f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Price Elasticity Computation

# COMMAND ----------

if "current_price" in available:
    price_idx = available.index("current_price")
    elasticity_records = []

    for section_id in test_df["section_id"].unique():
        section_mask = test_df["section_id"] == section_id
        if section_mask.sum() < 5:
            continue

        X_section = X_test[section_mask].copy()
        base_pred = best_model.predict(X_section)

        X_up = X_section.copy()
        X_up.iloc[:, price_idx] *= 1.01
        up_pred = best_model.predict(X_up)

        pct_change_demand = (up_pred - base_pred) / (base_pred + 1e-9)
        pct_change_price = 0.01
        elasticity = float(np.mean(pct_change_demand / pct_change_price))

        elasticity_records.append({
            "section_id": section_id,
            "elasticity": elasticity,
            "avg_price": float(X_section.iloc[:, price_idx].mean()),
            "avg_conversion": float(base_pred.mean()),
            "n_observations": int(section_mask.sum()),
        })

    elasticity_df = pd.DataFrame(elasticity_records)
    print(f"Computed elasticity for {len(elasticity_df)} sections")
    display(elasticity_df.head(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. SHAP Analysis

# COMMAND ----------

explainer = shap.TreeExplainer(best_model)
shap_values = explainer.shap_values(X_test)

fig_summary, _ = plt.subplots(figsize=(10, 8))
shap.summary_plot(shap_values, X_test, show=False)
plt.tight_layout()

fig_bar, _ = plt.subplots(figsize=(10, 6))
shap.summary_plot(shap_values, X_test, plot_type="bar", show=False)
plt.tight_layout()

if "current_price" in available:
    fig_dep, _ = plt.subplots(figsize=(8, 6))
    shap.dependence_plot("current_price", shap_values, X_test, show=False)
    plt.tight_layout()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. MLflow Logging & Registration

# COMMAND ----------

best_params = best_model.get_params()

with mlflow.start_run(run_name="xgb_price_sensitivity_hyperopt") as run:
    mlflow.log_params({k: v for k, v in best_params.items() if v is not None and k != "callbacks"})
    mlflow.log_param("hyperopt_max_evals", 30)
    mlflow.log_param("train_size", len(X_train))
    mlflow.log_param("test_size", len(X_test))
    mlflow.log_param("n_features", len(available))

    for k, v in metrics.items():
        mlflow.log_metric(k, v)

    mlflow.xgboost.log_model(best_model, artifact_path="xgb_model")

    with tempfile.TemporaryDirectory() as tmpdir:
        fig_summary.savefig(os.path.join(tmpdir, "shap_summary.png"), dpi=150, bbox_inches="tight")
        mlflow.log_artifact(os.path.join(tmpdir, "shap_summary.png"), "shap")

        fig_bar.savefig(os.path.join(tmpdir, "shap_bar.png"), dpi=150, bbox_inches="tight")
        mlflow.log_artifact(os.path.join(tmpdir, "shap_bar.png"), "shap")

        if "current_price" in available:
            fig_dep.savefig(os.path.join(tmpdir, "shap_price_dependence.png"), dpi=150, bbox_inches="tight")
            mlflow.log_artifact(os.path.join(tmpdir, "shap_price_dependence.png"), "shap")

            elasticity_df.to_csv(os.path.join(tmpdir, "elasticity_by_section.csv"), index=False)
            mlflow.log_artifact(os.path.join(tmpdir, "elasticity_by_section.csv"), "elasticity")

    run_id = run.info.run_id
    result = mlflow.register_model(f"runs:/{run_id}/xgb_model", "boxscore-price-sensitivity")
    print(f"Registered model version: {result.version}")

plt.close("all")
