"""
Pattern Management API Endpoints
Handles CRUD operations for sentiment patterns and pattern analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid

from ..database import get_db
from ..models import Pattern, PatternMatch, SentimentType, SentimentResult

router = APIRouter(prefix="/patterns", tags=["patterns"])


# Pydantic schemas
class PatternCreate(BaseModel):
    pattern_text: str
    sentiment_type: SentimentType
    notes: Optional[str] = None
    added_by: Optional[str] = None


class PatternUpdate(BaseModel):
    pattern_text: Optional[str] = None
    sentiment_type: Optional[SentimentType] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PatternResponse(BaseModel):
    id: uuid.UUID
    pattern_text: str
    sentiment_type: str
    is_active: bool
    match_count: int
    created_at: datetime
    updated_at: datetime
    last_matched_at: Optional[datetime]
    notes: Optional[str]
    added_by: Optional[str]

    class Config:
        from_attributes = True


class PatternMatchCreate(BaseModel):
    pattern_id: uuid.UUID
    job_id: uuid.UUID
    sentiment_result_id: uuid.UUID
    matched_text: str
    competitor_name: str
    segment_start_time: Optional[float] = None
    segment_end_time: Optional[float] = None


class PatternMatchResponse(BaseModel):
    id: uuid.UUID
    pattern_id: uuid.UUID
    job_id: uuid.UUID
    sentiment_result_id: uuid.UUID
    matched_text: str
    competitor_name: str
    segment_start_time: Optional[float]
    segment_end_time: Optional[float]
    detected_at: datetime

    class Config:
        from_attributes = True


class PatternAnalytics(BaseModel):
    pattern_id: uuid.UUID
    pattern_text: str
    sentiment_type: str
    total_matches: int
    matches_by_date: List[dict]
    top_competitors: List[dict]
    avg_matches_per_day: float


class BulkPatternsCreate(BaseModel):
    patterns: List[str]
    sentiment_type: SentimentType
    added_by: Optional[str] = None


# CRUD Endpoints

@router.get("/", response_model=List[PatternResponse])
def get_all_patterns(
    sentiment_type: Optional[SentimentType] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Get all patterns with optional filtering"""
    query = db.query(Pattern)

    if sentiment_type:
        query = query.filter(Pattern.sentiment_type == sentiment_type)

    if is_active is not None:
        query = query.filter(Pattern.is_active == is_active)

    patterns = query.order_by(Pattern.match_count.desc()).offset(skip).limit(limit).all()
    return patterns


@router.get("/{pattern_id}", response_model=PatternResponse)
def get_pattern(pattern_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific pattern by ID"""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return pattern


@router.post("/", response_model=PatternResponse, status_code=201)
def create_pattern(pattern: PatternCreate, db: Session = Depends(get_db)):
    """Create a new pattern"""
    # Check if pattern already exists
    existing = db.query(Pattern).filter(
        Pattern.pattern_text == pattern.pattern_text.strip().lower()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Pattern already exists")

    new_pattern = Pattern(
        pattern_text=pattern.pattern_text.strip().lower(),
        sentiment_type=pattern.sentiment_type,
        notes=pattern.notes,
        added_by=pattern.added_by
    )

    db.add(new_pattern)
    db.commit()
    db.refresh(new_pattern)

    return new_pattern


@router.post("/bulk", response_model=dict, status_code=201)
def create_patterns_bulk(bulk: BulkPatternsCreate, db: Session = Depends(get_db)):
    """Create multiple patterns at once"""
    added_count = 0
    skipped_count = 0
    errors = []

    for pattern_text in bulk.patterns:
        cleaned_text = pattern_text.strip().lower()

        if not cleaned_text or cleaned_text.startswith('#'):
            skipped_count += 1
            continue

        # Check if exists
        existing = db.query(Pattern).filter(Pattern.pattern_text == cleaned_text).first()
        if existing:
            skipped_count += 1
            continue

        try:
            new_pattern = Pattern(
                pattern_text=cleaned_text,
                sentiment_type=bulk.sentiment_type,
                added_by=bulk.added_by
            )
            db.add(new_pattern)
            added_count += 1
        except Exception as e:
            errors.append(f"Failed to add '{cleaned_text}': {str(e)}")

    db.commit()

    return {
        "added": added_count,
        "skipped": skipped_count,
        "errors": errors
    }


@router.put("/{pattern_id}", response_model=PatternResponse)
def update_pattern(
    pattern_id: uuid.UUID,
    pattern_update: PatternUpdate,
    db: Session = Depends(get_db)
):
    """Update a pattern"""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    if pattern_update.pattern_text is not None:
        # Check if new text conflicts with existing pattern
        cleaned_text = pattern_update.pattern_text.strip().lower()
        existing = db.query(Pattern).filter(
            Pattern.pattern_text == cleaned_text,
            Pattern.id != pattern_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Pattern text already exists")
        pattern.pattern_text = cleaned_text

    if pattern_update.sentiment_type is not None:
        pattern.sentiment_type = pattern_update.sentiment_type

    if pattern_update.is_active is not None:
        pattern.is_active = pattern_update.is_active

    if pattern_update.notes is not None:
        pattern.notes = pattern_update.notes

    db.commit()
    db.refresh(pattern)

    return pattern


@router.delete("/{pattern_id}", status_code=204)
def delete_pattern(pattern_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a pattern"""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db.delete(pattern)
    db.commit()

    return None


@router.delete("/by-text/{sentiment_type}/{pattern_text}", status_code=204)
def delete_pattern_by_text(
    sentiment_type: SentimentType,
    pattern_text: str,
    db: Session = Depends(get_db)
):
    """Delete a pattern by its text (for backward compatibility with existing API)"""
    pattern = db.query(Pattern).filter(
        Pattern.pattern_text == pattern_text.lower(),
        Pattern.sentiment_type == sentiment_type
    ).first()

    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    db.delete(pattern)
    db.commit()

    return None


# Pattern Match Endpoints

@router.post("/matches", response_model=PatternMatchResponse, status_code=201)
def create_pattern_match(
    match_data: PatternMatchCreate,
    db: Session = Depends(get_db)
):
    """
    Record a pattern match occurrence.

    This endpoint is called when a sentiment pattern is detected in a transcript segment.
    It tracks:
    - Which pattern was matched
    - What job/transcript it appeared in
    - The exact text that matched
    - Which competitor was mentioned
    - Timestamp and segment timing
    """
    # Verify pattern exists
    pattern = db.query(Pattern).filter(Pattern.id == match_data.pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Create the pattern match record
    new_match = PatternMatch(
        pattern_id=match_data.pattern_id,
        job_id=match_data.job_id,
        sentiment_result_id=match_data.sentiment_result_id,
        matched_text=match_data.matched_text,
        competitor_name=match_data.competitor_name,
        segment_start_time=match_data.segment_start_time,
        segment_end_time=match_data.segment_end_time
    )
    db.add(new_match)

    # Update pattern's match count and last matched timestamp
    pattern.match_count += 1
    pattern.last_matched_at = datetime.utcnow()

    db.commit()
    db.refresh(new_match)

    return new_match


@router.get("/{pattern_id}/matches", response_model=List[PatternMatchResponse])
def get_pattern_matches(
    pattern_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all matches for a specific pattern with optional date filtering"""
    query = db.query(PatternMatch).filter(PatternMatch.pattern_id == pattern_id)

    if start_date:
        query = query.filter(PatternMatch.detected_at >= start_date)

    if end_date:
        query = query.filter(PatternMatch.detected_at <= end_date)

    matches = query.order_by(PatternMatch.detected_at.desc()).offset(skip).limit(limit).all()
    return matches


# Analytics Endpoints

@router.get("/analytics/overview")
def get_pattern_analytics_overview(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get overall pattern analytics"""
    query = db.query(Pattern)

    # Get total patterns
    total_patterns = query.count()
    active_patterns = query.filter(Pattern.is_active == True).count()

    # Get match statistics
    match_query = db.query(PatternMatch)
    if start_date:
        match_query = match_query.filter(PatternMatch.detected_at >= start_date)
    if end_date:
        match_query = match_query.filter(PatternMatch.detected_at <= end_date)

    total_matches = match_query.count()

    # Top patterns by match count
    top_patterns = db.query(
        Pattern.id,
        Pattern.pattern_text,
        Pattern.sentiment_type,
        Pattern.match_count
    ).order_by(Pattern.match_count.desc()).limit(10).all()

    # Matches by sentiment type
    matches_by_sentiment = db.query(
        Pattern.sentiment_type,
        func.count(PatternMatch.id).label('count')
    ).join(PatternMatch).group_by(Pattern.sentiment_type).all()

    return {
        "total_patterns": total_patterns,
        "active_patterns": active_patterns,
        "total_matches": total_matches,
        "top_patterns": [
            {
                "id": str(p.id),
                "pattern_text": p.pattern_text,
                "sentiment_type": p.sentiment_type,
                "match_count": p.match_count
            }
            for p in top_patterns
        ],
        "matches_by_sentiment": [
            {"sentiment": s, "count": c}
            for s, c in matches_by_sentiment
        ]
    }


@router.get("/analytics/pattern/{pattern_id}")
def get_pattern_analytics(
    pattern_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get detailed analytics for a specific pattern"""
    pattern = db.query(Pattern).filter(Pattern.id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")

    # Build query
    query = db.query(PatternMatch).filter(PatternMatch.pattern_id == pattern_id)

    if start_date:
        query = query.filter(PatternMatch.detected_at >= start_date)
    if end_date:
        query = query.filter(PatternMatch.detected_at <= end_date)

    # Total matches in date range
    total_matches = query.count()

    # Matches by date (grouped by day)
    matches_by_date = db.query(
        func.date(PatternMatch.detected_at).label('date'),
        func.count(PatternMatch.id).label('count')
    ).filter(PatternMatch.pattern_id == pattern_id)

    if start_date:
        matches_by_date = matches_by_date.filter(PatternMatch.detected_at >= start_date)
    if end_date:
        matches_by_date = matches_by_date.filter(PatternMatch.detected_at <= end_date)

    matches_by_date = matches_by_date.group_by(func.date(PatternMatch.detected_at)).all()

    # Top competitors for this pattern
    top_competitors = db.query(
        PatternMatch.competitor_name,
        func.count(PatternMatch.id).label('count')
    ).filter(PatternMatch.pattern_id == pattern_id)

    if start_date:
        top_competitors = top_competitors.filter(PatternMatch.detected_at >= start_date)
    if end_date:
        top_competitors = top_competitors.filter(PatternMatch.detected_at <= end_date)

    top_competitors = top_competitors.group_by(
        PatternMatch.competitor_name
    ).order_by(func.count(PatternMatch.id).desc()).limit(10).all()

    # Calculate average matches per day
    if matches_by_date:
        avg_matches_per_day = total_matches / len(matches_by_date)
    else:
        avg_matches_per_day = 0

    return {
        "pattern_id": str(pattern.id),
        "pattern_text": pattern.pattern_text,
        "sentiment_type": pattern.sentiment_type,
        "total_matches": total_matches,
        "matches_by_date": [
            {"date": str(date), "count": count}
            for date, count in matches_by_date
        ],
        "top_competitors": [
            {"competitor": comp, "count": count}
            for comp, count in top_competitors
        ],
        "avg_matches_per_day": round(avg_matches_per_day, 2)
    }


@router.get("/analytics/trending")
def get_trending_patterns(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get trending patterns (most matched in recent days)"""
    start_date = datetime.utcnow() - timedelta(days=days)

    trending = db.query(
        Pattern.id,
        Pattern.pattern_text,
        Pattern.sentiment_type,
        func.count(PatternMatch.id).label('recent_matches')
    ).join(PatternMatch).filter(
        PatternMatch.detected_at >= start_date
    ).group_by(
        Pattern.id, Pattern.pattern_text, Pattern.sentiment_type
    ).order_by(func.count(PatternMatch.id).desc()).limit(limit).all()

    return {
        "period_days": days,
        "trending_patterns": [
            {
                "id": str(p.id),
                "pattern_text": p.pattern_text,
                "sentiment_type": p.sentiment_type,
                "recent_matches": p.recent_matches
            }
            for p in trending
        ]
    }
