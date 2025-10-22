"""
Script to import existing patterns from text files into the database.
Run this once to migrate from file-based patterns to database-based patterns.

Usage:
    python -m scripts.import_patterns_from_files
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Pattern, SentimentType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_patterns_from_file(file_path: str) -> list[str]:
    """Read patterns from a text file, filtering out comments and empty lines"""
    patterns = []

    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return patterns

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                patterns.append(line.lower())

    return patterns


def import_patterns(db: Session, patterns: list[str], sentiment_type: SentimentType, source_file: str):
    """Import patterns into the database"""
    added_count = 0
    skipped_count = 0

    for pattern_text in patterns:
        # Check if pattern already exists
        existing = db.query(Pattern).filter(Pattern.pattern_text == pattern_text).first()

        if existing:
            logger.info(f"Pattern already exists: '{pattern_text}'")
            skipped_count += 1
            continue

        # Create new pattern
        new_pattern = Pattern(
            pattern_text=pattern_text,
            sentiment_type=sentiment_type,
            added_by="migration_script",
            notes=f"Imported from {source_file}"
        )

        db.add(new_pattern)
        added_count += 1
        logger.info(f"Added pattern: '{pattern_text}' ({sentiment_type})")

    db.commit()

    return added_count, skipped_count


def main():
    """Main migration function"""
    logger.info("Starting pattern migration from text files to database")

    # Define file paths (adjust based on your project structure)
    positive_file = "../sentiment-analysis-tool-V1/positive_patterns.txt"
    negative_file = "../sentiment-analysis-tool-V1/negative_patterns.txt"

    # Try alternative paths if files not found
    if not os.path.exists(positive_file):
        positive_file = "sentiment-analysis-tool-V1/positive_patterns.txt"
    if not os.path.exists(negative_file):
        negative_file = "sentiment-analysis-tool-V1/negative_patterns.txt"

    # Read patterns from files
    logger.info(f"Reading positive patterns from: {positive_file}")
    positive_patterns = read_patterns_from_file(positive_file)
    logger.info(f"Found {len(positive_patterns)} positive patterns")

    logger.info(f"Reading negative patterns from: {negative_file}")
    negative_patterns = read_patterns_from_file(negative_file)
    logger.info(f"Found {len(negative_patterns)} negative patterns")

    # Create database session
    db = SessionLocal()

    try:
        # Import positive patterns
        logger.info("Importing positive patterns...")
        pos_added, pos_skipped = import_patterns(
            db,
            positive_patterns,
            SentimentType.POSITIVE,
            positive_file
        )

        # Import negative patterns
        logger.info("Importing negative patterns...")
        neg_added, neg_skipped = import_patterns(
            db,
            negative_patterns,
            SentimentType.NEGATIVE,
            negative_file
        )

        # Summary
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  Positive patterns - Added: {pos_added}, Skipped: {pos_skipped}")
        logger.info(f"  Negative patterns - Added: {neg_added}, Skipped: {neg_skipped}")
        logger.info(f"  Total - Added: {pos_added + neg_added}, Skipped: {pos_skipped + neg_skipped}")
        logger.info("=" * 60)
        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
