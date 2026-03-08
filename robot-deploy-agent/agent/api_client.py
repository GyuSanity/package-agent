"""HTTP client for communication with the control plane."""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_RETRY_TOTAL = 3
DEFAULT_BACKOFF_FACTOR = 1.0
DEFAULT_TIMEOUT = 15


class ApiClient:
    """Control plane HTTP client with retry/backoff."""

    def __init__(self, base_url: str, device_name: str, auth_key: str):
        self.base_url = base_url.rstrip("/")
        self.device_name = device_name
        self.auth_key = auth_key

        self.session = requests.Session()
        retry_strategy = Retry(
            total=DEFAULT_RETRY_TOTAL,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "X-Device-Auth-Key": self.auth_key,
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def send_heartbeat(
        self,
        agent_state: str,
        current_release_id: str | None = None,
    ) -> dict | None:
        """POST /api/v1/agent/heartbeat

        Args:
            agent_state: Current agent state string.
            current_release_id: ID of the currently applied release, if any.

        Returns:
            Response JSON dict, or None on failure.
        """
        payload: dict[str, Any] = {
            "device_name": self.device_name,
            "agent_state": agent_state,
        }
        if current_release_id is not None:
            payload["current_release_id"] = current_release_id

        try:
            resp = self.session.post(
                self._url("/api/v1/agent/heartbeat"),
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("Heartbeat sent successfully")
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("Failed to send heartbeat: %s", exc)
            return None

    def get_desired_release(self) -> dict | None:
        """GET /api/v1/agent/desired-release?device_name=xxx

        Returns:
            Release dict if a desired release exists, None otherwise.
        """
        try:
            resp = self.session.get(
                self._url("/api/v1/agent/desired-release"),
                params={"device_name": self.device_name},
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code in (204, 404):
                logger.debug("No desired release found")
                return None
            resp.raise_for_status()
            data = resp.json()
            # Control plane wraps response in {"release": {...}}, unwrap it
            release = data.get("release", data)
            if release is None:
                return None
            logger.info("Desired release received: id=%s", release.get("id"))
            return release
        except requests.RequestException as exc:
            logger.warning("Failed to get desired release: %s", exc)
            return None

    def send_report(
        self,
        report_type: str,
        agent_state: str,
        deployment_id: str | None = None,
        payload: dict | None = None,
    ) -> dict | None:
        """POST /api/v1/agent/report

        Args:
            report_type: Type of report (e.g. "state_change").
            agent_state: Current agent state string.
            deployment_id: Optional deployment ID this report relates to.
            payload: Optional extra payload dict.

        Returns:
            Response JSON dict, or None on failure.
        """
        body: dict[str, Any] = {
            "device_name": self.device_name,
            "report_type": report_type,
            "agent_state": agent_state,
        }
        if deployment_id is not None:
            body["deployment_id"] = deployment_id
        if payload is not None:
            body["payload"] = payload

        try:
            resp = self.session.post(
                self._url("/api/v1/agent/report"),
                json=body,
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            logger.debug("Report sent: type=%s, state=%s", report_type, agent_state)
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("Failed to send report: %s", exc)
            return None
