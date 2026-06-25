"""add user profile fields

Revision ID: b68bd74b290f
Revises: a607d5299204
Create Date: 2026-06-25 20:33:55.113389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b68bd74b290f'
down_revision: Union[str, Sequence[str], None] = 'a607d5299204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("employment_confidence", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("risk_tolerance", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("investment_horizon", sa.String(), nullable=True))
    op.add_column("users", sa.Column("investment_experience", sa.String(), nullable=True))
    op.add_column("users", sa.Column("income_stability", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("dependents_count", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("has_emergency_fund", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("preferred_assets", sa.String(), nullable=True))
    pass


def downgrade() -> None:
    op.drop_column("users", "preferred_assets")
    op.drop_column("users", "has_emergency_fund")
    op.drop_column("users", "dependents_count")
    op.drop_column("users", "income_stability")
    op.drop_column("users", "investment_experience")
    op.drop_column("users", "investment_horizon")
    op.drop_column("users", "risk_tolerance")
    op.drop_column("users", "employment_confidence")
    op.drop_column("users", "age")
    pass
