"""State machine for the deploy agent lifecycle."""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    READY_TO_APPLY = "ready_to_apply"
    APPLYING = "applying"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


VALID_TRANSITIONS = {
    AgentState.IDLE: [AgentState.CHECKING],
    AgentState.CHECKING: [AgentState.DOWNLOADING, AgentState.IDLE],
    AgentState.DOWNLOADING: [AgentState.READY_TO_APPLY, AgentState.FAILED],
    AgentState.READY_TO_APPLY: [AgentState.APPLYING, AgentState.FAILED],
    AgentState.APPLYING: [AgentState.VERIFYING, AgentState.FAILED],
    AgentState.VERIFYING: [AgentState.SUCCEEDED, AgentState.ROLLING_BACK],
    AgentState.SUCCEEDED: [AgentState.IDLE],
    AgentState.FAILED: [AgentState.IDLE],
    AgentState.ROLLING_BACK: [AgentState.ROLLED_BACK, AgentState.FAILED],
    AgentState.ROLLED_BACK: [AgentState.IDLE],
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


class StateMachine:
    """Manages agent state transitions with validation."""

    def __init__(self, initial_state: AgentState = AgentState.IDLE):
        self._current_state = initial_state
        logger.info("StateMachine initialised in state: %s", self._current_state.value)

    @property
    def current_state(self) -> AgentState:
        return self._current_state

    def transition(self, new_state: AgentState) -> None:
        """Transition to a new state, validating against VALID_TRANSITIONS.

        Args:
            new_state: The target state.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        allowed = VALID_TRANSITIONS.get(self._current_state, [])
        if new_state not in allowed:
            msg = (
                f"Invalid transition: {self._current_state.value} -> {new_state.value}. "
                f"Allowed targets: {[s.value for s in allowed]}"
            )
            logger.error(msg)
            raise InvalidTransitionError(msg)

        old_state = self._current_state
        self._current_state = new_state
        logger.info("State transition: %s -> %s", old_state.value, new_state.value)
