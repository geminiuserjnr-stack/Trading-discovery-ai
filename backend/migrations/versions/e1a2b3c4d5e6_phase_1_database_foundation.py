"""Phase 1 Database Foundation

Revision ID: e1a2b3c4d5e6
Revises: d9f8775993b0
Create Date: 2026-07-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = 'd9f8775993b0'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Expand Channel Model
    op.add_column('channels', sa.Column('investigation_status', sa.String(), nullable=True, server_default='pending'))
    op.add_column('channels', sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('channels', sa.Column('last_investigated', sa.DateTime(), nullable=True))

    # 2. Create discord_links table (if not already exists or upgrade it)
    # The existing community_links table is similar but we'll follow the new spec
    op.create_table('discord_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', sa.String(), nullable=False),
        sa.Column('invite_url', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('verification_status', sa.String(), nullable=True, server_default='unverified'),
        sa.Column('discord_type', sa.String(), nullable=True, server_default='unknown'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], )
    )

    # 3. Create channel_investigations table
    op.create_table('channel_investigations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('sources_checked', sa.Text(), nullable=True),
        sa.Column('discord_found', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], )
    )

    # 4. Upgrade Queries
    op.add_column('queries', sa.Column('country', sa.String(), nullable=True))
    op.add_column('queries', sa.Column('generation_source', sa.String(), nullable=True))
    op.add_column('queries', sa.Column('channels_discovered', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('queries', sa.Column('discords_found', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('queries', sa.Column('success_rate', sa.Float(), nullable=True, server_default='0.0'))


def downgrade():
    op.drop_column('queries', 'success_rate')
    op.drop_column('queries', 'discords_found')
    op.drop_column('queries', 'channels_discovered')
    op.drop_column('queries', 'generation_source')
    op.drop_column('queries', 'country')
    op.drop_table('channel_investigations')
    op.drop_table('discord_links')
    op.drop_column('channels', 'last_investigated')
    op.drop_column('channels', 'confidence_score')
    op.drop_column('channels', 'investigation_status')
