import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------- Device ----------

class DeviceCreate(BaseModel):
    device_name: str
    robot_model: str
    auth_key: str


class DeviceOut(BaseModel):
    id: uuid.UUID
    device_name: str
    robot_model: str
    status: str
    current_release_id: Optional[uuid.UUID] = None
    desired_release_id: Optional[uuid.UUID] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------- Release ----------

class ReleaseServiceCreate(BaseModel):
    service_name: str
    image_repo: str
    image_tag: str
    image_digest: str
    healthcheck_profile: Optional[dict] = None


class ReleaseServiceOut(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    service_name: str
    image_repo: str
    image_tag: str
    image_digest: str
    healthcheck_profile: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReleaseCreate(BaseModel):
    release_name: str
    robot_model: str
    created_by: str
    services: list[ReleaseServiceCreate]


class ReleaseOut(BaseModel):
    id: uuid.UUID
    release_name: str
    robot_model: str
    status: str
    created_by: str
    created_at: datetime
    services: list[ReleaseServiceOut] = []

    class Config:
        from_attributes = True


# ---------- Deployment ----------

class DeploymentCreate(BaseModel):
    release_id: uuid.UUID
    deployment_name: str
    target_type: str
    target_selector: dict
    strategy: str = "all_at_once"
    created_by: str


class DeploymentTargetOut(BaseModel):
    id: uuid.UUID
    deployment_id: uuid.UUID
    device_id: uuid.UUID
    desired_release_id: uuid.UUID
    state: str
    attempt_count: int
    last_error: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class DeploymentOut(BaseModel):
    id: uuid.UUID
    release_id: uuid.UUID
    deployment_name: str
    target_type: str
    target_selector: dict
    strategy: str
    status: str
    created_by: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    targets: list[DeploymentTargetOut] = []

    class Config:
        from_attributes = True


# ---------- Agent ----------

class HeartbeatRequest(BaseModel):
    device_name: str
    agent_state: str
    agent_version: Optional[str] = None
    current_release_id: Optional[uuid.UUID] = None


class DesiredReleaseOut(BaseModel):
    release: Optional[ReleaseOut] = None


class AgentReportRequest(BaseModel):
    device_name: str
    report_type: str
    agent_state: str
    deployment_id: Optional[uuid.UUID] = None
    payload: Optional[dict] = None


class AgentReportOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    report_type: str
    agent_state: Optional[str] = None
    payload: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
