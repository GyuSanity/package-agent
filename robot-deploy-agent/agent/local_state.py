"""Local state persistence via JSON file."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_STATE = {
    "agent_state": "idle",
    "current_release_id": None,
    "current_release_name": None,
    "last_deployment_id": None,
}


def load_state(path: str) -> dict:
    """Load agent state from a JSON file.

    Args:
        path: Path to the state JSON file.

    Returns:
        State dict. Returns empty dict if the file does not exist.
    """
    if not os.path.exists(path):
        logger.debug("State file not found at %s, returning empty state", path)
        return {}

    try:
        with open(path, "r") as f:
            state = json.load(f)
        logger.debug("Loaded state from %s: %s", path, state)
        return state
    except (json.JSONDecodeError, IOError) as exc:
        logger.error("Failed to load state from %s: %s", path, exc)
        return {}


def save_state(path: str, state: dict) -> None:
    """Save agent state to a JSON file.

    Creates parent directories if they do not exist.

    Args:
        path: Path to the state JSON file.
        state: State dict to persist.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.debug("Saved state to %s: %s", path, state)
    except IOError as exc:
        logger.error("Failed to save state to %s: %s", path, exc)
