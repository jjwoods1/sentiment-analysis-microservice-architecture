<script>
  import { onMount } from 'svelte';
  import { getJobsTable, getSentimentResultsTable, getStorageFiles } from '$lib/api.js';

  let activeTab = 'jobs';
  let loading = false;
  let error = null;

  // Jobs table data
  let jobsData = null;

  // Sentiment results table data
  let sentimentData = null;

  // Storage files data
  let storageData = null;

  // Search/filter
  let searchTerm = '';

  onMount(async () => {
    await loadJobsTable();
  });

  async function loadJobsTable() {
    loading = true;
    error = null;
    try {
      jobsData = await getJobsTable(1000);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function loadSentimentTable() {
    loading = true;
    error = null;
    try {
      sentimentData = await getSentimentResultsTable(1000);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function loadStorageFiles() {
    loading = true;
    error = null;
    try {
      storageData = await getStorageFiles();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function switchTab(tab) {
    activeTab = tab;
    searchTerm = '';

    if (tab === 'jobs' && !jobsData) {
      await loadJobsTable();
    } else if (tab === 'sentiment' && !sentimentData) {
      await loadSentimentTable();
    } else if (tab === 'storage' && !storageData) {
      await loadStorageFiles();
    }
  }

  function filterRows(rows, term) {
    if (!term) return rows;
    const lowerTerm = term.toLowerCase();
    return rows.filter(row => {
      return JSON.stringify(row).toLowerCase().includes(lowerTerm);
    });
  }

  function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    alert('Copied to clipboard!');
  }

  $: filteredJobs = jobsData ? filterRows(jobsData.rows, searchTerm) : [];
  $: filteredSentiment = sentimentData ? filterRows(sentimentData.rows, searchTerm) : [];
  $: filteredStorage = storageData ? filterRows(storageData.objects || [], searchTerm) : [];
</script>

<div class="admin-container">
  <div class="admin-header">
    <h1>Admin / Database Viewer</h1>
    <p>View and export raw database tables and storage files</p>
  </div>

  <!-- Tab Navigation -->
  <div class="tabs">
    <button
      class="tab {activeTab === 'jobs' ? 'active' : ''}"
      on:click={() => switchTab('jobs')}
    >
      Jobs Table
      {#if jobsData}
        <span class="badge">{jobsData.count}</span>
      {/if}
    </button>
    <button
      class="tab {activeTab === 'sentiment' ? 'active' : ''}"
      on:click={() => switchTab('sentiment')}
    >
      Sentiment Results
      {#if sentimentData}
        <span class="badge">{sentimentData.count}</span>
      {/if}
    </button>
    <button
      class="tab {activeTab === 'storage' ? 'active' : ''}"
      on:click={() => switchTab('storage')}
    >
      Storage Files
      {#if storageData}
        <span class="badge">{storageData.count}</span>
      {/if}
    </button>
  </div>

  <!-- Search and Export Controls -->
  <div class="controls">
    <input
      type="text"
      placeholder="Search..."
      bind:value={searchTerm}
      class="search-input"
    />
    {#if activeTab === 'jobs' && jobsData}
      <button on:click={() => downloadJSON(jobsData, 'jobs-table.json')} class="btn-export">
        Export Jobs JSON
      </button>
    {/if}
    {#if activeTab === 'sentiment' && sentimentData}
      <button on:click={() => downloadJSON(sentimentData, 'sentiment-results.json')} class="btn-export">
        Export Sentiment JSON
      </button>
    {/if}
    {#if activeTab === 'storage' && storageData}
      <button on:click={() => downloadJSON(storageData, 'storage-files.json')} class="btn-export">
        Export Files List JSON
      </button>
    {/if}
  </div>

  <!-- Loading / Error States -->
  {#if loading}
    <div class="loading">Loading...</div>
  {/if}

  {#if error}
    <div class="error">Error: {error}</div>
  {/if}

  <!-- Jobs Table -->
  {#if activeTab === 'jobs' && jobsData && !loading}
    <div class="table-container">
      <h2>Jobs Table ({filteredJobs.length} rows)</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Filename</th>
              <th>Status</th>
              <th>Error Message</th>
              <th>Left Channel URL</th>
              <th>Right Channel URL</th>
              <th>Left Transcript Path</th>
              <th>Right Transcript Path</th>
              <th>Competitors Found</th>
              <th>Created At</th>
              <th>Updated At</th>
              <th>Completed At</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredJobs as job}
              <tr>
                <td class="mono">
                  <button on:click={() => copyToClipboard(job.id)} class="copy-btn" title="Copy ID">
                    {job.id.substring(0, 8)}...
                  </button>
                </td>
                <td>{job.filename || '-'}</td>
                <td>
                  <span class="status-badge {job.status.toLowerCase()}">{job.status}</span>
                </td>
                <td class="error-cell">{job.error_message || '-'}</td>
                <td class="url-cell">{job.left_channel_url || '-'}</td>
                <td class="url-cell">{job.right_channel_url || '-'}</td>
                <td class="path-cell">{job.left_transcript_path || '-'}</td>
                <td class="path-cell">{job.right_transcript_path || '-'}</td>
                <td>{job.competitors_found ? job.competitors_found.join(', ') : '-'}</td>
                <td class="date-cell">{job.created_at || '-'}</td>
                <td class="date-cell">{job.updated_at || '-'}</td>
                <td class="date-cell">{job.completed_at || '-'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  <!-- Sentiment Results Table -->
  {#if activeTab === 'sentiment' && sentimentData && !loading}
    <div class="table-container">
      <h2>Sentiment Results Table ({filteredSentiment.length} rows)</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Job ID</th>
              <th>Competitor</th>
              <th>Result JSON</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredSentiment as result}
              <tr>
                <td class="mono">
                  <button on:click={() => copyToClipboard(result.id)} class="copy-btn" title="Copy ID">
                    {result.id.substring(0, 8)}...
                  </button>
                </td>
                <td class="mono">
                  <button on:click={() => copyToClipboard(result.job_id)} class="copy-btn" title="Copy Job ID">
                    {result.job_id.substring(0, 8)}...
                  </button>
                </td>
                <td>{result.competitor_name}</td>
                <td class="json-cell">
                  <details>
                    <summary>View JSON</summary>
                    <pre>{JSON.stringify(result.result_json, null, 2)}</pre>
                  </details>
                </td>
                <td class="date-cell">{result.created_at || '-'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}

  <!-- Storage Files -->
  {#if activeTab === 'storage' && storageData && !loading}
    <div class="table-container">
      <h2>Storage Files ({filteredStorage.length} files)</h2>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Object Name</th>
              <th>Size</th>
              <th>Last Modified</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredStorage as file}
              <tr>
                <td class="path-cell">
                  <button on:click={() => copyToClipboard(file.object_name)} class="copy-btn" title="Copy path">
                    {file.object_name}
                  </button>
                </td>
                <td>{file.size ? `${(file.size / 1024).toFixed(2)} KB` : '-'}</td>
                <td class="date-cell">{file.last_modified || '-'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<style>
  .admin-container {
    max-width: 1600px;
    margin: 0 auto;
    padding: 2rem;
  }

  .admin-header {
    margin-bottom: 2rem;
  }

  .admin-header h1 {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
  }

  .admin-header p {
    color: #666;
  }

  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    border-bottom: 2px solid #e5e7eb;
  }

  .tab {
    padding: 0.75rem 1.5rem;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    font-weight: 500;
    color: #6b7280;
    transition: all 0.2s;
    position: relative;
  }

  .tab:hover {
    color: #111827;
    background: #f9fafb;
  }

  .tab.active {
    color: #2563eb;
    border-bottom-color: #2563eb;
  }

  .badge {
    display: inline-block;
    background: #e5e7eb;
    color: #374151;
    padding: 0.125rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    margin-left: 0.5rem;
  }

  .tab.active .badge {
    background: #dbeafe;
    color: #1e40af;
  }

  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    align-items: center;
  }

  .search-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 1rem;
  }

  .btn-export {
    padding: 0.75rem 1.5rem;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: background 0.2s;
  }

  .btn-export:hover {
    background: #1d4ed8;
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: #6b7280;
    font-size: 1.125rem;
  }

  .error {
    background: #fee2e2;
    color: #991b1b;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
  }

  .table-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .table-container h2 {
    padding: 1rem 1.5rem;
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    border-bottom: 1px solid #e5e7eb;
  }

  .table-scroll {
    overflow-x: auto;
    max-height: calc(100vh - 400px);
    overflow-y: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  thead {
    position: sticky;
    top: 0;
    background: #f9fafb;
    z-index: 10;
  }

  th {
    text-align: left;
    padding: 0.75rem 1rem;
    font-weight: 600;
    color: #374151;
    border-bottom: 1px solid #e5e7eb;
    white-space: nowrap;
  }

  td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #f3f4f6;
  }

  tr:hover {
    background: #f9fafb;
  }

  .mono {
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
  }

  .copy-btn {
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    font-family: 'Courier New', monospace;
    font-size: 0.75rem;
    transition: all 0.2s;
  }

  .copy-btn:hover {
    background: #e5e7eb;
    border-color: #9ca3af;
  }

  .status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .status-badge.completed {
    background: #d1fae5;
    color: #065f46;
  }

  .status-badge.processing {
    background: #dbeafe;
    color: #1e40af;
  }

  .status-badge.pending {
    background: #fef3c7;
    color: #92400e;
  }

  .status-badge.failed {
    background: #fee2e2;
    color: #991b1b;
  }

  .error-cell {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #dc2626;
    font-size: 0.8rem;
  }

  .url-cell, .path-cell {
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: 'Courier New', monospace;
    font-size: 0.75rem;
    color: #6b7280;
  }

  .date-cell {
    font-size: 0.8rem;
    color: #6b7280;
    white-space: nowrap;
  }

  .json-cell {
    max-width: 400px;
  }

  details {
    cursor: pointer;
  }

  summary {
    color: #2563eb;
    font-weight: 500;
    user-select: none;
  }

  summary:hover {
    text-decoration: underline;
  }

  pre {
    background: #1f2937;
    color: #10b981;
    padding: 1rem;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 0.75rem;
    margin-top: 0.5rem;
    max-height: 400px;
    overflow-y: auto;
  }
</style>
