#!/bin/bash
# Setup script for pattern database tables and import existing patterns
# Run this script from the project root directory

set -e  # Exit on error

echo "=========================================="
echo "Pattern Database Setup Script"
echo "=========================================="
echo ""

# Step 1: Create database tables
echo "Step 1: Creating database tables..."
docker exec -i audio-postgres psql -U audiouser -d audiodb << 'EOF'
-- Create patterns table
CREATE TABLE IF NOT EXISTS patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_text VARCHAR NOT NULL UNIQUE,
    sentiment_type sentimenttype NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    match_count INTEGER NOT NULL DEFAULT 0,
    added_by VARCHAR,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_matched_at TIMESTAMP
);

-- Create indexes for patterns
CREATE INDEX IF NOT EXISTS ix_patterns_id ON patterns(id);
CREATE INDEX IF NOT EXISTS ix_patterns_pattern_text ON patterns(pattern_text);
CREATE INDEX IF NOT EXISTS ix_patterns_sentiment_type ON patterns(sentiment_type);
CREATE INDEX IF NOT EXISTS ix_patterns_is_active ON patterns(is_active);

-- Create pattern_matches table
CREATE TABLE IF NOT EXISTS pattern_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id UUID NOT NULL,
    job_id UUID NOT NULL,
    sentiment_result_id UUID NOT NULL,
    matched_text TEXT NOT NULL,
    competitor_name VARCHAR NOT NULL,
    segment_start_time FLOAT,
    segment_end_time FLOAT,
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_pattern FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE,
    CONSTRAINT fk_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    CONSTRAINT fk_sentiment_result FOREIGN KEY (sentiment_result_id) REFERENCES sentiment_results(id) ON DELETE CASCADE
);

-- Create indexes for pattern_matches
CREATE INDEX IF NOT EXISTS ix_pattern_matches_id ON pattern_matches(id);
CREATE INDEX IF NOT EXISTS ix_pattern_matches_pattern_id ON pattern_matches(pattern_id);
CREATE INDEX IF NOT EXISTS ix_pattern_matches_job_id ON pattern_matches(job_id);
CREATE INDEX IF NOT EXISTS ix_pattern_matches_sentiment_result_id ON pattern_matches(sentiment_result_id);
CREATE INDEX IF NOT EXISTS ix_pattern_matches_competitor_name ON pattern_matches(competitor_name);
CREATE INDEX IF NOT EXISTS ix_pattern_matches_detected_at ON pattern_matches(detected_at);

SELECT 'Tables created successfully!' as status;
EOF

echo "✓ Tables created"
echo ""

# Step 2: Mark migration as complete
echo "Step 2: Marking migration as complete..."
docker exec audio-orchestrator-api alembic stamp head
echo "✓ Migration stamped"
echo ""

# Step 3: Copy pattern files into container
echo "Step 3: Copying pattern files to container..."
docker cp sentiment-analysis-tool-V1/positive_patterns.txt audio-orchestrator-api:/app/positive_patterns.txt
docker cp sentiment-analysis-tool-V1/negative_patterns.txt audio-orchestrator-api:/app/negative_patterns.txt
echo "✓ Pattern files copied"
echo ""

# Step 4: Import patterns
echo "Step 4: Importing patterns from files..."
docker exec audio-orchestrator-api python /app/scripts/import_patterns_simple.py
echo ""

# Step 5: Verify setup
echo "Step 5: Verifying setup..."
PATTERN_COUNT=$(docker exec audio-postgres psql -U audiouser -d audiodb -t -c "SELECT COUNT(*) FROM patterns;")
echo "✓ Total patterns in database: $PATTERN_COUNT"
echo ""

echo "=========================================="
echo "✓ Setup complete!"
echo "=========================================="
echo ""
echo "Test the API:"
echo "  curl http://localhost:8100/patterns | jq"
echo ""
echo "View patterns in database:"
echo "  docker exec -it audio-postgres psql -U audiouser -d audiodb -c 'SELECT * FROM patterns LIMIT 10;'"
