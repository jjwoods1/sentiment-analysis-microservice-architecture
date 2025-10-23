<script>
  import { onMount } from 'svelte';
  import { getPatterns } from '$lib/api.js';

  let patterns = [];
  let loading = true;
  let error = '';
  let sortBy = 'matches'; // 'matches', 'name', 'recent'
  let filterType = 'all'; // 'all', 'positive', 'negative'
  let searchTerm = '';

  // Date filter
  let dateFilter = 'all'; // 'all', 'today', 'week', 'month', 'custom'
  let startDate = '';
  let endDate = '';

  onMount(async () => {
    await loadPatterns();
  });

  async function loadPatterns() {
    try {
      loading = true;
      error = '';

      const sentimentType = filterType === 'all' ? null : filterType;
      patterns = await getPatterns(sentimentType, true);

      console.log('Loaded patterns:', patterns.length);
    } catch (e) {
      error = `Failed to load patterns: ${e.message}`;
      console.error('Error loading patterns:', e);
    } finally {
      loading = false;
    }
  }

  // Reactive filtering and sorting
  $: filteredPatterns = patterns
    .filter(p => {
      // Filter by search term
      if (searchTerm.trim() && !p.pattern_text.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'matches') {
        return b.match_count - a.match_count;
      } else if (sortBy === 'name') {
        return a.pattern_text.localeCompare(b.pattern_text);
      } else if (sortBy === 'recent') {
        if (!a.last_matched_at) return 1;
        if (!b.last_matched_at) return -1;
        return new Date(b.last_matched_at) - new Date(a.last_matched_at);
      }
      return 0;
    });

  // Statistics
  $: totalPatterns = patterns.length;
  $: positivePatterns = patterns.filter(p => p.sentiment_type === 'positive').length;
  $: negativePatterns = patterns.filter(p => p.sentiment_type === 'negative').length;
  $: totalMatches = patterns.reduce((sum, p) => sum + p.match_count, 0);
  $: activePatterns = patterns.filter(p => p.match_count > 0).length;
  $: unusedPatterns = patterns.filter(p => p.match_count === 0).length;

  // Top patterns
  $: topPatterns = [...patterns]
    .filter(p => p.match_count > 0)
    .sort((a, b) => b.match_count - a.match_count)
    .slice(0, 10);

  async function handleFilterChange() {
    await loadPatterns();
  }

  function formatDate(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  }
</script>

<svelte:head>
  <title>Pattern Analytics</title>
</svelte:head>

<nav aria-label="breadcrumb">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/patterns">Patterns</a></li>
    <li>Analytics</li>
  </ul>
</nav>

<article>
  <header>
    <h1>Pattern Analytics</h1>
    <button on:click={loadPatterns} class="secondary" disabled={loading}>
      Refresh
    </button>
  </header>

  {#if loading}
    <p aria-busy="true">Loading analytics...</p>
  {:else if error}
    <p style="color: var(--del-color);">{error}</p>
  {:else}
    <!-- Summary Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{totalPatterns}</div>
        <div class="stat-label">Total Patterns</div>
        <div class="stat-breakdown">
          <span class="positive">{positivePatterns} positive</span>
          <span class="negative">{negativePatterns} negative</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{totalMatches}</div>
        <div class="stat-label">Total Matches</div>
        <div class="stat-breakdown">
          {activePatterns} patterns detected
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{activePatterns}</div>
        <div class="stat-label">Active Patterns</div>
        <div class="stat-breakdown">
          {unusedPatterns} never matched
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-value">{totalMatches > 0 ? (totalMatches / activePatterns).toFixed(1) : '0'}</div>
        <div class="stat-label">Avg Matches/Pattern</div>
        <div class="stat-breakdown">
          For active patterns
        </div>
      </div>
    </div>

    <!-- Top Patterns -->
    {#if topPatterns.length > 0}
      <article class="top-patterns">
        <header>
          <h2>Top 10 Most Detected Patterns</h2>
        </header>
        <div class="top-patterns-list">
          {#each topPatterns as pattern, index}
            <div class="top-pattern-item" class:positive={pattern.sentiment_type === 'positive'} class:negative={pattern.sentiment_type === 'negative'}>
              <div class="rank">#{index + 1}</div>
              <div class="pattern-info">
                <div class="pattern-text-large">{pattern.pattern_text}</div>
                <div class="pattern-meta">
                  <span class="sentiment-badge" class:positive={pattern.sentiment_type === 'positive'} class:negative={pattern.sentiment_type === 'negative'}>
                    {pattern.sentiment_type}
                  </span>
                  <span>Last detected: {formatDate(pattern.last_matched_at)}</span>
                </div>
              </div>
              <div class="match-count-large">
                {pattern.match_count}
                <span class="match-label">matches</span>
              </div>
            </div>
          {/each}
        </div>
      </article>
    {/if}

    <!-- All Patterns Table -->
    <article>
      <header>
        <h2>All Patterns</h2>
      </header>

      <!-- Filters and Search -->
      <div class="controls">
        <div class="filter-group">
          <label>
            Filter by type:
            <select bind:value={filterType} on:change={handleFilterChange}>
              <option value="all">All Types</option>
              <option value="positive">Positive Only</option>
              <option value="negative">Negative Only</option>
            </select>
          </label>

          <label>
            Sort by:
            <select bind:value={sortBy}>
              <option value="matches">Most Matches</option>
              <option value="recent">Recently Detected</option>
              <option value="name">Pattern Name</option>
            </select>
          </label>
        </div>

        <input
          type="search"
          bind:value={searchTerm}
          placeholder="Search patterns..."
          style="margin-top: 1rem;"
        />
      </div>

      <p class="results-count">Showing {filteredPatterns.length} of {totalPatterns} patterns</p>

      <!-- Patterns Table -->
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Pattern</th>
              <th>Type</th>
              <th>Matches</th>
              <th>Last Detected</th>
              <th>Added By</th>
            </tr>
          </thead>
          <tbody>
            {#if filteredPatterns.length === 0}
              <tr>
                <td colspan="5" style="text-align: center; color: var(--muted-color);">
                  {searchTerm ? 'No patterns match your search.' : 'No patterns found.'}
                </td>
              </tr>
            {:else}
              {#each filteredPatterns as pattern}
                <tr>
                  <td>
                    <code class="pattern-code">{pattern.pattern_text}</code>
                  </td>
                  <td>
                    <span class="sentiment-badge" class:positive={pattern.sentiment_type === 'positive'} class:negative={pattern.sentiment_type === 'negative'}>
                      {pattern.sentiment_type}
                    </span>
                  </td>
                  <td>
                    <strong>{pattern.match_count}</strong>
                  </td>
                  <td>
                    {formatDate(pattern.last_matched_at)}
                  </td>
                  <td>
                    {pattern.added_by || 'unknown'}
                  </td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </article>
  {/if}
</article>

<style>
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .stat-card {
    background: var(--card-background-color);
    border: 1px solid var(--muted-border-color);
    border-radius: 0.5rem;
    padding: 1.5rem;
    text-align: center;
  }

  .stat-value {
    font-size: 2.5rem;
    font-weight: bold;
    color: var(--primary);
    margin-bottom: 0.5rem;
  }

  .stat-label {
    font-size: 0.875rem;
    color: var(--muted-color);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }

  .stat-breakdown {
    font-size: 0.75rem;
    color: var(--muted-color);
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    flex-wrap: wrap;
  }

  .stat-breakdown .positive {
    color: var(--ins-color);
  }

  .stat-breakdown .negative {
    color: var(--del-color);
  }

  .top-patterns {
    margin-bottom: 2rem;
  }

  .top-patterns-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .top-pattern-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--card-background-color);
    border-radius: 0.5rem;
    border-left: 4px solid var(--muted-border-color);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .top-pattern-item:hover {
    transform: translateX(4px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .top-pattern-item.positive {
    border-left-color: var(--ins-color);
  }

  .top-pattern-item.negative {
    border-left-color: var(--del-color);
  }

  .rank {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--muted-color);
    min-width: 3rem;
    text-align: center;
  }

  .pattern-info {
    flex: 1;
  }

  .pattern-text-large {
    font-family: monospace;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .pattern-meta {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--muted-color);
    align-items: center;
  }

  .match-count-large {
    font-size: 2rem;
    font-weight: bold;
    color: var(--primary);
    text-align: center;
    min-width: 5rem;
  }

  .match-label {
    display: block;
    font-size: 0.75rem;
    font-weight: normal;
    color: var(--muted-color);
  }

  .controls {
    margin-bottom: 1rem;
  }

  .filter-group {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .filter-group label {
    flex: 1;
    min-width: 200px;
  }

  .results-count {
    font-size: 0.875rem;
    color: var(--muted-color);
    margin-bottom: 1rem;
  }

  .table-container {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th {
    text-align: left;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    color: var(--muted-color);
    padding: 0.75rem;
    border-bottom: 2px solid var(--muted-border-color);
  }

  td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--muted-border-color);
  }

  tbody tr:hover {
    background-color: var(--muted-border-color);
  }

  .pattern-code {
    font-family: monospace;
    background: var(--code-background-color);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.875rem;
  }

  .sentiment-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .sentiment-badge.positive {
    background-color: var(--ins-color);
    color: white;
  }

  .sentiment-badge.negative {
    background-color: var(--del-color);
    color: white;
  }

  @media (max-width: 768px) {
    .stats-grid {
      grid-template-columns: 1fr;
    }

    .filter-group {
      flex-direction: column;
    }

    .top-pattern-item {
      flex-direction: column;
      text-align: center;
    }

    .rank {
      min-width: auto;
    }
  }
</style>
