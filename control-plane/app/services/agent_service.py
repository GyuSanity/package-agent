import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AgentReport, DeploymentTarget, Deployment, Device, Release


async def authenticate_device(db: AsyncSession, device_name: str, auth_key: str) -> Device | None:
    result = await db.execute(select(Device).where(Device.device_name == device_name))
    device = result.scalar_one_or_none()
    if device is None:
        return None
    key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
    if device.auth_key_hash != key_hash:
        return None
    return device


async def heartbeat(db: AsyncSession, device: Device, agent_state: str, agent_version: str | None = None, current_release_id: uuid.UUID | None = None) -> Device:
    device.last_seen_at = datetime.utcnow()
    device.status = "online"
    device.updated_at = datetime.utcnow()
    if current_release_id is not None:
        device.current_release_id = current_release_id
    await db.commit()
    await db.refresh(device)
    return device


async def get_desired_release(db: AsyncSession, device: Device) -> Release | None:
    if device.desired_release_id is None:
        return None
    if device.desired_release_id == device.current_release_id:
        return None
    result = await db.execute(select(Release).where(Release.id == device.desired_release_id))
    return result.scalar_one_or_none()


async def process_report(
    db: AsyncSession,
    device: Device,
    report_type: str,
    agent_state: str,
    deployment_id: uuid.UUID | None = None,
    payload: dict | None = None,
) -> AgentReport:
    now = datetime.utcnow()

    report = AgentReport(
        id=uuid.uuid4(),
        device_id=device.id,
        report_type=report_type,
        agent_state=agent_state,
        payload=payload,
        created_at=now,
    )
    db.add(report)

    if report_type == "state_change" and agent_state == "succeeded":
        device.current_release_id = device.desired_release_id
        device.updated_at = now

    # Update deployment target if deployment_id provided
    if deployment_id is not None:
        stmt = select(DeploymentTarget).where(
            DeploymentTarget.deployment_id == deployment_id,
            DeploymentTarget.device_id == device.id,
        )
        result = await db.execute(stmt)
        target = result.scalar_one_or_none()
        if target is not None:
            if agent_state in ("succeeded", "failed", "rolled_back"):
                target.state = agent_state
                target.updated_at = now

            # Check if all targets for this deployment are terminal
            all_targets_result = await db.execute(
                select(DeploymentTarget).where(DeploymentTarget.deployment_id == deployment_id)
            )
            all_targets = all_targets_result.scalars().all()
            terminal_states = {"succeeded", "failed", "rolled_back"}
            if all(t.state in terminal_states for t in all_targets):
                dep_result = await db.execute(
                    select(Deployment).where(Deployment.id == deployment_id)
                )
                deployment = dep_result.scalar_one_or_none()
                if deployment is not None:
                    all_succeeded = all(t.state == "succeeded" for t in all_targets)
                    deployment.status = "completed" if all_succeeded else "failed"
                    deployment.finished_at = now

    await db.commit()
    await db.refresh(report)
    return report
