from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import (
    HeartbeatRequest,
    DesiredReleaseOut,
    AgentReportRequest,
    AgentReportOut,
    DeviceOut,
    ReleaseOut,
)
from app.services import agent_service

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


async def _auth_device(db: AsyncSession, device_name: str, auth_key: str):
    device = await agent_service.authenticate_device(db, device_name, auth_key)
    if device is None:
        return None
    return device


@router.post("/heartbeat", response_model=DeviceOut)
async def heartbeat(
    body: HeartbeatRequest,
    x_device_auth_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    device = await _auth_device(db, body.device_name, x_device_auth_key)
    if device is None:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    device = await agent_service.heartbeat(
        db,
        device,
        agent_state=body.agent_state,
        agent_version=body.agent_version,
        current_release_id=body.current_release_id,
    )
    return device


@router.get("/desired-release", response_model=DesiredReleaseOut)
async def desired_release(
    device_name: str,
    x_device_auth_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    device = await _auth_device(db, device_name, x_device_auth_key)
    if device is None:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    release = await agent_service.get_desired_release(db, device)
    if release is None:
        return JSONResponse(status_code=204, content=None)
    return DesiredReleaseOut(release=ReleaseOut.model_validate(release))


@router.post("/report", response_model=AgentReportOut, status_code=status.HTTP_201_CREATED)
async def report(
    body: AgentReportRequest,
    x_device_auth_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    device = await _auth_device(db, body.device_name, x_device_auth_key)
    if device is None:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    agent_report = await agent_service.process_report(
        db,
        device,
        report_type=body.report_type,
        agent_state=body.agent_state,
        deployment_id=body.deployment_id,
        payload=body.payload,
    )
    return agent_report
