"""add created_at and updated_at to habits

Revision ID: 5e1819758e86
Revises: 460fddeb317e
Create Date: 2025-06-27 10:40:29.322556

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5e1819758e86'
down_revision = '460fddeb317e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('habit_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('task_description', sa.Text(), nullable=False),
    sa.Column('difficulty_level', sa.Float(), nullable=False),
    sa.Column('estimated_duration', sa.Integer(), nullable=False),
    sa.Column('success_criteria', sa.Text(), nullable=False),
    sa.Column('celebration_message', sa.Text(), nullable=False),
    sa.Column('easier_alternative', sa.Text(), nullable=True),
    sa.Column('harder_alternative', sa.Text(), nullable=True),
    sa.Column('anchor_suggestion', sa.Text(), nullable=True),
    sa.Column('proof_requirements', sa.Text(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('assigned_date', sa.Date(), nullable=False),
    sa.Column('due_date', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('proof_type', sa.String(), nullable=True),
    sa.Column('proof_content', sa.Text(), nullable=True),
    sa.Column('proof_validation_result', sa.Boolean(), nullable=True),
    sa.Column('proof_validation_confidence', sa.Float(), nullable=True),
    sa.Column('proof_feedback', sa.Text(), nullable=True),
    sa.Column('ai_generation_metadata', sa.Text(), nullable=True),
    sa.Column('calibration_metadata', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['habit_id'], ['habits.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_entries_id'), 'task_entries', ['id'], unique=False)
    op.create_table('task_validations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_entry_id', sa.Integer(), nullable=False),
    sa.Column('is_valid', sa.Boolean(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.Column('feedback', sa.Text(), nullable=False),
    sa.Column('suggestions', sa.Text(), nullable=True),
    sa.Column('validation_model', sa.String(), nullable=False),
    sa.Column('validation_prompt', sa.Text(), nullable=True),
    sa.Column('validation_response', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['task_entry_id'], ['task_entries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_validations_id'), 'task_validations', ['id'], unique=False)
    op.add_column('ability_entries', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.alter_column('ability_entries', 'level',
               existing_type=postgresql.ENUM('cant_do', 'hard', 'easy', name='abilitylevel'),
               type_=sa.String(),
               existing_nullable=False)
    op.drop_constraint('ability_entries_user_id_fkey', 'ability_entries', type_='foreignkey')
    op.add_column('habits', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('habits', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('habits', 'description',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=True)
    op.drop_constraint('habits_user_id_fkey', 'habits', type_='foreignkey')
    op.create_foreign_key(None, 'habits', 'users', ['user_id'], ['id'])
    op.add_column('motivation_entries', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.alter_column('motivation_entries', 'level',
               existing_type=postgresql.ENUM('low', 'medium', 'high', name='motivationlevel'),
               type_=sa.String(),
               existing_nullable=False)
    op.drop_constraint('motivation_entries_user_id_fkey', 'motivation_entries', type_='foreignkey')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key('motivation_entries_user_id_fkey', 'motivation_entries', 'users', ['user_id'], ['clerk_id'])
    op.alter_column('motivation_entries', 'level',
               existing_type=sa.String(),
               type_=postgresql.ENUM('low', 'medium', 'high', name='motivationlevel'),
               existing_nullable=False)
    op.drop_column('motivation_entries', 'created_at')
    op.drop_constraint(None, 'habits', type_='foreignkey')
    op.create_foreign_key('habits_user_id_fkey', 'habits', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.alter_column('habits', 'description',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.drop_column('habits', 'updated_at')
    op.drop_column('habits', 'created_at')
    op.create_foreign_key('ability_entries_user_id_fkey', 'ability_entries', 'users', ['user_id'], ['clerk_id'])
    op.alter_column('ability_entries', 'level',
               existing_type=sa.String(),
               type_=postgresql.ENUM('cant_do', 'hard', 'easy', name='abilitylevel'),
               existing_nullable=False)
    op.drop_column('ability_entries', 'created_at')
    op.drop_index(op.f('ix_task_validations_id'), table_name='task_validations')
    op.drop_table('task_validations')
    op.drop_index(op.f('ix_task_entries_id'), table_name='task_entries')
    op.drop_table('task_entries')
    # ### end Alembic commands ###