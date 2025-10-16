<script>
  import { onMount } from 'svelte';
  import { getAnalyticsOverview, getCompetitorAnalytics, getAllCompetitors, getSentimentColor } from '$lib/api.js';

  let overview = null;
  let competitors = [];
  let selectedCompetitor = null;
  let competitorDetails = null;
  let loading = true;
  let error = '';
  let detailsLoading = false;
  let detailsError = '';

  onMount(async () => {
    await loadAnalytics();
  });

  async function loadAnalytics() {
    try {
      loading = true;
      error = '';

      // Load overview and competitors list in parallel
      const [overviewData, competitorsData] = await Promise.all([
        getAnalyticsOverview(),
        getAllCompetitors()
      ]);

      overview = overviewData;
      competitors = competitorsData.competitors;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function selectCompetitor(competitorName) {
    selectedCompetitor = competitorName;
    detailsLoading = true;
    detailsError = '';

    try {
      competitorDetails = await getCompetitorAnalytics(competitorName);
    } catch (e) {
      detailsError = e.message;
    } finally {
      detailsLoading = false;
    }
  }

  function clearSelection() {
    selectedCompetitor = null;
    competitorDetails = null;
  }
</script>

<svelte:head>
  <title>Analytics Dashboard</title>
</svelte:head>

<nav aria-label="breadcrumb">
  <ul>
    <li><a href="/">Home</a></li>
    <li>Analytics</li>
  </ul>
</nav>

<article>
  <header>
    <h1>Analytics Dashboard</h1>
    <button on:click={loadAnalytics} class="secondary" disabled={loading}>
      Refresh
    </button>
  </header>

  {#if loading}
    <p aria-busy="true">Loading analytics...</p>
  {:else if error}
    <p style="color: var(--del-color);">{error}</p>
  {:else if overview}
    <!-- Overview Stats -->
    <div class="grid">
      <article>
        <header><h3>Total Calls Processed</h3></header>
        <h2 style="text-align: center; margin: 2rem 0;">{overview.total_jobs}</h2>
      </article>

      <article>
        <header><h3>Unique Competitors</h3></header>
        <h2 style="text-align: center; margin: 2rem 0;">{overview.total_competitors}</h2>
      </article>
    </div>

    <!-- Top Competitors -->
    <article style="margin-top: 2rem;">
      <header>
        <h2>Top Mentioned Competitors</h2>
      </header>

      {#if overview.top_competitors.length > 0}
        <table>
          <thead>
            <tr>
              <th>Competitor</th>
              <th>Total Mentions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each overview.top_competitors as competitor}
              <tr>
                <td><strong>{competitor.name}</strong></td>
                <td>{competitor.count}</td>
                <td>
                  <button
                    on:click={() => selectCompetitor(competitor.name)}
                    class="secondary outline"
                    style="margin: 0; padding: 0.5rem 1rem;"
                  >
                    View Details
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <p>No competitor data available yet. Process some calls to see analytics!</p>
      {/if}
    </article>

    <!-- Overall Sentiment Distribution -->
    <article style="margin-top: 2rem;">
      <header>
        <h2>Overall Sentiment Distribution</h2>
      </header>

      {#if overview.sentiment_distribution.length > 0}
        <div class="sentiment-grid">
          {#each overview.sentiment_distribution as sentiment}
            <div class="sentiment-card">
              <mark class={getSentimentColor(sentiment.sentiment)}>
                {sentiment.sentiment}
              </mark>
              <h3>{sentiment.count}</h3>
              <small>mentions</small>
            </div>
          {/each}
        </div>
      {:else}
        <p>No sentiment data available yet.</p>
      {/if}
    </article>

    <!-- All Competitors List -->
    {#if competitors.length > 0}
      <article style="margin-top: 2rem;">
        <header>
          <h2>All Competitors ({competitors.length})</h2>
        </header>

        <div class="competitors-grid">
          {#each competitors as competitor}
            <div class="competitor-chip" on:click={() => selectCompetitor(competitor.name)}>
              <strong>{competitor.name}</strong>
              <small>{competitor.mention_count} mentions</small>
            </div>
          {/each}
        </div>
      </article>
    {/if}
  {/if}
</article>

<!-- Competitor Details Modal/Section -->
{#if selectedCompetitor}
  <article style="margin-top: 2rem; border: 2px solid var(--primary);">
    <header style="display: flex; justify-content: space-between; align-items: center;">
      <h2>Detailed Analytics: {selectedCompetitor}</h2>
      <button on:click={clearSelection} class="secondary">Close</button>
    </header>

    {#if detailsLoading}
      <p aria-busy="true">Loading competitor details...</p>
    {:else if detailsError}
      <p style="color: var(--del-color);">{detailsError}</p>
    {:else if competitorDetails}
      <div class="grid">
        <article>
          <header><h4>Total Mentions</h4></header>
          <h2 style="text-align: center; margin: 1rem 0;">{competitorDetails.total_mentions}</h2>
        </article>

        <article>
          <header><h4>Unique Calls</h4></header>
          <h2 style="text-align: center; margin: 1rem 0;">{competitorDetails.unique_calls}</h2>
        </article>
      </div>

      <h3 style="margin-top: 2rem;">Sentiment Breakdown</h3>
      <table>
        <thead>
          <tr>
            <th>Sentiment</th>
            <th>Count</th>
            <th>Percentage</th>
          </tr>
        </thead>
        <tbody>
          {#each competitorDetails.sentiment_breakdown as item}
            <tr>
              <td>
                <mark class={getSentimentColor(item.sentiment)}>
                  {item.sentiment}
                </mark>
              </td>
              <td>{item.count}</td>
              <td><strong>{item.percentage}%</strong></td>
            </tr>
          {/each}
        </tbody>
      </table>

      <!-- Visual Bar Chart -->
      <div style="margin-top: 2rem;">
        {#each competitorDetails.sentiment_breakdown as item}
          <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
              <span>{item.sentiment}</span>
              <span>{item.percentage}%</span>
            </div>
            <div style="background-color: #e0e0e0; border-radius: 4px; overflow: hidden; height: 24px;">
              <div
                class="progress-bar {getSentimentColor(item.sentiment)}"
                style="width: {item.percentage}%; height: 100%; transition: width 0.3s ease;"
              ></div>
            </div>
          </div>
        {/each}
      </div>

      <!-- All Individual Segments -->
      {#if competitorDetails.segments && competitorDetails.segments.length > 0}
        <h3 style="margin-top: 2rem;">All Mentions ({competitorDetails.segments.length})</h3>
        <p style="color: var(--muted-color); margin-bottom: 1rem;">Individual segment results showing all mentions of {selectedCompetitor}</p>

        <div class="segments-container">
          {#each competitorDetails.segments as segment}
            <div class="segment-card">
              <div class="segment-header">
                <mark class={getSentimentColor(segment.sentiment)}>
                  {segment.sentiment}
                </mark>
                <span class="detection-method">
                  {segment.detection_method === 'llm-based' ? 'LLM Based' : 'Rule Based'}
                </span>
              </div>

              <blockquote class="segment-text">
                "{segment.segment_text}"
              </blockquote>

              <div class="segment-meta">
                {#if segment.start_time && segment.end_time}
                  <small class="timestamp">
                    {Math.floor(parseFloat(segment.start_time) / 60)}:{String(Math.floor(parseFloat(segment.start_time) % 60)).padStart(2, '0')}
                    -
                    {Math.floor(parseFloat(segment.end_time) / 60)}:{String(Math.floor(parseFloat(segment.end_time) % 60)).padStart(2, '0')}
                  </small>
                {/if}
                {#if segment.detection_details}
                  <small class="detection-details">{segment.detection_details}</small>
                {/if}
                <small class="job-id" title="Job ID: {segment.job_id}">
                  Job: {segment.job_id.substring(0, 8)}...
                </small>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </article>
{/if}

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
  }

  .sentiment-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
  }

  .sentiment-card {
    text-align: center;
    padding: 1.5rem;
    background-color: var(--card-background-color);
    border-radius: 0.25rem;
    border: 1px solid var(--muted-border-color);
  }

  .sentiment-card h3 {
    margin: 0.5rem 0 0.25rem 0;
    font-size: 2rem;
  }

  .sentiment-card small {
    color: var(--muted-color);
  }

  .competitors-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .competitor-chip {
    padding: 1rem;
    background-color: var(--card-background-color);
    border: 1px solid var(--muted-border-color);
    border-radius: 0.25rem;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
  }

  .competitor-chip:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }

  .competitor-chip strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .competitor-chip small {
    color: var(--muted-color);
  }

  mark {
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-weight: 600;
  }

  mark.success {
    background-color: var(--ins-color);
    color: white;
  }

  mark.error {
    background-color: var(--del-color);
    color: white;
  }

  mark.info {
    background-color: var(--primary);
    color: white;
  }

  .progress-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .progress-bar.success {
    background-color: var(--ins-color);
  }

  .progress-bar.error {
    background-color: var(--del-color);
  }

  .progress-bar.info {
    background-color: var(--primary);
  }

  .segments-container {
    display: grid;
    gap: 1rem;
    margin-top: 1rem;
  }

  .segment-card {
    background-color: var(--card-background-color);
    border: 1px solid var(--muted-border-color);
    border-radius: 0.5rem;
    padding: 1rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .segment-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .segment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .detection-method {
    font-size: 0.875rem;
    color: var(--muted-color);
    background-color: var(--muted-border-color);
    padding: 0.25rem 0.75rem;
    border-radius: 0.25rem;
  }

  .segment-text {
    margin: 1rem 0;
    padding-left: 1rem;
    border-left: 3px solid var(--primary);
    font-style: italic;
    color: var(--color);
  }

  .segment-meta {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .segment-meta small {
    color: var(--muted-color);
    font-size: 0.875rem;
  }

  .segment-meta .timestamp {
    font-family: monospace;
  }

  .segment-meta .detection-details {
    font-style: italic;
  }

  .segment-meta .job-id {
    font-family: monospace;
    cursor: help;
  }
</style>
