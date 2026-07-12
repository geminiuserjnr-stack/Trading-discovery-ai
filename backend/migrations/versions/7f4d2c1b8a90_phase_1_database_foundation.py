"""Phase 1 database foundation for channel-centric discovery

Revision ID: 7f4d2c1b8a90
Revises: 3ab91f4770b8
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f4d2c1b8a90"
down_revision: Union[str, Sequence[str], None] = "3ab91f4770b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for channel-centric Discord discovery."""
    op.add_column("channels", sa.Column("investigation_status", sa.String(), server_default="pending", nullable=True))
    op.add_column("channels", sa.Column("confidence_score", sa.Float(), server_default="0", nullable=True))
    op.add_column("channels", sa.Column("last_investigated", sa.DateTime(), nullable=True))

    op.add_column("queries", sa.Column("country", sa.String(), nullable=True))
    op.add_column("queries", sa.Column("generation_source", sa.String(), nullable=True))
    op.add_column("queries", sa.Column("channels_discovered", sa.Integer(), server_default="0", nullable=True))
    op.add_column("queries", sa.Column("discords_found", sa.Integer(), server_default="0", nullable=True))
    op.add_column("queries", sa.Column("success_rate", sa.Float(), server_default="0", nullable=True))

    op.create_table(
        "discord_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("invite_url", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("verification_status", sa.String(), server_default="pending", nullable=False),
        sa.Column("discord_type", sa.String(), server_default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.channel_id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discord_links_channel_id", "discord_links", ["channel_id"])
    op.create_index("ix_discord_links_verification_status", "discord_links", ["verification_status"])

    op.create_table(
        "channel_investigations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("sources_checked", sa.Text(), nullable=True),
        sa.Column("discord_found", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.channel_id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channel_investigations_channel_id", "channel_investigations", ["channel_id"])
    op.create_index("ix_channel_investigations_status", "channel_investigations", ["status"])


def downgrade() -> None:
    """Downgrade schema for channel-centric Discord discovery."""
    op.drop_index("ix_channel_investigations_status", table_name="channel_investigations")
    op.drop_index("ix_channel_investigations_channel_id", table_name="channel_investigations")
    op.drop_table("channel_investigations")

    op.drop_index("ix_discord_links_verification_status", table_name="discord_links")
    op.drop_index("ix_discord_links_channel_id", table_name="discord_links")
    op.drop_table("discord_links")

    op.drop_column("queries", "success_rate")
    op.drop_column("queries", "discords_found")
    op.drop_column("queries", "channels_discovered")
    op.drop_column("queries", "generation_source")
    op.drop_column("queries", "country")

    op.drop_column("channels", "last_investigated")
    op.drop_column("channels", "confidence_score")
    op.drop_column("channels", "investigation_status")
