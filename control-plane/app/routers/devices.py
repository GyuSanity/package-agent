import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import DeviceCreate, DeviceOut
from app.services import device_service

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
async def register_device(body: DeviceCreate, db: AsyncSession = Depends(get_db)):
    device = await device_service.create_device(
        db,
        device_name=body.device_name,
        robot_model=body.robot_model,
        auth_key=body.auth_key,
    )
    return device


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    robot_model: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    devices = await device_service.list_devices(db, robot_model=robot_model, status=status_filter)
    return devices


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    device = await device_service.get_device(db, device_id)
    if device is None:
        return JSONResponse(status_code=404, content={"detail": "Device not found"})
    return device
