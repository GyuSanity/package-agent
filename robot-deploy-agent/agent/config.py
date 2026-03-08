"""YAML configuration loader for robot-deploy-agent."""

import logging
import os
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "/etc/robot-deploy-agent/agent.yaml"


@dataclass
class Config:
    control_plane_url: str = "http://localhost:8000"
    device_name: str = "robot-001"
    robot_model: str = "extreme"
    auth_key: str = "device-secret-key"
    polling_interval_sec: int = 30
    heartbeat_interval_sec: int = 60
    service_config_dir: str = "/etc/container-runner"
    state_file: str = "/var/lib/robot-deploy-agent/state.json"
    log_level: str = "INFO"
    dry_run: bool = False
    single_cycle: bool = False


def load_config(path: str | None = None) -> Config:
    """Load configuration from a YAML file.

    Args:
        path: Path to the YAML config file. If None, uses the
              AGENT_CONFIG_PATH env var or the default path.

    Returns:
        A populated Config dataclass instance.
    """
    if path is None:
        path = os.environ.get("AGENT_CONFIG_PATH", DEFAULT_CONFIG_PATH)

    logger.info("Loading config from %s", path)

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    config = Config(
        control_plane_url=raw.get("control_plane_url", Config.control_plane_url),
        device_name=raw.get("device_name", Config.device_name),
        robot_model=raw.get("robot_model", Config.robot_model),
        auth_key=raw.get("auth_key", Config.auth_key),
        polling_interval_sec=int(raw.get("polling_interval_sec", Config.polling_interval_sec)),
        heartbeat_interval_sec=int(raw.get("heartbeat_interval_sec", Config.heartbeat_interval_sec)),
        service_config_dir=raw.get("service_config_dir", Config.service_config_dir),
        state_file=raw.get("state_file", Config.state_file),
        log_level=raw.get("log_level", Config.log_level),
        dry_run=bool(raw.get("dry_run", Config.dry_run)),
        single_cycle=bool(raw.get("single_cycle", Config.single_cycle)),
    )

    logger.info("Config loaded: device_name=%s, control_plane_url=%s", config.device_name, config.control_plane_url)
    return config
