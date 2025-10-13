import os
import re
from typing import List, Set
from .config import settings


class CompetitorAnalyzer:
    def __init__(self):
        self.competitors: Set[str] = set()
        self._load_competitors()

    def _load_competitors(self):
        """Load competitor names from the competitors.txt file."""
        competitors_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.competitors_file)

        try:
            with open(competitors_path, 'r', encoding='utf-8') as f:
                for line in f:
                    competitor = line.strip()
                    if competitor:
                        self.competitors.add(competitor.lower())
            print(f"Loaded {len(self.competitors)} competitors from {competitors_path}")
        except FileNotFoundError:
            print(f"Warning: Competitors file not found at {competitors_path}")
            self.competitors = set()

    def find_competitors(self, transcript_text: str) -> List[str]:
        """
        Find unique competitor mentions in the transcript text.

        Args:
            transcript_text: The full transcript text to analyze

        Returns:
            List of unique competitor names found in the text
        """
        if not transcript_text:
            return []

        # Convert transcript to lowercase for case-insensitive matching
        text_lower = transcript_text.lower()

        # Find all mentioned competitors
        found_competitors = set()

        for competitor in self.competitors:
            # Use word boundary matching to avoid partial matches
            # For example, "Amazon" should match "Amazon" but not "Amazonian"
            pattern = r'\b' + re.escape(competitor) + r'\b'
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Return the original casing from our competitor list
                # Find the original case from the competitors.txt file
                for original_competitor in self.competitors:
                    if original_competitor.lower() == competitor:
                        # Get the original case by reading from file again or storing it
                        found_competitors.add(competitor.title())
                        break

        return sorted(list(found_competitors))


# Global instance to be used across requests
analyzer = CompetitorAnalyzer()


def find_competitors(transcript_text: str) -> List[str]:
    """
    Public interface to find competitors in transcript text.

    Args:
        transcript_text: The full transcript text to analyze

    Returns:
        List of unique competitor names found in the text
    """
    return analyzer.find_competitors(transcript_text)
