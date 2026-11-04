"""add authentication

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mssql import DATETIME2

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Not a valid Argon2 string, so existing users cannot sign in until the seed writes real hashes.
LOCKED_HASH = "!"


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.Unicode(50), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.execute(
        f"UPDATE users SET username = LEFT(LOWER(name), 50), password_hash = '{LOCKED_HASH}'"  # noqa: S608
    )
    op.alter_column("users", "username", existing_type=sa.Unicode(50), nullable=False)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.create_unique_constraint(op.f("uq_users_username"), "users", ["username"])
    op.create_check_constraint(
        op.f("ck_users_username_not_blank"), "users", "LEN(LTRIM(RTRIM(username))) > 0"
    )
    op.create_check_constraint(
        op.f("ck_users_password_hash_not_blank"), "users", "LEN(password_hash) > 0"
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.CHAR(32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("started_at", DATETIME2(precision=3), nullable=False),
        sa.Column("expires_at", DATETIME2(precision=3), nullable=False),
        sa.Column("ended_at", DATETIME2(precision=3), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user_id_users"),
        sa.CheckConstraint("expires_at > started_at", name=op.f("ck_sessions_expires_after_start")),
    )
    op.create_table(
        "sign_in_attempts",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("username", sa.Unicode(50), nullable=False),
        sa.Column("outcome", sa.String(10), nullable=False),
        sa.Column("attempted_at", DATETIME2(precision=3), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sign_in_attempts"),
        sa.CheckConstraint(
            "outcome IN ('success','failure','throttled','signout')",
            name=op.f("ck_sign_in_attempts_outcome_known"),
        ),
    )
    op.create_index(
        "ix_sign_in_attempts_username_attempted_at",
        "sign_in_attempts",
        ["username", "attempted_at"],
    )


def downgrade() -> None:
    op.drop_table("sign_in_attempts")
    op.drop_table("sessions")
    op.drop_constraint(op.f("ck_users_password_hash_not_blank"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_username_not_blank"), "users", type_="check")
    op.drop_constraint(op.f("uq_users_username"), "users", type_="unique")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
