#!/usr/bin/env python3
"""
Sentiment Analysis Tool

This script provides advanced sentiment analysis capabilities using:
1. Overall text sentiment analysis with DistilBERT or RoBERTa
2. Contextual sentiment analysis with Llama 2 7B

For usage instructions, see the accompanying README.md file or run with --help.
"""

import os
import sys
import subprocess
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
import logging
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sentiment_analysis")

# Constants
BASE_DIR = Path(__file__).parent.resolve()
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL", "http://orchestrator-api:8000")
LLM_DIR = BASE_DIR / ".models" / "llm"
LLM_MODEL_NAME = "llama-2-7b.Q4_K_M.gguf"
LLM_URL = "https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf"
MAX_TOKENS_FAST_MODEL = 512
FAST_MODEL_NAME = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
ROBERTA_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
MAX_LLM_CONTEXT = 512
MAX_RESPONSE_TOKENS = 300
NEGATIVE_PATTERNS_FILE = BASE_DIR / "negative_patterns.txt"
POSITIVE_PATTERNS_FILE = BASE_DIR / "positive_patterns.txt"
LLM_FALLBACK_LOG = BASE_DIR / "llm_fallback_segments.txt"

# Model selection - can be "llama" or "openai"
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "llama").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

# ---------------------------
# Imports - ML/AI dependencies
# ---------------------------
try:
    import torch
    from transformers import pipeline, AutoTokenizer
    from tqdm import tqdm
    import requests

    # Conditional imports based on selected model
    if SENTIMENT_MODEL == "llama":
        from llama_cpp import Llama
    elif SENTIMENT_MODEL == "openai":
        from openai import OpenAI
except ImportError as e:
    logger.error(f"Missing required dependency: {e}")
    logger.error("Please install dependencies using: pip install -r requirements.txt")
    sys.exit(1)

# ---------------------------
# Utility Functions
# ---------------------------
def download_llm_model() -> Path:
    """Download the LLM model if not already present."""
    LLM_DIR.mkdir(parents=True, exist_ok=True)
    model_path = LLM_DIR / LLM_MODEL_NAME
    
    if not model_path.exists():
        logger.info(f"Downloading {LLM_MODEL_NAME}...")
        response = requests.get(LLM_URL, stream=True)
        total = int(response.headers.get("content-length", 0))
        
        with open(model_path, "wb") as f, tqdm(
            desc=f"Downloading {LLM_MODEL_NAME}",
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                bar.update(size)
                
    return model_path

# Pattern cache to avoid hitting API on every call
_pattern_cache = {
    'positive': {'patterns': [], 'patterns_dict': {}, 'last_updated': None},
    'negative': {'patterns': [], 'patterns_dict': {}, 'last_updated': None}
}
_CACHE_DURATION = timedelta(minutes=5)  # Refresh cache every 5 minutes


def load_patterns_from_api(sentiment_type: str) -> Tuple[List[str], Dict[str, str]]:
    """
    Load sentiment patterns from the orchestrator API database.
    Uses caching to avoid excessive API calls.

    Args:
        sentiment_type: "positive" or "negative"

    Returns:
        Tuple of (patterns_list, patterns_dict) where patterns_dict maps pattern_text to pattern_id
    """
    global _pattern_cache

    # Check cache
    cache_entry = _pattern_cache.get(sentiment_type)
    if cache_entry and cache_entry['last_updated']:
        if datetime.now() - cache_entry['last_updated'] < _CACHE_DURATION:
            logger.debug(f"Using cached {sentiment_type} patterns")
            return cache_entry['patterns'], cache_entry['patterns_dict']

    # Fetch from API
    try:
        url = f"{ORCHESTRATOR_API_URL}/patterns/?sentiment_type={sentiment_type}&is_active=true&limit=10000"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        patterns = []
        patterns_dict = {}

        for pattern_obj in data:
            pattern_text = pattern_obj['pattern_text'].lower()
            pattern_id = pattern_obj['id']
            patterns.append(pattern_text)
            patterns_dict[pattern_text] = pattern_id

        # Update cache
        _pattern_cache[sentiment_type] = {
            'patterns': patterns,
            'patterns_dict': patterns_dict,
            'last_updated': datetime.now()
        }

        logger.info(f"Loaded {len(patterns)} {sentiment_type} patterns from database")
        return patterns, patterns_dict

    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading patterns from API: {e}")
        logger.warning(f"Falling back to file-based patterns for {sentiment_type}")

        # Fallback to file-based patterns
        file_path = POSITIVE_PATTERNS_FILE if sentiment_type == "positive" else NEGATIVE_PATTERNS_FILE
        patterns = load_patterns_from_file(file_path)
        patterns_dict = {}  # No IDs available from files

        return patterns, patterns_dict


def load_patterns_from_file(file_path: Path) -> List[str]:
    """
    Load sentiment patterns from a text file (fallback method).

    Args:
        file_path: Path to the patterns file

    Returns:
        List of patterns (lines that don't start with # and aren't empty)
    """
    patterns = []
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line.lower())
            logger.info(f"Loaded {len(patterns)} patterns from {file_path.name}")
        else:
            logger.warning(f"Pattern file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error loading patterns from {file_path}: {e}")

    return patterns

def detect_sentiment_keywords(text: str, context: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Use rule-based detection for strong sentiment indicators.

    Args:
        text: The text to analyze
        context: The context word to focus on

    Returns:
        Tuple of (sentiment, matched_pattern, pattern_id) where:
        - sentiment is "positive", "negative", "neutral", or None
        - matched_pattern is the pattern text that was matched, or None
        - pattern_id is the database ID of the matched pattern, or None
    """
    text_lower = text.lower()
    context_lower = context.lower()

    # Create flexible pattern that works with alphanumeric brand names (e.g., "O2", "3G", "4G")
    escaped_context = re.escape(context_lower)
    context_pattern = re.compile(
        r'(?:^|(?<=\s))' + escaped_context + r'(?=\s|[.,!?;:]|$)',
        re.IGNORECASE
    )
    if context_pattern.search(text):
        # Load patterns from database API (with fallback to files)
        negative_patterns, neg_dict = load_patterns_from_api("negative")
        positive_patterns, pos_dict = load_patterns_from_api("positive")

        # Check for negative sentiment patterns
        for pattern in negative_patterns:
            if pattern in text_lower:
                pattern_id = neg_dict.get(pattern)
                logger.info(f"Rule-based detection found negative pattern '{pattern}' (ID: {pattern_id}) in text")
                return "negative", pattern, pattern_id

        # Check for positive sentiment patterns
        for pattern in positive_patterns:
            if pattern in text_lower:
                pattern_id = pos_dict.get(pattern)
                logger.info(f"Rule-based detection found positive pattern '{pattern}' (ID: {pattern_id}) in text")
                return "positive", pattern, pattern_id

    # No strong sentiment found
    return None, None, None

def validate_json_against_schema(json_data: Dict[str, Any], schema_file: str) -> bool:
    """Validate a JSON object against a schema."""
    try:
        logger.info(f"Validating JSON with keys: {list(json_data.keys())}")
        logger.info(f"JSON data type: {type(json_data)}")

        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        # Basic validation (more comprehensive validation would use jsonschema library)
        required_keys = schema.get("required", [])
        logger.info(f"Schema requires keys: {required_keys}")

        for key in required_keys:
            if key not in json_data:
                logger.error(f"Missing required key: {key}")
                logger.error(f"Available keys in json_data: {list(json_data.keys())}")
                return False

        # Check segments structure for transcripts
        if "segments" in json_data:
            logger.info(f"Validating {len(json_data['segments'])} segments")
            for i, segment in enumerate(json_data["segments"]):
                required_segment_keys = ["id", "start", "end", "text"]
                for seg_key in required_segment_keys:
                    if seg_key not in segment:
                        logger.error(f"Invalid segment {i}: missing required field '{seg_key}'")
                        logger.error(f"Segment has keys: {list(segment.keys())}")
                        return False

        logger.info("Validation passed")
        return True
    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return False

def load_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a file based on its extension."""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            if file_path.endswith(".json"):
                return json.load(f)
            else:
                # For plain text files, return a simple dict with text content
                return {"text": f.read()}
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        sys.exit(1)

def analyze_sentiment_with_openai(segment_text: str, context: str) -> tuple[str, str]:
    """
    Analyze sentiment using OpenAI API.

    Args:
        segment_text: The text segment to analyze
        context: The context word to focus on

    Returns:
        Tuple of (sentiment, details) where sentiment is "positive", "negative", or "neutral"
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable not set")
        return "neutral", "Error: No API key provided"

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""Analyze sentiment about "{context}" in this text: "{segment_text}"

Rules:
- Only sentiment about "{context}" matters
- Handle negation (e.g., "not good" = negative)
- Questions, factual statements, introductions, and identification statements = neutral
- Factual examples: "calling from {context}", "this is {context}", "speaking from {context}", "representative from {context}" = neutral
- Only emotional or evaluative statements about {context} can be positive or negative
- If there is no emotional opinion expressed about {context}, classify as neutral
- Mixed sentiment = use the stronger one

Respond ONLY with valid JSON in this exact format:
{{"sentiment": "positive"}} OR {{"sentiment": "negative"}} OR {{"sentiment": "neutral"}}"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a sentiment analysis assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )

        response_text = response.choices[0].message.content.strip()

        # Parse the JSON response
        sentiment = None

        # Strategy 1: Try to parse as JSON
        try:
            parsed = json.loads(response_text)
            if "sentiment" in parsed:
                sentiment = parsed["sentiment"].lower()
        except json.JSONDecodeError:
            # Strategy 2: Look for sentiment value in quotes
            value_match = re.search(r'"sentiment"\s*:\s*"(positive|negative|neutral)"', response_text, re.IGNORECASE)
            if value_match:
                sentiment = value_match.group(1).lower()
            else:
                # Strategy 3: Look for just the sentiment word
                word_match = re.search(r'\b(positive|negative|neutral)\b', response_text, re.IGNORECASE)
                if word_match:
                    sentiment = word_match.group(1).lower()

        if sentiment and sentiment in ["positive", "negative", "neutral"]:
            return sentiment, f"Model: {OPENAI_MODEL_NAME}"
        else:
            logger.warning(f"Invalid OpenAI response: {response_text}")
            return "neutral", f"Failed to parse OpenAI response, defaulted to neutral"

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return "neutral", f"API error: {str(e)}"

def analyze_sentiment_with_llama(segment_text: str, context: str, llm) -> tuple[str, str]:
    """
    Analyze sentiment using local Llama model.

    Args:
        segment_text: The text segment to analyze
        context: The context word to focus on
        llm: The loaded Llama model instance

    Returns:
        Tuple of (sentiment, details) where sentiment is "positive", "negative", or "neutral"
    """
    class DevNull:
        def write(self, msg): pass
        def flush(self): pass

    prompt = f"""Analyze sentiment about "{context}" in this text: "{segment_text}"

Rules:
- Only sentiment about "{context}" matters
- Handle negation (e.g., "not good" = negative)
- Questions, factual statements, introductions, and identification statements = neutral
- Factual examples: "calling from {context}", "this is {context}", "speaking from {context}", "representative from {context}" = neutral
- Only emotional or evaluative statements about {context} can be positive or negative
- If there is no emotional opinion expressed about {context}, classify as neutral
- Mixed sentiment = use the stronger one

Respond ONLY with valid JSON in this exact format:
{{"sentiment": "positive"}} OR {{"sentiment": "negative"}} OR {{"sentiment": "neutral"}}

JSON response:"""

    try:
        _stdout, _stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = DevNull()
        response = llm(
            prompt,
            max_tokens=120,
            temperature=0.1,
            top_p=0.9,
            stop=["\n\n", "Explanation:", "Note:"],
            repeat_penalty=1.1
        )
    finally:
        sys.stdout, sys.stderr = _stdout, _stderr

    # Parse JSON response
    try:
        llm_response_text = response['choices'][0]['text'].strip()
        sentiment = None

        # Strategy 1: Try to find ANY JSON object with sentiment key
        json_matches = re.finditer(r'\{[^}]*\}', llm_response_text)
        for match in json_matches:
            try:
                potential_json = match.group(0)
                parsed = json.loads(potential_json)
                if "sentiment" in parsed:
                    sentiment = parsed["sentiment"].lower()
                    logger.info(f"✓ Extracted JSON: {potential_json}")
                    break
            except json.JSONDecodeError:
                continue

        # Strategy 2: Look for sentiment value directly in quotes
        if not sentiment:
            value_match = re.search(r'"sentiment"\s*:\s*"(positive|negative|neutral)"', llm_response_text, re.IGNORECASE)
            if value_match:
                sentiment = value_match.group(1).lower()
                logger.info(f"✓ Extracted sentiment from pattern: {sentiment}")

        # Strategy 3: Look for just the sentiment words
        if not sentiment:
            word_match = re.search(r'\b(positive|negative|neutral)\b', llm_response_text, re.IGNORECASE)
            if word_match:
                sentiment = word_match.group(1).lower()
                logger.info(f"✓ Extracted sentiment word: {sentiment}")

        if sentiment and sentiment in ["positive", "negative", "neutral"]:
            return sentiment, "Model: Llama 2 7B"
        else:
            raise ValueError(f"Invalid or missing sentiment value: {sentiment}")

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"✗ PARSING FAILED: {type(e).__name__}: {e}")
        return "neutral", "Failed to parse LLM response, defaulted to neutral"
    except Exception as e:
        logger.error(f"✗ PARSING FAILED: {type(e).__name__}: {e}")
        return "neutral", f"Failed to parse LLM response (error: {str(e)}), defaulted to neutral"

# ---------------------------
# Sentiment Analysis Functions
# ---------------------------
def analyze_overall_sentiment(file_path: str, model_name: str = "roberta") -> Dict[str, Any]:
    """
    Analyze overall sentiment of text using the specified model.
    
    Args:
        file_path: Path to the file to analyze
        model_name: Model to use - either 'distilbert' or 'roberta'
    """
    logger.info(f"Starting overall sentiment analysis using {model_name} model...")
    
    # Load the file content
    data = load_file(file_path)
    text = data.get("text", "")
    
    if not text:
        logger.error(f"No text content found in {file_path}")
        sys.exit(1)
    
    # Select the model to use
    if model_name == "distilbert":
        model = FAST_MODEL_NAME
        tokenizer_name = FAST_MODEL_NAME
    else:  # default to roberta
        model = ROBERTA_MODEL_NAME
        tokenizer_name = ROBERTA_MODEL_NAME
    
    # Initialize tokenizer for chunking text
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    
    def chunk_text(text, chunk_size=MAX_TOKENS_FAST_MODEL):
        tokens = tokenizer.encode(text, truncation=False)
        for i in range(0, len(tokens), chunk_size):
            yield tokenizer.decode(tokens[i:i + chunk_size], clean_up_tokenization_spaces=True)
    
    # Set up sentiment analysis pipeline
    device = 0 if torch.cuda.is_available() else -1
    sentiment_pipe = pipeline(
        "sentiment-analysis",
        model=model,
        device=device,
        tokenizer=tokenizer_name
    )
    
    # Process text in chunks
    chunks = list(chunk_text(text))
    results = []
    
    for chunk in tqdm(chunks, desc="Analyzing sentiment", ncols=80):
        res = sentiment_pipe(chunk, truncation=True, max_length=MAX_TOKENS_FAST_MODEL)
        results.extend(res)
    
    # Count sentiment results based on model output format
    if model_name == "distilbert":
        pos = sum(1 for r in results if r['label'].lower().startswith("pos"))
        neg = sum(1 for r in results if r['label'].lower().startswith("neg"))
        neutral = sum(1 for r in results if r['label'].lower().startswith("neu"))
    else:  # roberta model uses different label format
        pos = sum(1 for r in results if r['label'].lower() == "positive")
        neg = sum(1 for r in results if r['label'].lower() == "negative")
        neutral = sum(1 for r in results if r['label'].lower() == "neutral")
    
    # Determine overall sentiment
    if pos > neg and pos > neutral:
        overall = "positive"
    elif neg > pos and neg > neutral:
        overall = "negative"
    else:
        overall = "neutral"
    
    # Format results according to specified output structure
    output = {
        "overall_sentiment": overall,
        "positive": pos,
        "neutral": neutral,
        "negative": neg,
        "metadata": {
            "model_used": model_name,
            "model_full_name": model,
            "total_chunks_analyzed": len(chunks),
            "device": "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
        }
    }

    logger.info(f"Overall sentiment analysis complete: {overall}")
    return output

def analyze_contextual_sentiment(file_path: str, context: str) -> Dict[str, Any]:
    """Analyze contextual sentiment using LLM (Llama 2 or OpenAI) combined with rule-based detection."""
    logger.info(f"Starting contextual sentiment analysis for context: {context}...")
    logger.info(f"Using sentiment model: {SENTIMENT_MODEL}")

    # Validate the input file against the transcript schema
    schema_path = os.path.join(BASE_DIR, "transcript-schema.json")
    data = load_file(file_path)
    
    if not validate_json_against_schema(data, schema_path):
        logger.error(f"Invalid transcript format in {file_path}")
        sys.exit(1)
    
    # Extract segments from the transcript
    segments = data.get("segments", [])
    if not segments:
        logger.error("No segments found in the transcript")
        sys.exit(1)
    
    # Find segments containing the context word
    context_segments = []
    # Create flexible pattern that works with alphanumeric brand names (e.g., "O2", "3G", "4G")
    # Use word boundaries but handle cases where boundaries don't work (alphanumeric)
    escaped_context = re.escape(context.lower())
    # Try word boundary match, but also allow standalone match for alphanumeric terms
    context_pattern = re.compile(
        r'(?:^|(?<=\s))' + escaped_context + r'(?=\s|[.,!?;:]|$)',
        re.IGNORECASE
    )

    for segment in segments:
        segment_text = segment.get("text", "")
        # Skip segments with only one word (single-word segments are too short for sentiment analysis)
        word_count = len(segment_text.split())
        if word_count <= 1:
            logger.debug(f"Skipping single-word segment {segment.get('id')}: '{segment_text}'")
            continue
        if context_pattern.search(segment_text):
            context_segments.append(segment)
    
    if not context_segments:
        logger.warning(f"Context '{context}' not found in any segment")
        return {
            "context": context,
            "overall_sentiment": "neutral",
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "segments": []
        }
    
    # Load the LLM model (only for Llama, not needed for OpenAI)
    llm = None
    if SENTIMENT_MODEL == "llama":
        logger.info("Loading Llama model for contextual analysis...")
        model_path = download_llm_model()

        # Suppress llama_cpp logs and prints
        logging.getLogger("llama_cpp").setLevel(logging.CRITICAL)

        class DevNull:
            def write(self, msg): pass
            def flush(self): pass

        try:
            _stdout, _stderr = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = DevNull()
            llm = Llama(model_path=str(model_path), n_ctx=1024)
        finally:
            sys.stdout, sys.stderr = _stdout, _stderr
    elif SENTIMENT_MODEL == "openai":
        logger.info("Using OpenAI API for contextual analysis...")
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY environment variable not set")
            sys.exit(1)
    else:
        logger.error(f"Invalid SENTIMENT_MODEL: {SENTIMENT_MODEL}. Must be 'llama' or 'openai'")
        sys.exit(1)
    
    # Process each segment containing the context
    pos = neg = neutral = 0
    result_segments = []
    
    for segment in tqdm(context_segments, desc="Analyzing segments", ncols=80):
        segment_text = segment.get("text", "")

        # First check for strong sentiment indicators with rule-based approach
        rule_sentiment, matched_pattern, pattern_id = detect_sentiment_keywords(segment_text, context)

        detection_method = None
        detection_details = None

        if rule_sentiment:
            # Strong rule-based sentiment found, use it
            sentiment = rule_sentiment
            detection_method = "rule-based"
            detection_details = f"Matched pattern: '{matched_pattern}'"

            # Enhanced logging for rule-based detection
            logger.info("="*80)
            logger.info(f"SEGMENT {segment.get('id')} RULE-BASED DETECTION")
            logger.info(f"Context: {context}")
            logger.info(f"Segment Text: {segment_text}")
            logger.info(f"✓ Matched Pattern: '{matched_pattern}' (ID: {pattern_id})")
            logger.info(f"✓ Detected Sentiment: {sentiment}")
            logger.info("="*80)
        else:
            # No pattern match - log this segment for future pattern updates
            logger.info("="*80)
            logger.info(f"SEGMENT {segment.get('id')} - NO PATTERN MATCH (Falling back to LLM)")
            logger.info(f"Context: {context}")
            logger.info(f"Segment Text: {segment_text}")
            logger.info("="*80)

            # Save segment to LLM fallback log file
            try:
                from datetime import datetime
                with open(LLM_FALLBACK_LOG, 'a', encoding='utf-8') as fallback_file:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    fallback_file.write(f"\n{'='*80}\n")
                    fallback_file.write(f"Timestamp: {timestamp}\n")
                    fallback_file.write(f"Context: {context}\n")
                    fallback_file.write(f"Segment ID: {segment.get('id')}\n")
                    fallback_file.write(f"Segment Text: {segment_text}\n")
                    fallback_file.write(f"{'='*80}\n")
                logger.info(f"Saved segment to LLM fallback log: {LLM_FALLBACK_LOG}")
            except Exception as e:
                logger.warning(f"Failed to save segment to fallback log: {e}")

            # Use LLM for sentiment analysis
            if SENTIMENT_MODEL == "openai":
                sentiment, detection_details = analyze_sentiment_with_openai(segment_text, context)
                detection_method = "llm-based-openai"
            else:  # llama
                sentiment, detection_details = analyze_sentiment_with_llama(segment_text, context, llm)
                detection_method = "llm-based-llama"

            # Log the LLM analysis result
            logger.info("="*80)
            logger.info(f"SEGMENT {segment.get('id')} LLM ANALYSIS")
            logger.info(f"Context: {context}")
            logger.info(f"Segment Text: {segment_text}")
            logger.info(f"✓ Detected Sentiment: {sentiment}")
            logger.info(f"✓ Detection Details: {detection_details}")
            logger.info("="*80)

        # Update counters
        if sentiment == "positive":
            pos += 1
        elif sentiment == "negative":
            neg += 1
        else:
            neutral += 1

        # Add segment to results with start and end times
        segment_result = {
            "segment-id": segment.get("id"),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "text": segment_text,
            "sentiment": sentiment,
            "detection_method": detection_method,
            "detection_details": detection_details
        }

        # Add pattern tracking info if available
        if pattern_id and matched_pattern:
            segment_result["pattern_id"] = pattern_id
            segment_result["matched_pattern"] = matched_pattern

        result_segments.append(segment_result)
    
    # Determine overall sentiment
    if pos > neg and pos > neutral:
        overall = "positive"
    elif neg > pos and neg > neutral:
        overall = "negative"
    else:
        overall = "neutral"
    
    # Format results according to specified output structure
    output = {
        "context": context,
        "overall_sentiment": overall,
        "positive": pos,
        "neutral": neutral,
        "negative": neg,
        "segments": result_segments,
        "metadata": {
            "total_segments_analyzed": len(result_segments),
            "total_segments_in_transcript": len(segments),
            "pattern_files_loaded": {
                "positive_patterns": str(POSITIVE_PATTERNS_FILE),
                "negative_patterns": str(NEGATIVE_PATTERNS_FILE)
            },
            "analysis_methods_used": list(set([seg["detection_method"] for seg in result_segments]))
        }
    }

    logger.info(f"Contextual sentiment analysis complete for '{context}': {overall}")
    return output

# ---------------------------
# Main CLI Interface
# ---------------------------
def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Advanced Sentiment Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --type overall --model roberta --file path/to/text.txt
  %(prog)s --type contextual --file path/to/transcript.json --context Vodafone
        """
    )
    
    parser.add_argument(
        "--type", "-t", 
        choices=["overall", "contextual"], 
        help="Type of sentiment analysis to perform"
    )
    
    parser.add_argument(
        "--model", "-m",
        choices=["distilbert", "roberta"],
        default="roberta",
        help="Model to use for overall sentiment analysis (default: roberta)"
    )
    
    parser.add_argument(
        "--file", "-f", 
        type=str, 
        help="Path to the input file"
    )
    
    parser.add_argument(
        "--context", "-c", 
        type=str, 
        help="Context word for contextual analysis (required for contextual analysis)"
    )
    
    parser.add_argument(
        "--output", "-o", 
        type=str, 
        help="Path to save the output JSON (if not provided, prints to stdout)"
    )
    
    args = parser.parse_args()
    
    # Interactive mode if required arguments are missing
    analysis_type = args.type or input("Enter analysis type (overall/contextual): ").strip().lower()
    
    if analysis_type not in ["overall", "contextual"]:
        logger.error("Invalid analysis type. Must be 'overall' or 'contextual'.")
        sys.exit(1)
    
    file_path = args.file or input("Enter path to file for analysis: ").strip()
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    # Run the appropriate analysis
    if analysis_type == "overall":
        model_name = args.model or input("Enter model name (distilbert/roberta): ").strip().lower() or "roberta"
        if model_name not in ["distilbert", "roberta"]:
            logger.error("Invalid model name. Must be 'distilbert' or 'roberta'.")
            sys.exit(1)
        
        result = analyze_overall_sentiment(file_path, model_name)
    else:  # contextual
        context = args.context or input("Enter context word for analysis: ").strip()
        if not context:
            logger.error("Context is required for contextual analysis.")
            sys.exit(1)
        
        result = analyze_contextual_sentiment(file_path, context)
    
    # Output the results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        sys.exit(1)
