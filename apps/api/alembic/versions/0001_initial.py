"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-06-19
"""
from alembic import op
import os
import sys

# allow imports from package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from forgesight_api.db.session import Base  # noqa: E402
from forgesight_api.db import models  # noqa: F401, E402

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
