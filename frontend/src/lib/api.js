import { browser } from '$app/environment';

// API URL - configure this to match your server
const API_URL = 'http://10.1.0.35:8100';

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
 * @returns {Promise<Object>}
 */
export async function getAnalyticsOverview() {
  const response = await fetch(`${API_URL}/analytics/overview`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch analytics');
  }

  return await response.json();
}

/**
 * Get competitor-specific analytics
 * @param {string} competitorName - The competitor name
 * @returns {Promise<Object>}
 */
export async function getCompetitorAnalytics(competitorName) {
  const response = await fetch(`${API_URL}/analytics/competitor/${encodeURIComponent(competitorName)}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch competitor analytics');
  }

  return await response.json();
}

/**
 * Get list of all competitors
 * @returns {Promise<{competitors: Array}>}
 */
export async function getAllCompetitors() {
  const response = await fetch(`${API_URL}/analytics/competitors/list`);

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
