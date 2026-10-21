"""Add team workspace invitations.

Revision ID: 0003_workspace_collaboration
Revises: 0002_projects_datasets
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_workspace_collaboration"
down_revision: str | None = "0002_projects_datasets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("invited_by", sa.String(length=36), nullable=False),
        sa.Column("accepted_by", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('editor', 'reviewer', 'viewer')",
            name="ck_workspace_invitations_role",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked')",
            name="ck_workspace_invitations_status",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_invitations_workspace_id",
        "workspace_invitations",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_workspace_invitations_email_status",
        "workspace_invitations",
        ["email", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_invitations_email_status",
        table_name="workspace_invitations",
    )
    op.drop_index(
        "ix_workspace_invitations_workspace_id",
        table_name="workspace_invitations",
    )
    op.drop_table("workspace_invitations")
