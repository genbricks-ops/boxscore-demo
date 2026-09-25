# Databricks notebook source
# MAGIC %md
# MAGIC # Model Serving Endpoints
# MAGIC Register production models as real-time Databricks Model Serving endpoints
# MAGIC for ad-hoc "what-if" pricing and demand scenarios.

# COMMAND ----------

import mlflow
from mlflow.tracking import MlflowClient
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput,
    ServedEntityInput,
    AutoCaptureConfigInput,
)
import json
import time

client = MlflowClient()
w = WorkspaceClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"

ENDPOINTS = {
    "boxscore-demand-forecast": {
        "registered_name": "boxscore-demand-forecast",
        "workload_size": "Small",
        "scale_to_zero": True,
        "min_provisioned_throughput": 0,
        "max_provisioned_throughput": 100,
    },
    "boxscore-price-sensitivity": {
        "registered_name": "boxscore-price-sensitivity",
        "workload_size": "Small",
        "scale_to_zero": True,
        "min_provisioned_throughput": 0,
        "max_provisioned_throughput": 100,
    },
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create or Update Serving Endpoints

# COMMAND ----------

def get_production_version(registered_name):
    versions = client.get_latest_versions(registered_name, stages=["Production"])
    if versions:
        return versions[0].version
    all_versions = client.search_model_versions(f"name='{registered_name}'")
    if all_versions:
        return sorted(all_versions, key=lambda v: int(v.version), reverse=True)[0].version
    return None


def create_or_update_endpoint(endpoint_name, config):
    model_version = get_production_version(config["registered_name"])
    if not model_version:
        print(f"SKIP: No model version found for {config['registered_name']}")
        return

    served_entity = ServedEntityInput(
        entity_name=config["registered_name"],
        entity_version=model_version,
        workload_size=config["workload_size"],
        scale_to_zero_enabled=config["scale_to_zero"],
    )

    endpoint_config = EndpointCoreConfigInput(
        served_entities=[served_entity],
        auto_capture_config=AutoCaptureConfigInput(
            catalog_name=CATALOG,
            schema_name="monitoring",
            enabled=True,
        ),
    )

    existing_endpoints = [e.name for e in w.serving_endpoints.list()]

    if endpoint_name in existing_endpoints:
        print(f"Updating endpoint: {endpoint_name} -> v{model_version}")
        w.serving_endpoints.update_config(endpoint_name, served_entities=[served_entity])
    else:
        print(f"Creating endpoint: {endpoint_name} with v{model_version}")
        w.serving_endpoints.create(name=endpoint_name, config=endpoint_config)

    print(f"  Model: {config['registered_name']} v{model_version}")
    print(f"  Scale-to-zero: {config['scale_to_zero']}")


for ep_name, ep_config in ENDPOINTS.items():
    try:
        create_or_update_endpoint(ep_name, ep_config)
    except Exception as e:
        print(f"ERROR creating {ep_name}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Wait for Endpoints to be Ready

# COMMAND ----------

def wait_for_endpoint(endpoint_name, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        try:
            ep = w.serving_endpoints.get(endpoint_name)
            state = ep.state
            if state and state.ready == "READY":
                print(f"  {endpoint_name}: READY")
                return True
            if state and state.config_update == "UPDATE_FAILED":
                print(f"  {endpoint_name}: FAILED")
                return False
            print(f"  {endpoint_name}: {state.ready if state else 'PENDING'}...")
        except Exception:
            print(f"  {endpoint_name}: not found yet...")
        time.sleep(15)
    print(f"  {endpoint_name}: TIMEOUT after {timeout}s")
    return False

print("Waiting for endpoints...")
for ep_name in ENDPOINTS:
    wait_for_endpoint(ep_name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Endpoints with Sample Payloads

# COMMAND ----------

demand_test_payload = {
    "dataframe_records": [
        {
            "days_to_event": 14,
            "day_of_week": 5,
            "month": 7,
            "is_weekend": 1,
            "is_promotion": 1,
            "opponent_draw_index": 0.85,
            "win_pct": 0.520,
            "rolling_7d_page_views": 12500,
            "rolling_14d_page_views": 11800,
            "sales_velocity_24h": 45.2,
            "section_capacity": 2500,
            "price_tier": 3,
        }
    ]
}

pricing_test_payload = {
    "dataframe_records": [
        {
            "current_price": 75.00,
            "price_vs_median": 1.05,
            "secondary_market_premium": 1.25,
            "days_to_event": 14,
            "sell_through_rate": 0.65,
            "remaining_inventory_pct": 0.35,
            "demand_index": 0.80,
            "seat_quality_score": 7.5,
            "price_changes_7d": 1,
        }
    ]
}

TEST_PAYLOADS = {
    "boxscore-demand-forecast": demand_test_payload,
    "boxscore-price-sensitivity": pricing_test_payload,
}

for ep_name, payload in TEST_PAYLOADS.items():
    print(f"\nTesting {ep_name}...")
    try:
        response = w.serving_endpoints.query(ep_name, dataframe_records=payload["dataframe_records"])
        print(f"  Response: {response.predictions}")
    except Exception as e:
        print(f"  Test failed (endpoint may still be provisioning): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Endpoint Status Summary

# COMMAND ----------

print("=" * 70)
print("  Model Serving Endpoints")
print("=" * 70)
for ep_name, ep_config in ENDPOINTS.items():
    try:
        ep = w.serving_endpoints.get(ep_name)
        state = ep.state.ready if ep.state else "UNKNOWN"
        entities = ep.config.served_entities if ep.config else []
        version = entities[0].entity_version if entities else "?"
        print(f"  {ep_name:<35} v{version:<5}  {state}")
    except Exception:
        print(f"  {ep_name:<35} NOT FOUND")
print("=" * 70)
