import { browser } from '$app/environment';

// API URL - configure this to match your server
const API_URL = 'http://10.1.0.35:8100';
const SENTIMENT_API_URL = 'http://10.1.0.35:8008';

/**
 * Upload an audio file for processing
 * @param {File} file - The audio file to upload
 * @returns {Promise<{job_id: string, message: string, status: string}>}
 */
export async function uploadAudioFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  return await response.json();
}

/**
 * Get all jobs with pagination
 * @param {number} skip - Number of jobs to skip
 * @param {number} limit - Maximum number of jobs to return
 * @returns {Promise<{total: number, jobs: Array}>}
 */
export async function getJobs(skip = 0, limit = 100) {
  const response = await fetch(`${API_URL}/jobs?skip=${skip}&limit=${limit}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch jobs');
  }

  return await response.json();
}

/**
 * Get a specific job by ID
 * @param {string} jobId - The job ID
 * @returns {Promise<Object>}
 */
export async function getJob(jobId) {
  const response = await fetch(`${API_URL}/jobs/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch job');
  }

  return await response.json();
}

/**
 * Format date string to readable format
 * @param {string} dateString - ISO date string
 * @returns {string}
 */
export function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString();
}

/**
 * Get status badge color class
 * @param {string} status - Job status
 * @returns {string}
 */
export function getStatusColor(status) {
  switch (status) {
    case 'COMPLETED':
      return 'success';
    case 'FAILED':
      return 'error';
    case 'PROCESSING':
      return 'info';
    case 'PENDING':
      return 'warning';
    default:
      return '';
  }
}

/**
 * Get analytics overview
 * @param {Object} params - Query parameters (start_date, end_date)
 * @returns {Promise<Object>}
 */
export async function getAnalyticsOverview(params = {}) {
  const queryString = new URLSearchParams(params).toString();
  const url = queryString ? `${API_URL}/analytics/overview?${queryString}` : `${API_URL}/analytics/overview`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch analytics');
  }

  return await response.json();
}

/**
 * Get competitor-specific analytics
 * @param {string} competitorName - The competitor name
 * @param {Object} params - Query parameters (start_date, end_date)
 * @returns {Promise<Object>}
 */
export async function getCompetitorAnalytics(competitorName, params = {}) {
  const queryString = new URLSearchParams(params).toString();
  const url = queryString
    ? `${API_URL}/analytics/competitor/${encodeURIComponent(competitorName)}?${queryString}`
    : `${API_URL}/analytics/competitor/${encodeURIComponent(competitorName)}`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch competitor analytics');
  }

  return await response.json();
}

/**
 * Get list of all competitors
 * @param {Object} params - Query parameters (start_date, end_date)
 * @returns {Promise<{competitors: Array}>}
 */
export async function getAllCompetitors(params = {}) {
  const queryString = new URLSearchParams(params).toString();
  const url = queryString ? `${API_URL}/analytics/competitors/list?${queryString}` : `${API_URL}/analytics/competitors/list`;
  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch competitors');
  }

  return await response.json();
}

/**
 * Get sentiment color class
 * @param {string} sentiment - Sentiment value
 * @returns {string}
 */
export function getSentimentColor(sentiment) {
  if (!sentiment) return '';
  const s = sentiment.toLowerCase();
  if (s.includes('positive')) return 'success';
  if (s.includes('negative')) return 'error';
  if (s.includes('neutral')) return 'info';
  return '';
}

/**
 * Get raw jobs table data
 * @param {number} limit - Maximum number of rows to return
 * @returns {Promise<Object>}
 */
export async function getJobsTable(limit = 1000) {
  const response = await fetch(`${API_URL}/admin/database/jobs?limit=${limit}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch jobs table');
  }

  return await response.json();
}

/**
 * Get raw sentiment_results table data
 * @param {number} limit - Maximum number of rows to return
 * @returns {Promise<Object>}
 */
export async function getSentimentResultsTable(limit = 1000) {
  const response = await fetch(`${API_URL}/admin/database/sentiment_results?limit=${limit}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch sentiment results table');
  }

  return await response.json();
}

/**
 * Get list of storage files
 * @returns {Promise<Object>}
 */
export async function getStorageFiles() {
  const response = await fetch(`${API_URL}/admin/storage/files`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch storage files');
  }

  return await response.json();
}

// ---------------------------
// Sentiment Pattern Management
// ---------------------------

/**
 * Get all patterns from the database with optional filtering
 * @param {string} sentimentType - Optional: 'positive', 'negative', or null for all
 * @param {boolean} activeOnly - Optional: only return active patterns
 * @returns {Promise<Array<Object>>} Array of pattern objects with id, pattern_text, sentiment_type, match_count, etc.
 */
export async function getPatterns(sentimentType = null, activeOnly = true) {
  let url = `${API_URL}/patterns/?skip=0&limit=1000`;
  if (sentimentType) {
    url += `&sentiment_type=${sentimentType}`;
  }
  if (activeOnly) {
    url += '&active_only=true';
  }

  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch patterns');
  }

  return await response.json();
}

/**
 * Get positive sentiment patterns
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function getPositivePatterns() {
  const patterns = await getPatterns('positive');
  return {
    patterns: patterns,
    count: patterns.length
  };
}

/**
 * Get negative sentiment patterns
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function getNegativePatterns() {
  const patterns = await getPatterns('negative');
  return {
    patterns: patterns,
    count: patterns.length
  };
}

/**
 * Create a new pattern in the database
 * @param {string} patternText - The pattern text
 * @param {string} sentimentType - 'positive' or 'negative'
 * @param {string} notes - Optional notes
 * @returns {Promise<Object>} The created pattern object
 */
export async function createPattern(patternText, sentimentType, notes = null) {
  const response = await fetch(`${API_URL}/patterns/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      pattern_text: patternText.toLowerCase().trim(),
      sentiment_type: sentimentType,
      notes: notes,
      added_by: 'web_interface'
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create pattern');
  }

  return await response.json();
}

/**
 * Add a positive sentiment pattern
 * @param {string} pattern - The pattern to add
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function addPositivePattern(pattern) {
  await createPattern(pattern, 'positive');
  return await getPositivePatterns();
}

/**
 * Add a negative sentiment pattern
 * @param {string} pattern - The pattern to add
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function addNegativePattern(pattern) {
  await createPattern(pattern, 'negative');
  return await getNegativePatterns();
}

/**
 * Bulk create patterns
 * @param {Array<string>} patterns - Array of pattern strings
 * @param {string} sentimentType - 'positive' or 'negative'
 * @returns {Promise<Object>}
 */
export async function bulkCreatePatterns(patterns, sentimentType) {
  const response = await fetch(`${API_URL}/patterns/bulk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      patterns: patterns.map(p => p.toLowerCase().trim()),
      sentiment_type: sentimentType,
      added_by: 'web_interface'
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to bulk create patterns');
  }

  return await response.json();
}

/**
 * Replace all positive patterns (bulk upload)
 * @param {Array<string>} patterns - List of patterns to set
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function replacePositivePatterns(patterns) {
  // For database, we add new patterns in bulk
  await bulkCreatePatterns(patterns, 'positive');
  return await getPositivePatterns();
}

/**
 * Replace all negative patterns (bulk upload)
 * @param {Array<string>} patterns - List of patterns to set
 * @returns {Promise<{patterns: Array<Object>, count: number}>}
 */
export async function replaceNegativePatterns(patterns) {
  // For database, we add new patterns in bulk
  await bulkCreatePatterns(patterns, 'negative');
  return await getNegativePatterns();
}

/**
 * Delete a pattern by ID
 * @param {string} patternId - The pattern UUID to delete
 * @returns {Promise<void>}
 */
export async function deletePattern(patternId) {
  const response = await fetch(`${API_URL}/patterns/${patternId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete pattern');
  }
}

/**
 * Delete a positive sentiment pattern
 * @param {Object} pattern - The pattern object with id
 * @returns {Promise<Object>}
 */
export async function deletePositivePattern(pattern) {
  const patternId = pattern.id || pattern;
  await deletePattern(patternId);
  return {};
}

/**
 * Delete a negative sentiment pattern
 * @param {Object} pattern - The pattern object with id
 * @returns {Promise<Object>}
 */
export async function deleteNegativePattern(pattern) {
  const patternId = pattern.id || pattern;
  await deletePattern(patternId);
  return {};
}

/**
 * Get pattern analytics overview
 * @param {string} startDate - Optional start date for filtering
 * @param {string} endDate - Optional end date for filtering
 * @returns {Promise<Object>} Analytics overview data
 */
export async function getPatternAnalyticsOverview(startDate = null, endDate = null) {
  let url = `${API_URL}/patterns/analytics/overview`;
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (params.toString()) url += `?${params.toString()}`;

  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch analytics overview');
  }

  return await response.json();
}

/**
 * Get detailed analytics for a specific pattern
 * @param {string} patternId - The pattern UUID
 * @param {string} startDate - Optional start date for filtering
 * @param {string} endDate - Optional end date for filtering
 * @returns {Promise<Object>} Pattern analytics with matches by date and competitors
 */
export async function getPatternAnalytics(patternId, startDate = null, endDate = null) {
  let url = `${API_URL}/patterns/analytics/pattern/${patternId}`;
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (params.toString()) url += `?${params.toString()}`;

  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch pattern analytics');
  }

  return await response.json();
}

/**
 * Get trending patterns (most matched recently)
 * @param {number} days - Number of days to look back (default 7)
 * @param {number} limit - Maximum number of patterns to return
 * @returns {Promise<Array>} Array of trending patterns
 */
export async function getTrendingPatterns(days = 7, limit = 10) {
  const url = `${API_URL}/patterns/analytics/trending?days=${days}&limit=${limit}`;

  const response = await fetch(url);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch trending patterns');
  }

  return await response.json();
}
