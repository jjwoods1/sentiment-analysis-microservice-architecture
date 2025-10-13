"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create job status enum
    op.execute("CREATE TYPE jobstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')")

    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='jobstatus'),
                  nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('left_channel_url', sa.String(), nullable=True),
        sa.Column('right_channel_url', sa.String(), nullable=True),
        sa.Column('left_transcript_path', sa.String(), nullable=True),
        sa.Column('right_transcript_path', sa.String(), nullable=True),
        sa.Column('competitors_found', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Create indexes
    op.create_index('ix_jobs_id', 'jobs', ['id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])

    # Create sentiment_results table
    op.create_table(
        'sentiment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competitor_name', sa.String(), nullable=False),
        sa.Column('result_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_sentiment_results_id', 'sentiment_results', ['id'])
    op.create_index('ix_sentiment_results_job_id', 'sentiment_results', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_sentiment_results_job_id', table_name='sentiment_results')
    op.drop_index('ix_sentiment_results_id', table_name='sentiment_results')
    op.drop_table('sentiment_results')

    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_id', table_name='jobs')
    op.drop_table('jobs')

    op.execute('DROP TYPE jobstatus')
