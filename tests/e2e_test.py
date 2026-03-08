#!/usr/bin/env python3
"""E2E integration test for Control Plane + Agent.

Prerequisites:
    1. Control Plane running: cd control-plane && docker compose up -d
    2. Python packages: pip install requests pyyaml

Usage:
    cd /home/gyyeon/eCode
    python3 tests/e2e_test.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import requests

BASE_URL = "http://localhost:8000"
DEVICE_NAME = "test-robot-001"
ROBOT_MODEL = "extreme"
AUTH_KEY = "test-secret-key"
HEADERS = {"X-Device-Auth-Key": AUTH_KEY, "Content-Type": "application/json"}

passed = 0
failed = 0


def run_step(name, fn, *args, **kwargs):
    global passed, failed
    print(f"\n--- {name} ---")
    try:
        result = fn(*args, **kwargs)
        passed += 1
        return result
    except Exception as e:
        failed += 1
        print(f"  FAIL: {e}")
        return None


def wait_for_control_plane():
    """Wait for the control plane to be ready."""
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=3)
            if r.status_code == 200:
                print("  PASS: Control plane is ready")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(2)
    raise RuntimeError("Control plane not reachable at " + BASE_URL)


def register_device():
    """Register a test device."""
    r = requests.post(f"{BASE_URL}/api/v1/devices", json={
        "device_name": DEVICE_NAME,
        "robot_model": ROBOT_MODEL,
        "auth_key": AUTH_KEY,
    })
    assert r.status_code == 201, f"Device registration failed: {r.status_code} {r.text}"
    device = r.json()
    assert device["device_name"] == DEVICE_NAME
    assert device["robot_model"] == ROBOT_MODEL
    print(f"  PASS: Device registered, id={device['id']}")
    return device


def create_release():
    """Create a multi-service release."""
    r = requests.post(f"{BASE_URL}/api/v1/releases", json={
        "release_name": "e2e-test-release-v1",
        "robot_model": ROBOT_MODEL,
        "created_by": "e2e-test",
        "services": [
            {
                "service_name": "rise",
                "image_repo": "registry.example.com/rise",
                "image_tag": "v1.0.0",
                "image_digest": "sha256:abcdef1234567890",
                "healthcheck_profile": {
                    "type": "http",
                    "url": "http://localhost:9090/health",
                    "timeout_sec": 5,
                    "interval_sec": 2,
                    "success_threshold": 1,
                },
            },
            {
                "service_name": "rise-dashboard",
                "image_repo": "registry.example.com/rise-dashboard",
                "image_tag": "v1.0.0",
                "image_digest": "sha256:fedcba0987654321",
                "healthcheck_profile": {
                    "type": "tcp",
                    "host": "localhost",
                    "port": 3000,
                    "timeout_sec": 5,
                    "interval_sec": 2,
                    "success_threshold": 1,
                },
            },
        ],
    })
    assert r.status_code == 201, f"Release creation failed: {r.status_code} {r.text}"
    release = r.json()
    assert len(release["services"]) == 2
    print(f"  PASS: Release created, id={release['id']}, services={len(release['services'])}")
    return release


def create_deployment(release_id):
    """Create a deployment targeting all devices with the robot model."""
    r = requests.post(f"{BASE_URL}/api/v1/deployments", json={
        "release_id": release_id,
        "deployment_name": "e2e-test-deploy",
        "target_type": "model",
        "target_selector": {"robot_model": ROBOT_MODEL},
        "strategy": "all_at_once",
        "created_by": "e2e-test",
    })
    assert r.status_code == 201, f"Deployment creation failed: {r.status_code} {r.text}"
    deployment = r.json()
    assert deployment["status"] == "in_progress"
    assert len(deployment["targets"]) >= 1, "Expected at least 1 target device"
    print(f"  PASS: Deployment created, id={deployment['id']}, targets={len(deployment['targets'])}")
    return deployment


def verify_desired_release():
    """Check that the agent can fetch a desired release."""
    r = requests.get(
        f"{BASE_URL}/api/v1/agent/desired-release",
        params={"device_name": DEVICE_NAME},
        headers=HEADERS,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    assert "release" in data, f"Response missing 'release' key: {data}"
    assert data["release"] is not None, "release is None"
    release = data["release"]
    print(f"  PASS: Desired release available, id={release['id']}, name={release['release_name']}")
    return data


def run_agent(config_yaml_path):
    """Run the agent in dry-run + single-cycle mode."""
    env = os.environ.copy()
    env["AGENT_CONFIG_PATH"] = config_yaml_path
    result = subprocess.run(
        [sys.executable, "-m", "agent.main"],
        cwd=os.path.join(os.path.dirname(os.path.dirname(__file__)), "robot-deploy-agent"),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    print(f"  Agent output (last 20 lines):")
    for line in output.strip().split("\n")[-20:]:
        print(f"    {line}")

    assert result.returncode == 0, f"Agent exited with code {result.returncode}"
    assert "[DRY RUN]" in output, "Expected [DRY RUN] log entries in agent output"
    print("  PASS: Agent ran successfully in dry-run mode")


def verify_env_files(tmp_config_dir):
    """Check that .env files were written to the temp dir."""
    rise_env = os.path.join(tmp_config_dir, "rise", ".env")
    assert os.path.exists(rise_env), f"Expected .env at {rise_env}"
    with open(rise_env) as f:
        content = f.read()
    assert "RISE_IMAGE=" in content, f".env missing RISE_IMAGE: {content}"
    assert "registry.example.com/rise" in content, f".env missing image repo: {content}"
    print(f"  PASS: .env file written correctly")
    print(f"    Content: {content.strip()}")

    dashboard_env = os.path.join(tmp_config_dir, "rise-dashboard", ".env")
    assert os.path.exists(dashboard_env), f"Expected .env at {dashboard_env}"
    with open(dashboard_env) as f:
        content = f.read()
    assert "RISE_DASHBOARD_IMAGE=" in content
    print(f"  PASS: rise-dashboard .env file also written correctly")


def verify_state_file(state_file):
    """Check that state file was updated with the release id."""
    assert os.path.exists(state_file), f"State file not found at {state_file}"
    with open(state_file) as f:
        state = json.load(f)
    assert state.get("current_release_id") is not None, f"current_release_id is None: {state}"
    print(f"  PASS: State file updated, current_release_id={state['current_release_id']}")
    return state


def verify_auth_rejection():
    """Check that wrong auth key is rejected."""
    r = requests.get(
        f"{BASE_URL}/api/v1/agent/desired-release",
        params={"device_name": DEVICE_NAME},
        headers={"X-Device-Auth-Key": "wrong-key"},
    )
    assert r.status_code == 401, f"Expected 401 for wrong key, got {r.status_code}"
    print("  PASS: Wrong auth key correctly rejected (401)")


def main():
    global passed, failed

    print("=" * 60)
    print("  Robot Edge Deployment Platform - E2E Test")
    print("=" * 60)

    # Setup temp directories
    tmp_config_dir = tempfile.mkdtemp(prefix="e2e-svc-config-")
    tmp_state_dir = tempfile.mkdtemp(prefix="e2e-state-")
    state_file_path = os.path.join(tmp_state_dir, "state.json")
    config_yaml_path = os.path.join(tmp_state_dir, "agent-test.yaml")

    # Write test config yaml
    with open(config_yaml_path, "w") as f:
        f.write(
            f'control_plane_url: "{BASE_URL}"\n'
            f'device_name: "{DEVICE_NAME}"\n'
            f'robot_model: "{ROBOT_MODEL}"\n'
            f'auth_key: "{AUTH_KEY}"\n'
            f"polling_interval_sec: 2\n"
            f"heartbeat_interval_sec: 5\n"
            f'service_config_dir: "{tmp_config_dir}"\n'
            f'state_file: "{state_file_path}"\n'
            f'log_level: "DEBUG"\n'
            f"dry_run: true\n"
            f"single_cycle: true\n"
        )

    try:
        # Phase 1: Control Plane API tests
        run_step("1. Wait for control plane", wait_for_control_plane)
        device = run_step("2. Register device", register_device)
        release = run_step("3. Create release (multi-service)", create_release)
        if release:
            run_step("4. Create deployment", create_deployment, release["id"])
        run_step("5. Verify desired release API", verify_desired_release)
        run_step("6. Verify auth rejection", verify_auth_rejection)

        # Phase 2: Agent dry-run test
        run_step("7. Run agent (dry-run + single-cycle)", run_agent, config_yaml_path)
        run_step("8. Verify .env files created", verify_env_files, tmp_config_dir)
        run_step("9. Verify state file updated", verify_state_file, state_file_path)

    finally:
        # Cleanup
        shutil.rmtree(tmp_config_dir, ignore_errors=True)
        shutil.rmtree(tmp_state_dir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
