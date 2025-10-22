from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, ARRAY, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum
from .database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SentimentType(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Audio channel URLs from split service
    left_channel_url = Column(String, nullable=True)
    right_channel_url = Column(String, nullable=True)

    # Transcript paths in MinIO
    left_transcript_path = Column(String, nullable=True)
    right_transcript_path = Column(String, nullable=True)

    # Competitor analysis results
    competitors_found = Column(ARRAY(String), nullable=True)

    # Progress tracking
    current_step = Column(String, nullable=True)  # e.g., "Transcribing left channel", "Analyzing competitors"
    progress_percentage = Column(String, nullable=True)  # e.g., "25%", "50%", "75%"
    total_competitors = Column(String, nullable=True)  # Total competitors to analyze
    completed_competitors = Column(String, nullable=True)  # How many sentiment analyses completed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    sentiment_results = relationship("SentimentResult", back_populates="job", cascade="all, delete-orphan")


class SentimentResult(Base):
    __tablename__ = "sentiment_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_name = Column(String, nullable=False, index=True)

    # Individual segment data
    segment_text = Column(Text, nullable=False)
    sentiment = Column(String, nullable=False, index=True)  # positive, negative, neutral
    detection_method = Column(String, nullable=False)  # llm-based or rule-based
    detection_details = Column(String, nullable=True)  # e.g., "Model: Llama 2 7B" or "Matched pattern: 'very slow'"

    # Segment metadata
    segment_id = Column(String, nullable=True)
    start_time = Column(String, nullable=True)  # Store as string for flexibility
    end_time = Column(String, nullable=True)

    # Additional metadata from sentiment analysis
    context = Column(String, nullable=True)  # The search context used
    metadata_json = Column(JSONB, nullable=True)  # Store any additional metadata

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="sentiment_results")
    pattern_matches = relationship("PatternMatch", back_populates="sentiment_result", cascade="all, delete-orphan")


class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pattern_text = Column(String, nullable=False, unique=True, index=True)
    sentiment_type = Column(Enum(SentimentType), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    match_count = Column(Integer, default=0, nullable=False)  # Cached count for performance

    # Metadata
    added_by = Column(String, nullable=True)  # Optional: track who added it
    notes = Column(Text, nullable=True)  # Optional: notes about the pattern

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_matched_at = Column(DateTime, nullable=True)  # When it was last matched

    # Relationships
    pattern_matches = relationship("PatternMatch", back_populates="pattern", cascade="all, delete-orphan")


class PatternMatch(Base):
    __tablename__ = "pattern_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("patterns.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    sentiment_result_id = Column(UUID(as_uuid=True), ForeignKey("sentiment_results.id", ondelete="CASCADE"), nullable=False, index=True)

    # Match details
    matched_text = Column(Text, nullable=False)  # The actual text that matched the pattern
    competitor_name = Column(String, nullable=False, index=True)  # Denormalized for easier querying

    # Audio segment information
    segment_start_time = Column(Float, nullable=True)  # Start time in seconds
    segment_end_time = Column(Float, nullable=True)  # End time in seconds

    # Timestamp
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    pattern = relationship("Pattern", back_populates="pattern_matches")
    job = relationship("Job")
    sentiment_result = relationship("SentimentResult", back_populates="pattern_matches")
