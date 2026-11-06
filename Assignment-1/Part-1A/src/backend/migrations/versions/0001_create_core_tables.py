"""create core tables

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mssql import DATETIME2

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "buses",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("name", sa.Unicode(100), nullable=False),
        sa.Column("total_seats", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_buses"),
        sa.UniqueConstraint("name", name="uq_buses_name"),
        sa.CheckConstraint("total_seats BETWEEN 1 AND 60", name=op.f("ck_buses_total_seats_range")),
        sa.CheckConstraint("LEN(LTRIM(RTRIM(name))) > 0", name=op.f("ck_buses_name_not_blank")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("name", sa.Unicode(100), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("name", name="uq_users_name"),
        sa.CheckConstraint("LEN(LTRIM(RTRIM(name))) > 0", name=op.f("ck_users_name_not_blank")),
    )
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=False),
        sa.Column("booked_at", DATETIME2(precision=3), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"], name="fk_bookings_bus_id_buses"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_bookings_user_id_users"),
        sa.UniqueConstraint("bus_id", "seat_number", name="UQ_bookings_bus_seat"),
        sa.CheckConstraint("seat_number >= 1", name=op.f("ck_bookings_seat_number_positive")),
    )


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("users")
    op.drop_table("buses")
