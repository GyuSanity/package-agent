"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "releases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("release_name", sa.String, nullable=False),
        sa.Column("robot_model", sa.String, nullable=False),
        sa.Column("status", sa.String, server_default="draft"),
        sa.Column("created_by", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_name", sa.String, unique=True, nullable=False),
        sa.Column("robot_model", sa.String, nullable=False),
        sa.Column("status", sa.String, server_default="online"),
        sa.Column("current_release_id", UUID(as_uuid=True), sa.ForeignKey("releases.id"), nullable=True),
        sa.Column("desired_release_id", UUID(as_uuid=True), sa.ForeignKey("releases.id"), nullable=True),
        sa.Column("auth_key_hash", sa.String, nullable=False),
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "release_services",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("release_id", UUID(as_uuid=True), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("service_name", sa.String, nullable=False),
        sa.Column("image_repo", sa.String, nullable=False),
        sa.Column("image_tag", sa.String, nullable=False),
        sa.Column("image_digest", sa.String, nullable=False),
        sa.Column("healthcheck_profile", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "deployments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("release_id", UUID(as_uuid=True), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("deployment_name", sa.String, nullable=False),
        sa.Column("target_type", sa.String, nullable=False),
        sa.Column("target_selector", JSON, nullable=False),
        sa.Column("strategy", sa.String, server_default="all_at_once"),
        sa.Column("status", sa.String, server_default="pending"),
        sa.Column("created_by", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "deployment_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=False),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("desired_release_id", UUID(as_uuid=True), sa.ForeignKey("releases.id"), nullable=False),
        sa.Column("state", sa.String, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, server_default="0"),
        sa.Column("last_error", sa.String, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "agent_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("device_id", UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("report_type", sa.String, nullable=False),
        sa.Column("agent_state", sa.String, nullable=True),
        sa.Column("payload", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_reports")
    op.drop_table("deployment_targets")
    op.drop_table("deployments")
    op.drop_table("release_services")
    op.drop_table("devices")
    op.drop_table("releases")
