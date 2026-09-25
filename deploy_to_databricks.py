#!/usr/bin/env python3
"""
Boxscore Demo — Databricks Deployment Script
Handles CLI setup, secrets management, scope selection, and app deployment.
"""

import os
import sys
import json
import subprocess
import getpass
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import argparse
import fnmatch
import shutil
import time


@dataclass
class SecretConfig:
    key: str
    value: str
    description: str


@dataclass
class ScopeInfo:
    name: str
    owner: str
    created_at: str
    secret_count: int


class DatabricksDeployer:
    def __init__(self):
        self.workspace_url = None
        self.token = None
        self.user_email = None
        self.app_name = "boxscore-demo"
        self.app_folder = None
        self._auto_detect_workspace_info()

        self.required_secrets = [
            SecretConfig("databricks-token", "", "Databricks personal access token"),
            SecretConfig("databricks-api-url", "", "Databricks workspace URL"),
            SecretConfig("openai-api-key", "", "OpenAI API key"),
            SecretConfig("anthropic-api-key", "", "Anthropic API key"),
            SecretConfig("session-secret", "", "Session secret for FastAPI"),
        ]

    def _auto_detect_workspace_info(self):
        try:
            exit_code, stdout, stderr = self.run_command(["databricks", "config", "get", "host"])
            if exit_code == 0 and stdout.strip():
                self.workspace_url = stdout.strip()

            exit_code, stdout, stderr = self.run_command(["databricks", "current-user", "me", "--output", "json"])
            if exit_code == 0 and stdout.strip():
                try:
                    user_info = json.loads(stdout)
                    self.user_email = user_info.get("userName") or user_info.get("user_name")
                    if self.user_email and not self.app_folder:
                        self.app_folder = f"/Workspace/Users/{self.user_email}/{self.app_name}"
                except json.JSONDecodeError:
                    pass

            if not self.app_folder:
                self.app_folder = f"/Workspace/Users/YOUR_USER@example.com/{self.app_name}"
        except Exception:
            if not self.app_folder:
                self.app_folder = f"/Workspace/Users/YOUR_USER@example.com/{self.app_name}"

    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(command, capture_output=capture_output, text=True, check=False)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_databricks_cli(self) -> bool:
        print("🔍 Checking Databricks CLI...")
        exit_code, stdout, stderr = self.run_command(["databricks", "--version"])
        if exit_code != 0:
            print("❌ Databricks CLI not found. Install: pip install databricks-cli")
            return False

        exit_code, stdout, stderr = self.run_command(["databricks", "workspace", "list", "/"])
        if exit_code != 0:
            print("❌ Databricks CLI not configured. Run: databricks configure --token")
            return False

        print("✅ Databricks CLI is ready")
        return True

    def list_scopes(self) -> List[ScopeInfo]:
        print("📋 Fetching available scopes...")
        exit_code, stdout, stderr = self.run_command(["databricks", "secrets", "list-scopes"])
        if exit_code != 0:
            print(f"❌ Error listing scopes: {stderr}")
            return []

        scopes = []
        lines = stdout.strip().split('\n')
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    scope_name = parts[0]
                    exit_code, secret_stdout, _ = self.run_command(["databricks", "secrets", "list", "--scope", scope_name])
                    secret_count = 0
                    if exit_code == 0:
                        secret_count = len(secret_stdout.strip().split('\n')) - 1
                    scopes.append(ScopeInfo(scope_name, parts[1], parts[2], secret_count))
        return scopes

    def select_scope(self, scopes: List[ScopeInfo]) -> Optional[str]:
        if not scopes:
            print("❌ No scopes found")
            return None

        print(f"\n📊 Found {len(scopes)} scopes:")
        print("-" * 80)
        print(f"{'#':<3} {'Scope Name':<30} {'Owner':<20} {'Secrets':<8} {'Created':<15}")
        print("-" * 80)

        display_scopes = scopes[:20]
        for i, scope in enumerate(display_scopes, 1):
            print(f"{i:<3} {scope.name:<30} {scope.owner:<20} {scope.secret_count:<8} {scope.created_at:<15}")

        if len(scopes) > 20:
            print(f"... and {len(scopes) - 20} more scopes")

        while True:
            try:
                choice = input(f"\n🎯 Select a scope (1-{len(display_scopes)}) or enter scope name: ").strip()
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(display_scopes):
                        return display_scopes[idx].name
                    print(f"❌ Invalid number. Please enter 1-{len(display_scopes)}")
                    continue
                for scope in scopes:
                    if scope.name == choice:
                        return choice
                print("❌ Invalid scope name. Please try again.")
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled")
                return None

    def create_scope(self) -> Optional[str]:
        print("\n🆕 Creating new scope...")
        scope_name = input("Enter scope name: ").strip()
        if not scope_name:
            print("❌ Scope name cannot be empty")
            return None

        exit_code, stdout, stderr = self.run_command(["databricks", "secrets", "create-scope", "--scope", scope_name])
        if exit_code == 0:
            print(f"✅ Created scope: {scope_name}")
            return scope_name
        else:
            print(f"❌ Failed to create scope: {stderr}")
            return None

    def get_secret_values(self) -> bool:
        print("\n🔐 Setting up secrets...")
        for secret in self.required_secrets:
            if secret.key == "databricks-api-url":
                secret.value = self.workspace_url or input(f"Enter {secret.description}: ").strip()
            elif secret.key == "session-secret":
                import secrets
                secret.value = secrets.token_urlsafe(32)
                print(f"✅ Generated session secret: {secret.value[:16]}...")
            else:
                secret.value = getpass.getpass(f"Enter {secret.description}: ").strip()
            if not secret.value:
                print(f"❌ {secret.description} cannot be empty")
                return False
        return True

    def add_secrets_to_scope(self, scope_name: str) -> bool:
        print(f"\n🔐 Adding secrets to scope: {scope_name}")
        for secret in self.required_secrets:
            print(f"Adding {secret.key}...")
            exit_code, stdout, stderr = self.run_command([
                "databricks", "secrets", "put", "--scope", scope_name, "--key", secret.key, "--string-value", secret.value
            ])
            if exit_code != 0:
                print(f"❌ Failed to add secret {secret.key}: {stderr}")
                return False
        print("✅ All secrets added successfully")
        return True

    def build_frontend(self) -> bool:
        print("🔨 Building React frontend...")
        result = subprocess.run(["npm", "run", "build"], cwd="frontend", capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Frontend build failed: {result.stderr}")
            return False
        print("✅ Frontend built successfully")
        return True

    def copy_static_files(self) -> bool:
        print("📁 Copying static files...")
        if os.path.exists("backend/static"):
            shutil.rmtree("backend/static")
        shutil.copytree("frontend/dist", "backend/static")
        print("✅ Static files copied successfully")
        return True

    def package_backend(self) -> bool:
        print("📦 Packaging backend...")
        build_dir = "backend/build"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)

        exclude_patterns = [
            "venv", "venv.*", ".venv", "env", ".env",
            "__pycache__", "*.pyc", "*.pyo", "*.pyd",
            ".pytest_cache", "test_*.py", "tests",
            "test_*.log", "test_*.txt", "*.log",
            "data.json", "cookies.txt",
            ".env_template", "Makefile",
            "build", "dist", "*.egg-info",
            "mlruns", "databricks_backup",
            "*.backup", "*.dbd_secrets",
            "node_modules", ".git", ".gitignore",
            ".DS_Store", "Thumbs.db",
        ]

        def should_exclude(item):
            return any(fnmatch.fnmatch(item, p) for p in exclude_patterns)

        for item in os.listdir("backend"):
            if not should_exclude(item) and not item.startswith('.'):
                src = os.path.join("backend", item)
                dst = os.path.join(build_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

        app_yaml_dst = os.path.join(build_dir, "app.yaml")
        with open(app_yaml_dst, 'w') as f:
            f.write('command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n\n')
            f.write('env:\n')
            f.write('  - name: ENV\n    value: "production"\n')
            f.write('  - name: PORT\n    value: "8000"\n')
            f.write('  - name: DEBUG\n    value: "False"\n')

        print("✅ Backend packaged successfully")
        return True

    def import_to_workspace(self) -> bool:
        print("📤 Importing to Databricks workspace...")
        exit_code, stdout, stderr = self.run_command([
            "databricks", "workspace", "import-dir", "backend/build", self.app_folder, "--overwrite"
        ])
        if exit_code != 0:
            print(f"❌ Failed to import to workspace: {stderr}")
            return False
        print("✅ Imported to workspace successfully")
        return True

    def deploy_app(self, scope_name: str = None) -> bool:
        print("🚀 Deploying app to Databricks...")
        exit_code, stdout, stderr = self.run_command(["databricks", "apps", "create", self.app_name])
        if exit_code != 0 and "already exists" not in stderr and "maximum number of apps" not in stderr:
            print(f"❌ Failed to create app: {stderr}")
            return False

        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "deploy", self.app_name, "--source-code-path", self.app_folder
        ])
        if exit_code != 0:
            print(f"❌ Failed to deploy app: {stderr}")
            return False
        print("✅ App deployed successfully!")
        return True

    def wait_for_app_deletion(self, app_name: str, timeout_seconds: int = 300) -> bool:
        print("⏳ Waiting for app deletion to complete...")
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            exit_code, stdout, stderr = self.run_command(["databricks", "apps", "list"])
            if exit_code != 0:
                print(f"❌ Error checking app list: {stderr}")
                return False
            if app_name not in stdout:
                print(f"✅ App '{app_name}' has been successfully deleted")
                return True
            print(f"⏳ App '{app_name}' still being deleted... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(5)
        print(f"❌ Timeout waiting for app deletion after {timeout_seconds} seconds")
        return False

    def delete_app(self, app_name: str) -> bool:
        print(f"🗑️  Deleting app: {app_name}")
        exit_code, stdout, stderr = self.run_command(["databricks", "apps", "delete", app_name])
        if exit_code == 0:
            print(f"✅ Deleted app: {app_name}")
            return True
        print(f"❌ Failed to delete app: {stderr}")
        return False

    def hard_redeploy(self, scope_name: str = None) -> bool:
        print(f"🔥 Starting HARD REDEPLOY for app: {self.app_name}")
        print("=" * 60)

        exit_code, stdout, stderr = self.run_command(["databricks", "apps", "list"])
        if exit_code != 0:
            print(f"❌ Error checking app list: {stderr}")
            return False

        if self.app_name in stdout:
            if not self.delete_app(self.app_name):
                return False
            if not self.wait_for_app_deletion(self.app_name):
                return False
        else:
            print(f"ℹ️  App '{self.app_name}' does not exist. Proceeding with fresh deployment.")

        if not self.build_frontend():
            return False
        if not self.copy_static_files():
            return False
        if not self.package_backend():
            return False
        if not self.import_to_workspace():
            return False
        if not self.deploy_app(scope_name or ""):
            return False

        self.get_app_info()
        print(f"\n🎉 HARD REDEPLOY completed successfully!")
        return True

    def get_app_info(self) -> bool:
        print("🔍 Getting app information...")
        exit_code, stdout, stderr = self.run_command(["databricks", "apps", "get", self.app_name])
        if exit_code != 0:
            print(f"❌ Failed to get app info: {stderr}")
            return False
        try:
            app_info = json.loads(stdout)
            print(f"\n📱 App Information:")
            print(f"   Name: {app_info.get('name', 'N/A')}")
            print(f"   Status: {app_info.get('app_status', {}).get('state', 'N/A')}")
            app_url = app_info.get('url', 'N/A')
            if app_url and app_url != 'N/A':
                print(f"\n🌐 App URL: {app_url}")
            return True
        except json.JSONDecodeError:
            print(f"❌ Failed to parse app info: {stdout}")
            return False

    def cleanup(self):
        print("🧹 Cleaning up...")
        if os.path.exists("backend/build"):
            shutil.rmtree("backend/build")
        if os.path.exists("app_env.json"):
            os.remove("app_env.json")
        print("✅ Cleanup completed")

    def deploy(self, hard_redeploy: bool = False):
        print(f"🚀 Boxscore Demo — Databricks Deployment\n{'=' * 60}")
        if not self.check_databricks_cli():
            self.cleanup()
            return False

        if hard_redeploy:
            print("🔥 HARD REDEPLOY mode")
            success = self.hard_redeploy()
            self.cleanup()
            return success

        if not self.build_frontend():
            self.cleanup()
            return False
        if not self.copy_static_files():
            self.cleanup()
            return False
        if not self.package_backend():
            self.cleanup()
            return False
        if not self.import_to_workspace():
            self.cleanup()
            return False
        if not self.deploy_app():
            self.cleanup()
            return False

        self.get_app_info()
        print("🎉 Deployment completed successfully!")
        self.cleanup()
        return True


def main():
    parser = argparse.ArgumentParser(description="Deploy Boxscore Demo to Databricks")
    parser.add_argument("--app-name", default="boxscore-demo", help="App name")
    parser.add_argument("--app-folder", default=None, help="Workspace folder path")
    parser.add_argument("--hard-redeploy", action="store_true", help="Delete and redeploy fresh")
    args = parser.parse_args()

    deployer = DatabricksDeployer()
    deployer.app_name = args.app_name

    if args.app_folder:
        deployer.app_folder = args.app_folder
    elif deployer.user_email:
        deployer.app_folder = f"/Workspace/Users/{deployer.user_email}/{args.app_name}"

    print(f"📍 App will be deployed to: {deployer.app_folder}")
    success = deployer.deploy(hard_redeploy=args.hard_redeploy)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
