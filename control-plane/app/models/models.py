import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    robot_model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="online")
    current_release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=True)
    desired_release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=True)
    auth_key_hash: Mapped[str] = mapped_column(String, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_name: Mapped[str] = mapped_column(String, nullable=False)
    robot_model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    services: Mapped[list["ReleaseService"]] = relationship("ReleaseService", back_populates="release", lazy="selectin")


class ReleaseService(Base):
    __tablename__ = "release_services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    service_name: Mapped[str] = mapped_column(String, nullable=False)
    image_repo: Mapped[str] = mapped_column(String, nullable=False)
    image_tag: Mapped[str] = mapped_column(String, nullable=False)
    image_digest: Mapped[str] = mapped_column(String, nullable=False)
    healthcheck_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    release: Mapped["Release"] = relationship("Release", back_populates="services")


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    deployment_name: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_selector: Mapped[dict] = mapped_column(JSON, nullable=False)
    strategy: Mapped[str] = mapped_column(String, default="all_at_once")
    status: Mapped[str] = mapped_column(String, default="pending")
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    targets: Mapped[list["DeploymentTarget"]] = relationship("DeploymentTarget", back_populates="deployment", lazy="selectin")


class DeploymentTarget(Base):
    __tablename__ = "deployment_targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("deployments.id"), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    desired_release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=False)
    state: Mapped[str] = mapped_column(String, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="targets")


class AgentReport(Base):
    __tablename__ = "agent_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("devices.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    agent_state: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
