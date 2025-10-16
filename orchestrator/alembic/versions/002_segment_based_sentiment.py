"""Convert sentiment results to segment-based storage

Revision ID: 002
Revises: 001
Create Date: 2025-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, add progress tracking columns to jobs table if they don't exist
    op.add_column('jobs', sa.Column('current_step', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('progress_percentage', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('total_competitors', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('completed_competitors', sa.String(), nullable=True))

    # Drop the old sentiment_results table entirely and recreate with new schema
    # This is acceptable since we're changing the fundamental data structure
    op.drop_index('ix_sentiment_results_job_id', table_name='sentiment_results')
    op.drop_index('ix_sentiment_results_id', table_name='sentiment_results')
    op.drop_table('sentiment_results')

    # Create new sentiment_results table with segment-based structure
    op.create_table(
        'sentiment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competitor_name', sa.String(), nullable=False),

        # Individual segment data
        sa.Column('segment_text', sa.Text(), nullable=False),
        sa.Column('sentiment', sa.String(), nullable=False),  # positive, negative, neutral
        sa.Column('detection_method', sa.String(), nullable=False),  # llm-based or rule-based
        sa.Column('detection_details', sa.String(), nullable=True),

        # Segment metadata
        sa.Column('segment_id', sa.String(), nullable=True),
        sa.Column('start_time', sa.String(), nullable=True),
        sa.Column('end_time', sa.String(), nullable=True),

        # Additional metadata
        sa.Column('context', sa.String(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
    )

    # Create indexes for better query performance
    op.create_index('ix_sentiment_results_id', 'sentiment_results', ['id'])
    op.create_index('ix_sentiment_results_job_id', 'sentiment_results', ['job_id'])
    op.create_index('ix_sentiment_results_competitor_name', 'sentiment_results', ['competitor_name'])
    op.create_index('ix_sentiment_results_sentiment', 'sentiment_results', ['sentiment'])


def downgrade() -> None:
    # Drop the new table
    op.drop_index('ix_sentiment_results_sentiment', table_name='sentiment_results')
    op.drop_index('ix_sentiment_results_competitor_name', table_name='sentiment_results')
    op.drop_index('ix_sentiment_results_job_id', table_name='sentiment_results')
    op.drop_index('ix_sentiment_results_id', table_name='sentiment_results')
    op.drop_table('sentiment_results')

    # Recreate old table structure
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

    # Remove progress tracking columns from jobs table
    op.drop_column('jobs', 'completed_competitors')
    op.drop_column('jobs', 'total_competitors')
    op.drop_column('jobs', 'progress_percentage')
    op.drop_column('jobs', 'current_step')
