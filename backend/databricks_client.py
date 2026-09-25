"""Databricks SDK client with auto-auth (deployed) and token fallback (local dev)."""
from __future__ import annotations

import os
import logging
import requests as http_requests
from typing import Optional, List, Dict

logger = logging.getLogger("boxscore.databricks")

DATABRICKS_HOST = os.getenv(
    "DATABRICKS_HOST", "https://dbc-65b0e455-bd37.cloud.databricks.com"
)
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

_workspace_client = None
_auth_mode = None


def _init():
    global _workspace_client, _auth_mode
    if _auth_mode is not None:
        return

    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.config import Config

        config = Config(http_timeout_seconds=30)
        _workspace_client = WorkspaceClient(config=config)
        _workspace_client.current_user.me()
        _auth_mode = "sdk"
        logger.info("Databricks SDK auto-auth active")
    except Exception as e:
        logger.warning(f"SDK auth unavailable ({e}), trying token fallback")
        if DATABRICKS_TOKEN:
            _auth_mode = "token"
            logger.info("Using token-based auth")
        else:
            _auth_mode = "none"
            logger.warning("No Databricks auth — serving endpoints unreachable, using mock fallback")


def query_serving_endpoint(endpoint_name: str, payload: dict) -> dict | None:
    """Call a Model Serving endpoint. Returns the parsed response or None on failure."""
    _init()

    if _auth_mode == "sdk" and _workspace_client:
        try:
            resp = _workspace_client.api_client.do(
                "POST",
                f"/serving-endpoints/{endpoint_name}/invocations",
                body=payload,
            )
            return resp
        except Exception as e:
            logger.warning(f"SDK call to {endpoint_name} failed: {e}")
            return None

    elif _auth_mode == "token" and DATABRICKS_TOKEN:
        url = f"{DATABRICKS_HOST}/serving-endpoints/{endpoint_name}/invocations"
        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            resp = http_requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Token call to {endpoint_name} failed: {e}")
            return None

    return None


def list_registered_models(catalog: str = "workspace", schema: str = "boxscore_models"):
    """List UC registered models. Returns list of dicts or None."""
    _init()

    if _auth_mode == "sdk" and _workspace_client:
        try:
            models = []
            for m in _workspace_client.registered_models.list(
                catalog_name=catalog, schema_name=schema, include_aliases=True
            ):
                models.append({
                    "full_name": m.full_name,
                    "name": m.name,
                    "owner": m.owner,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                    "aliases": [
                        {"alias_name": a.alias_name, "version_num": a.version_num}
                        for a in (m.aliases or [])
                    ],
                })
            return models
        except Exception as e:
            logger.warning(f"SDK list_registered_models failed: {e}")
            return None

    elif _auth_mode == "token" and DATABRICKS_TOKEN:
        url = f"{DATABRICKS_HOST}/api/2.1/unity-catalog/models"
        params = {"catalog_name": catalog, "schema_name": schema, "include_aliases": True}
        headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
        try:
            resp = http_requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("registered_models", []):
                models.append({
                    "full_name": m.get("full_name"),
                    "name": m.get("name"),
                    "owner": m.get("owner"),
                    "created_at": m.get("created_at"),
                    "updated_at": m.get("updated_at"),
                    "aliases": [
                        {"alias_name": a.get("alias_name"), "version_num": a.get("version_num")}
                        for a in m.get("aliases", [])
                    ],
                })
            return models
        except Exception as e:
            logger.warning(f"Token list_registered_models failed: {e}")
            return None

    return None


def list_serving_endpoints():
    """List serving endpoints. Returns list of dicts or None."""
    _init()

    if _auth_mode == "sdk" and _workspace_client:
        try:
            endpoints = []
            for ep in _workspace_client.serving_endpoints.list():
                endpoints.append({
                    "name": ep.name,
                    "state": ep.state.ready.value if ep.state and ep.state.ready else "UNKNOWN",
                    "creation_timestamp": ep.creation_timestamp,
                })
            return endpoints
        except Exception as e:
            logger.warning(f"SDK list_serving_endpoints failed: {e}")
            return None

    elif _auth_mode == "token" and DATABRICKS_TOKEN:
        url = f"{DATABRICKS_HOST}/api/2.0/serving-endpoints"
        headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}"}
        try:
            resp = http_requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            endpoints = []
            for ep in data.get("endpoints", []):
                endpoints.append({
                    "name": ep.get("name"),
                    "state": ep.get("state", {}).get("ready", "UNKNOWN"),
                    "creation_timestamp": ep.get("creation_timestamp"),
                })
            return endpoints
        except Exception as e:
            logger.warning(f"Token list_serving_endpoints failed: {e}")
            return None

    return None


def set_model_alias(full_name: str, alias: str, version_num: int) -> bool:
    """Set a UC model alias (e.g. champion). Returns True on success."""
    _init()

    if _auth_mode == "sdk" and _workspace_client:
        try:
            _workspace_client.registered_models.set_alias(
                full_name=full_name, alias=alias, version_num=version_num,
            )
            return True
        except Exception as e:
            logger.warning(f"SDK set_alias failed: {e}")
            return False

    elif _auth_mode == "token" and DATABRICKS_TOKEN:
        url = f"{DATABRICKS_HOST}/api/2.1/unity-catalog/registered-models/{full_name}/aliases"
        headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
        try:
            resp = http_requests.post(
                url, json={"alias_name": alias, "version_num": version_num},
                headers=headers, timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Token set_alias failed: {e}")
            return False

    return False


def update_serving_endpoint(endpoint_name: str, entity_name: str, entity_version: str) -> bool:
    """Update a serving endpoint to a new model version. Returns True on success."""
    _init()

    config_body = {
        "served_entities": [{
            "entity_name": entity_name,
            "entity_version": entity_version,
            "workload_size": "Small",
            "scale_to_zero_enabled": True,
        }],
    }

    if _auth_mode == "sdk" and _workspace_client:
        try:
            _workspace_client.serving_endpoints.update_config(
                name=endpoint_name, **config_body,
            )
            return True
        except Exception as e:
            logger.warning(f"SDK update_serving_endpoint failed: {e}")
            return False

    elif _auth_mode == "token" and DATABRICKS_TOKEN:
        url = f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{endpoint_name}/config"
        headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
        try:
            resp = http_requests.put(url, json=config_body, headers=headers, timeout=15)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"Token update_serving_endpoint failed: {e}")
            return False

    return False


def get_auth_mode() -> str:
    _init()
    return _auth_mode or "none"
