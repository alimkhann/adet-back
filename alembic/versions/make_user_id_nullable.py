from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '6898f64d146b'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column(
        "support_requests",
        "user_id",
        existing_type=sa.String(),
        nullable=True
    )

def downgrade():
    op.alter_column(
        "support_requests",
        "user_id",
        existing_type=sa.String(),
        nullable=False
    )