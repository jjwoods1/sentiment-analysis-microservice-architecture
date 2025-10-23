"""
Simple script to import patterns from text files in the container.
This script assumes the pattern files are at /app/positive_patterns.txt and /app/negative_patterns.txt

Run with:
    python /app/scripts/import_patterns_simple.py
"""

import sys
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Pattern, SentimentType

def import_from_file(file_path, sentiment_type):
    """Import patterns from a file"""
    added = 0
    skipped = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            db = SessionLocal()

            for line in f:
                line = line.strip().lower()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Check if pattern already exists
                existing = db.query(Pattern).filter(Pattern.pattern_text == line).first()

                if not existing:
                    try:
                        pattern = Pattern(
                            pattern_text=line,
                            sentiment_type=sentiment_type,
                            added_by='file_import',
                            notes='Imported from text file'
                        )
                        db.add(pattern)
                        db.commit()  # Commit each pattern individually
                        added += 1
                        print(f"✓ Added: {line}")
                    except Exception as e:
                        db.rollback()
                        print(f"⚠ Skipped (error): {line} - {str(e)}")
                        skipped += 1
                else:
                    skipped += 1

            db.close()

    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        print("Please copy pattern files to the container first:")
        print(f"  docker cp sentiment-analysis-tool-V1/positive_patterns.txt audio-orchestrator-api:/app/positive_patterns.txt")
        print(f"  docker cp sentiment-analysis-tool-V1/negative_patterns.txt audio-orchestrator-api:/app/negative_patterns.txt")
        return 0, 0

    return added, skipped


if __name__ == "__main__":
    print("="*60)
    print("Pattern Import Script")
    print("="*60)

    print("\nImporting positive patterns...")
    pos_added, pos_skipped = import_from_file('/app/positive_patterns.txt', SentimentType.POSITIVE)
    print(f"Positive patterns: {pos_added} added, {pos_skipped} skipped")

    print("\nImporting negative patterns...")
    neg_added, neg_skipped = import_from_file('/app/negative_patterns.txt', SentimentType.NEGATIVE)
    print(f"Negative patterns: {neg_added} added, {neg_skipped} skipped")

    print("\n" + "="*60)
    print("Import Summary:")
    print(f"  Total patterns added: {pos_added + neg_added}")
    print(f"  Total patterns skipped: {pos_skipped + neg_skipped}")
    print("="*60)

    # Verify import
    db = SessionLocal()
    total_patterns = db.query(Pattern).count()
    positive_count = db.query(Pattern).filter(Pattern.sentiment_type == SentimentType.POSITIVE).count()
    negative_count = db.query(Pattern).filter(Pattern.sentiment_type == SentimentType.NEGATIVE).count()
    db.close()

    print(f"\nDatabase now contains:")
    print(f"  Positive patterns: {positive_count}")
    print(f"  Negative patterns: {negative_count}")
    print(f"  Total: {total_patterns}")
    print("\n✓ Import complete!")
