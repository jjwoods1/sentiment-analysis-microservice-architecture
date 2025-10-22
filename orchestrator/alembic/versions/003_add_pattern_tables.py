"""Add pattern tables for pattern management and tracking

Revision ID: 003
Revises: 002
Create Date: 2025-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create sentiment_type enum
    sentiment_type_enum = postgresql.ENUM('positive', 'negative', 'neutral', name='sentimenttype')
    sentiment_type_enum.create(op.get_bind(), checkfirst=True)

    # Create patterns table
    op.create_table(
        'patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('pattern_text', sa.String(), nullable=False, unique=True),
        sa.Column('sentiment_type', sentiment_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('match_count', sa.Integer(), nullable=False, default=0),
        sa.Column('added_by', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_matched_at', sa.DateTime(), nullable=True),
    )

    # Create indexes for patterns table
    op.create_index('ix_patterns_id', 'patterns', ['id'])
    op.create_index('ix_patterns_pattern_text', 'patterns', ['pattern_text'])
    op.create_index('ix_patterns_sentiment_type', 'patterns', ['sentiment_type'])
    op.create_index('ix_patterns_is_active', 'patterns', ['is_active'])

    # Create pattern_matches table
    op.create_table(
        'pattern_matches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('pattern_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sentiment_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('matched_text', sa.Text(), nullable=False),
        sa.Column('competitor_name', sa.String(), nullable=False),
        sa.Column('segment_start_time', sa.Float(), nullable=True),
        sa.Column('segment_end_time', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.ForeignKeyConstraint(['pattern_id'], ['patterns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sentiment_result_id'], ['sentiment_results.id'], ondelete='CASCADE'),
    )

    # Create indexes for pattern_matches table
    op.create_index('ix_pattern_matches_id', 'pattern_matches', ['id'])
    op.create_index('ix_pattern_matches_pattern_id', 'pattern_matches', ['pattern_id'])
    op.create_index('ix_pattern_matches_job_id', 'pattern_matches', ['job_id'])
    op.create_index('ix_pattern_matches_sentiment_result_id', 'pattern_matches', ['sentiment_result_id'])
    op.create_index('ix_pattern_matches_competitor_name', 'pattern_matches', ['competitor_name'])
    op.create_index('ix_pattern_matches_detected_at', 'pattern_matches', ['detected_at'])


def downgrade():
    # Drop pattern_matches table and indexes
    op.drop_index('ix_pattern_matches_detected_at', 'pattern_matches')
    op.drop_index('ix_pattern_matches_competitor_name', 'pattern_matches')
    op.drop_index('ix_pattern_matches_sentiment_result_id', 'pattern_matches')
    op.drop_index('ix_pattern_matches_job_id', 'pattern_matches')
    op.drop_index('ix_pattern_matches_pattern_id', 'pattern_matches')
    op.drop_index('ix_pattern_matches_id', 'pattern_matches')
    op.drop_table('pattern_matches')

    # Drop patterns table and indexes
    op.drop_index('ix_patterns_is_active', 'patterns')
    op.drop_index('ix_patterns_sentiment_type', 'patterns')
    op.drop_index('ix_patterns_pattern_text', 'patterns')
    op.drop_index('ix_patterns_id', 'patterns')
    op.drop_table('patterns')

    # Drop enum type
    sentiment_type_enum = postgresql.ENUM('positive', 'negative', 'neutral', name='sentimenttype')
    sentiment_type_enum.drop(op.get_bind(), checkfirst=True)
