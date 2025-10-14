#!/usr/bin/env python3
"""
Clear all records from the database.
WARNING: This will delete ALL jobs and sentiment results permanently!
"""

import sys
from orchestrator.app.database import SessionLocal, engine
from orchestrator.app import models

def clear_database():
    """Delete all records from jobs and sentiment_results tables."""
    db = SessionLocal()

    try:
        print("WARNING: This will delete ALL data from the database!")
        print("This action cannot be undone.")

        response = input("Are you sure you want to continue? (yes/no): ")

        if response.lower() != 'yes':
            print("Operation cancelled.")
            return

        # Count current records
        jobs_count = db.query(models.Job).count()
        sentiment_count = db.query(models.SentimentResult).count()

        print(f"\nFound {jobs_count} jobs and {sentiment_count} sentiment results.")
        print("Deleting...")

        # Delete all sentiment results first (due to foreign key constraint)
        deleted_sentiment = db.query(models.SentimentResult).delete()
        print(f"Deleted {deleted_sentiment} sentiment results.")

        # Delete all jobs
        deleted_jobs = db.query(models.Job).delete()
        print(f"Deleted {deleted_jobs} jobs.")

        # Commit the transaction
        db.commit()

        print("\n✓ Database cleared successfully!")

        # Verify
        remaining_jobs = db.query(models.Job).count()
        remaining_sentiment = db.query(models.SentimentResult).count()
        print(f"Remaining records: {remaining_jobs} jobs, {remaining_sentiment} sentiment results")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    clear_database()
