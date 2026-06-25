"""change briefs.user_id from uuid to varchar(64)

Watchman now shares STK's database and reads holdings from STK's ``holdings``
table, whose ``user_id`` is ``varchar(64)``. Align ``briefs.user_id`` with that
type so a brief can be keyed by the same string user id (rather than a UUID).

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "briefs",
        "user_id",
        existing_type=sa.Uuid(),
        type_=sa.String(length=64),
        existing_nullable=False,
        postgresql_using="user_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "briefs",
        "user_id",
        existing_type=sa.String(length=64),
        type_=sa.Uuid(),
        existing_nullable=False,
        postgresql_using="user_id::uuid",
    )
