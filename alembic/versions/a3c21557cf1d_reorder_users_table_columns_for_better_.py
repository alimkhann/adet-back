"""Reorder users table columns for better organization

Revision ID: a3c21557cf1d
Revises: 9d8f61174665
Create Date: 2025-06-21 20:29:06.001013

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3c21557cf1d'
down_revision = '9d8f61174665'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reorder columns in users table for better organization
    # New order: id, clerk_id, email, username, is_active, created_at, updated_at

    # PostgreSQL doesn't have a direct way to reorder columns, so we need to:
    # 1. Create a new table with the desired column order
    # 2. Copy data from the old table
    # 3. Drop the old table
    # 4. Rename the new table

    # First, drop the foreign key constraint
    op.execute("ALTER TABLE onboarding_progress DROP CONSTRAINT IF EXISTS onboarding_progress_user_id_fkey")

    # Create new table with desired column order
    op.execute("""
        CREATE TABLE users_new (
            id SERIAL PRIMARY KEY,
            clerk_id VARCHAR NOT NULL,
            email VARCHAR NOT NULL,
            username VARCHAR,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    # Copy data from old table to new table
    op.execute("""
        INSERT INTO users_new (id, clerk_id, email, username, is_active, created_at, updated_at)
        SELECT id, clerk_id, email, username, is_active, created_at, updated_at
        FROM users
    """)

    # Drop the old table
    op.execute("DROP TABLE users")

    # Rename new table to original name
    op.execute("ALTER TABLE users_new RENAME TO users")

    # Recreate indexes
    op.execute("CREATE INDEX ix_users_clerk_id ON users (clerk_id)")
    op.execute("CREATE INDEX ix_users_email ON users (email)")
    op.execute("CREATE INDEX ix_users_id ON users (id)")

    # Recreate the foreign key constraint
    op.execute("""
        ALTER TABLE onboarding_progress
        ADD CONSTRAINT onboarding_progress_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id)
    """)


def downgrade() -> None:
    # Revert to original column order: id, clerk_id, username, is_active, created_at, updated_at, email

    # Drop the foreign key constraint
    op.execute("ALTER TABLE onboarding_progress DROP CONSTRAINT IF EXISTS onboarding_progress_user_id_fkey")

    # Create table with original column order
    op.execute("""
        CREATE TABLE users_old (
            id SERIAL PRIMARY KEY,
            clerk_id VARCHAR NOT NULL,
            username VARCHAR,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE,
            email VARCHAR NOT NULL
        )
    """)

    # Copy data from current table to old table
    op.execute("""
        INSERT INTO users_old (id, clerk_id, username, is_active, created_at, updated_at, email)
        SELECT id, clerk_id, username, is_active, created_at, updated_at, email
        FROM users
    """)

    # Drop the current table
    op.execute("DROP TABLE users")

    # Rename old table to original name
    op.execute("ALTER TABLE users_old RENAME TO users")

    # Recreate indexes
    op.execute("CREATE INDEX ix_users_clerk_id ON users (clerk_id)")
    op.execute("CREATE INDEX ix_users_email ON users (email)")
    op.execute("CREATE INDEX ix_users_id ON users (id)")

    # Recreate the foreign key constraint
    op.execute("""
        ALTER TABLE onboarding_progress
        ADD CONSTRAINT onboarding_progress_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id)
    """)