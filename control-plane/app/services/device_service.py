import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Device


async def create_device(db: AsyncSession, device_name: str, robot_model: str, auth_key: str) -> Device:
    auth_key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
    device = Device(
        id=uuid.uuid4(),
        device_name=device_name,
        robot_model=robot_model,
        auth_key_hash=auth_key_hash,
        status="online",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def list_devices(db: AsyncSession, robot_model: str | None = None, status: str | None = None) -> list[Device]:
    stmt = select(Device)
    if robot_model is not None:
        stmt = stmt.where(Device.robot_model == robot_model)
    if status is not None:
        stmt = stmt.where(Device.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_device(db: AsyncSession, device_id: uuid.UUID) -> Device | None:
    result = await db.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none()


async def get_device_by_name(db: AsyncSession, device_name: str) -> Device | None:
    result = await db.execute(select(Device).where(Device.device_name == device_name))
    return result.scalar_one_or_none()
