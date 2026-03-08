"""Health check utilities for deployed services."""

import logging
import socket
import time

import requests

logger = logging.getLogger(__name__)


def check_http(url: str, timeout: int = 5) -> bool:
    """Perform an HTTP GET health check.

    Args:
        url: The URL to check.
        timeout: Request timeout in seconds.

    Returns:
        True if the response status is 2xx, False otherwise.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        ok = 200 <= resp.status_code < 300
        logger.debug("HTTP check %s: status=%d, ok=%s", url, resp.status_code, ok)
        return ok
    except requests.RequestException as exc:
        logger.debug("HTTP check %s failed: %s", url, exc)
        return False


def check_tcp(host: str, port: int, timeout: int = 5) -> bool:
    """Perform a TCP connect health check.

    Args:
        host: Target hostname or IP.
        port: Target port number.
        timeout: Connection timeout in seconds.

    Returns:
        True if the TCP connection succeeds, False otherwise.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            logger.debug("TCP check %s:%d succeeded", host, port)
            return True
    except (socket.timeout, socket.error, OSError) as exc:
        logger.debug("TCP check %s:%d failed: %s", host, port, exc)
        return False


def run_healthcheck(profile: dict) -> bool:
    """Run a single health check based on a profile.

    Profile types:
        - "http": keys url, timeout_sec, interval_sec, success_threshold
        - "tcp": keys host, port, timeout_sec, interval_sec, success_threshold
        - "docker_health": always returns True (assumes healthy)

    Args:
        profile: Health check profile dict.

    Returns:
        True if the health check passes, False otherwise.
    """
    check_type = profile.get("type", "")
    timeout_sec = profile.get("timeout_sec", 5)
    interval_sec = profile.get("interval_sec", 5)
    success_threshold = profile.get("success_threshold", 1)

    if check_type == "docker_health":
        logger.info("docker_health check type: assuming healthy")
        return True

    if check_type == "http":
        url = profile.get("url", "")
        logger.info("Running HTTP health check: url=%s, threshold=%d", url, success_threshold)
        for attempt in range(1, success_threshold + 1):
            if check_http(url, timeout=timeout_sec):
                logger.info("HTTP health check passed on attempt %d/%d", attempt, success_threshold)
                return True
            logger.debug("HTTP health check attempt %d/%d failed", attempt, success_threshold)
            if attempt < success_threshold:
                time.sleep(interval_sec)
        logger.warning("HTTP health check failed after %d attempts", success_threshold)
        return False

    if check_type == "tcp":
        host = profile.get("host", "localhost")
        port = profile.get("port", 0)
        logger.info("Running TCP health check: %s:%d, threshold=%d", host, port, success_threshold)
        for attempt in range(1, success_threshold + 1):
            if check_tcp(host, port, timeout=timeout_sec):
                logger.info("TCP health check passed on attempt %d/%d", attempt, success_threshold)
                return True
            logger.debug("TCP health check attempt %d/%d failed", attempt, success_threshold)
            if attempt < success_threshold:
                time.sleep(interval_sec)
        logger.warning("TCP health check failed after %d attempts", success_threshold)
        return False

    logger.warning("Unknown health check type: %s, skipping", check_type)
    return True


def run_all_healthchecks(services: list[dict]) -> bool:
    """Run health checks for all services that have a healthcheck profile.

    Each service dict may contain a "healthcheck" key with a profile dict.

    Args:
        services: List of service dicts.

    Returns:
        True if all health checks pass, False if any fails.
    """
    all_ok = True
    for svc in services:
        service_name = svc.get("service_name", "unknown")
        profile = svc.get("healthcheck")
        if profile is None:
            logger.debug("No healthcheck profile for service %s, skipping", service_name)
            continue
        logger.info("Running healthcheck for service: %s", service_name)
        if not run_healthcheck(profile):
            logger.error("Healthcheck failed for service: %s", service_name)
            all_ok = False
    return all_ok
