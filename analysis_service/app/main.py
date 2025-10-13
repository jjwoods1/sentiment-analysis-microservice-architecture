from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import logging
from datetime import datetime
from .logic import find_competitors

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Competitor Analysis Service")


class TranscriptRequest(BaseModel):
    transcript_text: str


class CompetitorResponse(BaseModel):
    competitors_found: List[str]
    count: int


@app.get("/")
async def root():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "Competitor Analysis Service"}


@app.get("/health")
async def health_check():
    """
    Comprehensive health check for analysis service.
    """
    try:
        # Test competitor list loading
        from .logic import CompetitorFinder
        finder = CompetitorFinder()
        competitor_count = len(finder.competitors)

        logger.info(f"Health check: Analysis service is healthy with {competitor_count} competitors loaded")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "analysis-api",
            "competitors_loaded": competitor_count
        }
    except Exception as e:
        logger.error(f"Health check: Analysis service is unhealthy - {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "analysis-api",
            "error": str(e)
        }


@app.post("/find-competitors", response_model=CompetitorResponse)
async def find_competitors_endpoint(request: TranscriptRequest):
    """
    Find unique competitor mentions in the provided transcript text.

    Args:
        request: TranscriptRequest containing the transcript_text

    Returns:
        CompetitorResponse with list of found competitors and count
    """
    competitors = find_competitors(request.transcript_text)

    return CompetitorResponse(
        competitors_found=competitors,
        count=len(competitors)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
