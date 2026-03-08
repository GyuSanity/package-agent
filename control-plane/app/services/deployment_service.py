import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Deployment, DeploymentTarget, Device
from app.schemas.schemas import DeploymentCreate


async def create_deployment(db: AsyncSession, data: DeploymentCreate) -> Deployment:
    now = datetime.utcnow()
    deployment = Deployment(
        id=uuid.uuid4(),
        release_id=data.release_id,
        deployment_name=data.deployment_name,
        target_type=data.target_type,
        target_selector=data.target_selector,
        strategy=data.strategy,
        status="in_progress",
        created_by=data.created_by,
        created_at=now,
        started_at=now,
    )
    db.add(deployment)

    # Find target devices
    if data.target_type == "model":
        robot_model = data.target_selector.get("robot_model")
        stmt = select(Device).where(Device.robot_model == robot_model)
    elif data.target_type == "device_list":
        device_ids = data.target_selector.get("device_ids", [])
        device_uuids = [uuid.UUID(did) if isinstance(did, str) else did for did in device_ids]
        stmt = select(Device).where(Device.id.in_(device_uuids))
    else:
        stmt = select(Device).where(False)

    result = await db.execute(stmt)
    devices = result.scalars().all()

    for device in devices:
        target = DeploymentTarget(
            id=uuid.uuid4(),
            deployment_id=deployment.id,
            device_id=device.id,
            desired_release_id=data.release_id,
            state="pending",
            attempt_count=0,
            updated_at=now,
        )
        db.add(target)
        device.desired_release_id = data.release_id
        device.updated_at = now

    await db.commit()
    await db.refresh(deployment)
    return deployment


async def list_deployments(db: AsyncSession) -> list[Deployment]:
    result = await db.execute(select(Deployment))
    return list(result.scalars().all())


async def get_deployment(db: AsyncSession, deployment_id: uuid.UUID) -> Deployment | None:
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    return result.scalar_one_or_none()
