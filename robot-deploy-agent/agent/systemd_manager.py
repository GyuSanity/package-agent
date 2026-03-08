"""Systemd service management via subprocess."""

import logging
import subprocess

logger = logging.getLogger(__name__)


def restart_service(service_name: str, dry_run: bool = False) -> bool:
    """Restart a container service via systemctl.

    Args:
        service_name: Logical service name (without -container.service suffix).
        dry_run: If True, skip actual restart and return True.

    Returns:
        True if the restart succeeded, False otherwise.
    """
    unit = f"{service_name}-container.service"
    if dry_run:
        logger.info("[DRY RUN] Would restart systemd unit: %s", unit)
        return True
    logger.info("Restarting systemd unit: %s", unit)
    try:
        result = subprocess.run(
            ["systemctl", "restart", unit],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("Successfully restarted %s", unit)
            return True
        else:
            logger.error(
                "Failed to restart %s: returncode=%d, stderr=%s",
                unit,
                result.returncode,
                result.stderr.strip(),
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error("Timed out restarting %s", unit)
        return False
    except Exception as exc:
        logger.error("Error restarting %s: %s", unit, exc)
        return False


def is_service_active(service_name: str, dry_run: bool = False) -> bool:
    """Check whether a container service is active via systemctl.

    Args:
        service_name: Logical service name (without -container.service suffix).
        dry_run: If True, assume service is active.

    Returns:
        True if the service is active, False otherwise.
    """
    unit = f"{service_name}-container.service"
    if dry_run:
        logger.info("[DRY RUN] Would check service status: %s (assuming active)", unit)
        return True
    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=30,
        )
        active = result.stdout.strip() == "active"
        logger.debug("Service %s is %s", unit, "active" if active else "not active")
        return active
    except Exception as exc:
        logger.error("Error checking status of %s: %s", unit, exc)
        return False


def restart_all_services(service_names: list[str], dry_run: bool = False) -> bool:
    """Restart all listed services.

    Args:
        service_names: List of logical service names.
        dry_run: If True, skip actual restarts.

    Returns:
        True if all restarts succeeded, False if any failed.
    """
    all_ok = True
    for name in service_names:
        if not restart_service(name, dry_run=dry_run):
            all_ok = False
            logger.error("Failed to restart service: %s", name)
    return all_ok
