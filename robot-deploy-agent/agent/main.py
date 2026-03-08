"""Main entry point and polling loop for the robot deploy agent."""

import logging
import os
import time

from agent.api_client import ApiClient
from agent.config import load_config, Config
from agent.docker_manager import pull_all_images
from agent.healthcheck import run_all_healthchecks
from agent.local_state import load_state, save_state
from agent.meta_renderer import update_all_env_files
from agent.rollback import RollbackManager
from agent.state_machine import AgentState, StateMachine
from agent.systemd_manager import restart_all_services

logger = logging.getLogger(__name__)


def reconcile(
    config: Config,
    api_client: ApiClient,
    state_machine: StateMachine,
    local_state_path: str,
) -> None:
    """Single reconciliation cycle.

    Checks for a desired release from the control plane and, if one
    differs from the current release, performs the full deploy workflow:
    download images, update .env files, restart services, verify health,
    and roll back on failure.
    """
    state_machine.transition(AgentState.CHECKING)

    # 1. Get desired release
    desired = api_client.get_desired_release()
    if desired is None:
        logger.debug("No desired release, returning to idle")
        state_machine.transition(AgentState.IDLE)
        return

    current_state = load_state(local_state_path)
    if current_state.get("current_release_id") == desired["id"]:
        logger.debug("Already on desired release %s, returning to idle", desired["id"])
        state_machine.transition(AgentState.IDLE)
        return

    services = desired["services"]
    service_names = [s["service_name"] for s in services]

    # 2. Download (pre-pull all images)
    state_machine.transition(AgentState.DOWNLOADING)
    api_client.send_report("state_change", AgentState.DOWNLOADING.value)

    if not pull_all_images(services, dry_run=config.dry_run):
        state_machine.transition(AgentState.FAILED)
        api_client.send_report(
            "state_change",
            AgentState.FAILED.value,
            payload={"error": "image pull failed"},
        )
        state_machine.transition(AgentState.IDLE)
        return

    # 3. Ready to apply
    state_machine.transition(AgentState.READY_TO_APPLY)

    # 4. Backup + apply
    rollback_mgr = RollbackManager(config.service_config_dir)
    rollback_mgr.backup_env_files(service_names)

    state_machine.transition(AgentState.APPLYING)
    api_client.send_report("state_change", AgentState.APPLYING.value)

    update_all_env_files(config.service_config_dir, services)

    if not restart_all_services(service_names, dry_run=config.dry_run):
        # Rollback on restart failure
        state_machine.transition(AgentState.FAILED)
        api_client.send_report(
            "state_change",
            AgentState.FAILED.value,
            payload={"error": "service restart failed"},
        )
        state_machine.transition(AgentState.IDLE)
        return

    # 5. Verify
    state_machine.transition(AgentState.VERIFYING)
    api_client.send_report("state_change", AgentState.VERIFYING.value)

    if run_all_healthchecks(services, dry_run=config.dry_run):
        state_machine.transition(AgentState.SUCCEEDED)
        save_state(local_state_path, {
            "agent_state": AgentState.IDLE.value,
            "current_release_id": desired["id"],
            "current_release_name": desired.get("release_name"),
            "last_deployment_id": desired.get("deployment_id"),
        })
        api_client.send_report("state_change", AgentState.SUCCEEDED.value)
        state_machine.transition(AgentState.IDLE)
    else:
        # Rollback on healthcheck failure
        state_machine.transition(AgentState.ROLLING_BACK)
        api_client.send_report("state_change", AgentState.ROLLING_BACK.value)
        rollback_mgr.perform_rollback(service_names, dry_run=config.dry_run)
        state_machine.transition(AgentState.ROLLED_BACK)
        api_client.send_report(
            "state_change",
            AgentState.ROLLED_BACK.value,
            payload={"error": "healthcheck failed"},
        )
        state_machine.transition(AgentState.IDLE)


def main() -> None:
    """Main entry point: load config, set up logging, and run polling loop."""
    config_path = os.environ.get("AGENT_CONFIG_PATH", "/etc/robot-deploy-agent/agent.yaml")
    config = load_config(config_path)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "Starting robot-deploy-agent: device=%s, polling=%ds, heartbeat=%ds",
        config.device_name,
        config.polling_interval_sec,
        config.heartbeat_interval_sec,
    )

    api_client = ApiClient(config.control_plane_url, config.device_name, config.auth_key)
    state_machine = StateMachine()

    last_heartbeat = 0.0

    while True:
        try:
            # Heartbeat
            now = time.time()
            if now - last_heartbeat >= config.heartbeat_interval_sec:
                current = load_state(config.state_file)
                api_client.send_heartbeat(
                    state_machine.current_state.value,
                    current.get("current_release_id"),
                )
                last_heartbeat = now

            # Reconcile
            reconcile(config, api_client, state_machine, config.state_file)
        except Exception:
            logger.exception("Reconciliation error")

        if config.single_cycle:
            logger.info("Single cycle mode: exiting after one reconciliation")
            break

        time.sleep(config.polling_interval_sec)


if __name__ == "__main__":
    main()
