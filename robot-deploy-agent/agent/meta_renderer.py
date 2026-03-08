"""Update .env files with new image references for container-runner."""

import logging
import os

logger = logging.getLogger(__name__)

# Maps service names to their corresponding environment variable keys,
# matching the convention used by container-runner's generate_config.py.
SERVICE_ENV_MAP = {
    "rise": "RISE_IMAGE",
    "rise-dashboard": "RISE_DASHBOARD_IMAGE",
    "whole-body-controller": "WHOLE_BODY_CONTROLLER_IMAGE",
}


def _get_env_key(service_name: str) -> str:
    """Get the .env variable key for a service name.

    Uses SERVICE_ENV_MAP if the service is known, otherwise generates
    a key by upper-casing the name, replacing hyphens with underscores,
    and appending _IMAGE.
    """
    if service_name in SERVICE_ENV_MAP:
        return SERVICE_ENV_MAP[service_name]
    return service_name.upper().replace("-", "_") + "_IMAGE"


def update_env_file(
    service_config_dir: str,
    service_name: str,
    image_repo: str,
    image_tag: str,
    image_digest: str,
) -> None:
    """Update a service's .env file with a new image reference.

    The image reference format is: <image_repo>:<image_tag>@<image_digest>

    If the .env file exists and contains the key, its value is replaced.
    If the key is not found, it is appended. If the file does not exist,
    it is created.

    Args:
        service_config_dir: Root directory for service configs.
        service_name: Name of the service.
        image_repo: Docker image repository.
        image_tag: Docker image tag.
        image_digest: Docker image digest (e.g. sha256:...).
    """
    env_key = _get_env_key(service_name)
    image_ref = f"{image_repo}:{image_tag}@{image_digest}"
    env_path = os.path.join(service_config_dir, service_name, ".env")

    logger.info("Updating %s: %s=%s", env_path, env_key, image_ref)

    lines: list[str] = []
    found = False

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

        new_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(f"{env_key}="):
                new_lines.append(f"{env_key}={image_ref}\n")
                found = True
            else:
                new_lines.append(line)
        lines = new_lines

    if not found:
        lines.append(f"{env_key}={image_ref}\n")

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(env_path), exist_ok=True)

    with open(env_path, "w") as f:
        f.writelines(lines)

    logger.info("Updated .env for service %s", service_name)


def update_all_env_files(service_config_dir: str, services: list[dict]) -> None:
    """Update .env files for all services.

    Args:
        service_config_dir: Root directory for service configs.
        services: List of dicts, each with keys: service_name, image_repo,
                  image_tag, image_digest.
    """
    for svc in services:
        update_env_file(
            service_config_dir=service_config_dir,
            service_name=svc["service_name"],
            image_repo=svc["image_repo"],
            image_tag=svc["image_tag"],
            image_digest=svc["image_digest"],
        )
