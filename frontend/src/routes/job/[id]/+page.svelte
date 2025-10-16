<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { getJob, formatDate, getStatusColor } from '$lib/api.js';

  let jobId = $page.params.id;
  let job = null;
  let loading = true;
  let error = '';
  let pollInterval = null;

  onMount(async () => {
    await loadJob();

    // Poll every 5 seconds if job is not completed or failed
    if (job && (job.status === 'PENDING' || job.status === 'PROCESSING')) {
      pollInterval = setInterval(async () => {
        await loadJob();

        // Stop polling if job is completed or failed
        if (job && (job.status === 'COMPLETED' || job.status === 'FAILED')) {
          clearInterval(pollInterval);
        }
      }, 5000);
    }
  });

  onDestroy(() => {
    if (pollInterval) {
      clearInterval(pollInterval);
    }
  });

  async function loadJob() {
    try {
      loading = true;
      error = '';
      job = await getJob(jobId);
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function getSentimentColor(sentiment) {
    if (!sentiment) return '';

    const s = sentiment.toLowerCase();
    if (s.includes('positive')) return 'success';
    if (s.includes('negative')) return 'error';
    if (s.includes('neutral')) return 'info';
    return '';
  }
</script>

<svelte:head>
  <title>Job Details - {jobId}</title>
</svelte:head>

<nav aria-label="breadcrumb">
  <ul>
    <li><a href="/">Home</a></li>
    <li>Job Details</li>
  </ul>
</nav>

{#if loading && !job}
  <article aria-busy="true">
    <p>Loading job details...</p>
  </article>
{:else if error}
  <article>
    <header>
      <h2>Error</h2>
    </header>
    <p style="color: var(--del-color);">{error}</p>
    <button on:click={() => goto('/')}>Back to Home</button>
  </article>
{:else if job}
  <article>
    <header>
      <h1>Job Details</h1>
      <p>
        <mark class={getStatusColor(job.status)}>{job.status}</mark>
        {#if job.status === 'PROCESSING' || job.status === 'PENDING'}
          <span aria-busy="true" style="margin-left: 1rem;">Processing...</span>
        {/if}
      </p>
    </header>

    <!-- Progress Bar -->
    {#if job.status === 'PROCESSING' && job.progress_percentage}
      <div class="progress-container">
        <div class="progress-header">
          <span class="progress-label">{job.current_step || 'Processing...'}</span>
          <span class="progress-percent">{job.progress_percentage}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: {job.progress_percentage}"></div>
        </div>
        {#if job.total_competitors && job.completed_competitors}
          <p class="progress-subtext">
            Analyzed {job.completed_competitors} of {job.total_competitors} competitors
          </p>
        {/if}
      </div>
    {/if}

    <h3>Basic Information</h3>
    <table>
      <tbody>
        <tr>
          <td><strong>Job ID</strong></td>
          <td><code>{job.id}</code></td>
        </tr>
        <tr>
          <td><strong>Filename</strong></td>
          <td>{job.filename}</td>
        </tr>
        <tr>
          <td><strong>Status</strong></td>
          <td>{job.status}</td>
        </tr>
        <tr>
          <td><strong>Created At</strong></td>
          <td>{formatDate(job.created_at)}</td>
        </tr>
        {#if job.completed_at}
          <tr>
            <td><strong>Completed At</strong></td>
            <td>{formatDate(job.completed_at)}</td>
          </tr>
        {/if}
      </tbody>
    </table>

    {#if job.error_message}
      <article style="background-color: var(--del-color); color: white; margin-top: 1rem;">
        <header>
          <h3>Error Message</h3>
        </header>
        <p>{job.error_message}</p>
      </article>
    {/if}

    {#if job.competitors_found && job.competitors_found.length > 0}
      <h3 style="margin-top: 2rem;">Competitors Mentioned</h3>
      <p>Found {job.competitors_found.length} unique competitor(s) in the transcript:</p>
      <ul>
        {#each job.competitors_found as competitor}
          <li><strong>{competitor}</strong></li>
        {/each}
      </ul>
    {/if}

    {#if job.sentiment_results && job.sentiment_results.length > 0}
      <h3 style="margin-top: 2rem;">Sentiment Analysis Results</h3>

      {@const groupedResults = job.sentiment_results.reduce((acc, result) => {
        if (!acc[result.competitor_name]) {
          acc[result.competitor_name] = [];
        }
        acc[result.competitor_name].push(result);
        return acc;
      }, {})}

      {#each Object.entries(groupedResults) as [competitorName, segments]}
        {@const posCount = segments.filter(s => s.sentiment.toLowerCase() === 'positive').length}
        {@const negCount = segments.filter(s => s.sentiment.toLowerCase() === 'negative').length}
        {@const neuCount = segments.filter(s => s.sentiment.toLowerCase() === 'neutral').length}
        {@const overallSentiment = posCount > negCount ? (posCount > neuCount ? 'positive' : 'neutral') : (negCount > neuCount ? 'negative' : 'neutral')}

        <details open>
          <summary>
            <strong>{competitorName}</strong>
            <span style="margin-left: 1rem;">
              ({segments.length} mention{segments.length !== 1 ? 's' : ''})
            </span>
            <mark class={getSentimentColor(overallSentiment)} style="margin-left: 0.5rem;">
              {overallSentiment}
            </mark>
          </summary>

          <article style="margin-top: 1rem;">
            <div class="sentiment-summary">
              <span class="stat positive">{posCount} Positive</span>
              <span class="stat negative">{negCount} Negative</span>
              <span class="stat neutral">{neuCount} Neutral</span>
            </div>

            <div class="segments-container">
              {#each segments as segment}
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
                  </div>
                </div>
              {/each}
            </div>
          </article>
        </details>
      {/each}
    {/if}

    {#if job.status === 'COMPLETED' && (!job.sentiment_results || job.sentiment_results.length === 0)}
      <article style="margin-top: 2rem;">
        <p>No sentiment analysis results available. No competitors were found in the transcript.</p>
      </article>
    {/if}
  </article>

  <button on:click={() => goto('/')} style="margin-top: 2rem;">Back to Home</button>
{/if}

<style>
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

  mark.warning {
    background-color: #ff9800;
    color: white;
  }

  details {
    margin-bottom: 1rem;
  }

  summary {
    cursor: pointer;
    padding: 0.5rem;
    background-color: var(--card-background-color);
    border-radius: 0.25rem;
  }

  summary:hover {
    background-color: var(--muted-border-color);
  }

  .progress-container {
    background-color: var(--card-background-color);
    border: 1px solid var(--muted-border-color);
    border-radius: 0.5rem;
    padding: 1.5rem;
    margin: 2rem 0;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .progress-label {
    font-weight: 600;
    font-size: 1rem;
    color: var(--primary);
  }

  .progress-percent {
    font-weight: 700;
    font-size: 1.25rem;
    color: var(--primary);
  }

  .progress-bar {
    width: 100%;
    height: 24px;
    background-color: var(--muted-border-color);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
    border-radius: 12px;
    transition: width 0.5s ease-in-out;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 0.5rem;
    box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
  }

  .progress-subtext {
    margin-top: 0.75rem;
    font-size: 0.9rem;
    color: var(--muted-color);
    text-align: center;
  }

  .sentiment-summary {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding: 1rem;
    background-color: var(--card-background-color);
    border-radius: 0.25rem;
    justify-content: center;
  }

  .sentiment-summary .stat {
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    font-weight: 600;
  }

  .sentiment-summary .stat.positive {
    background-color: var(--ins-color);
    color: white;
  }

  .sentiment-summary .stat.negative {
    background-color: var(--del-color);
    color: white;
  }

  .sentiment-summary .stat.neutral {
    background-color: var(--primary);
    color: white;
  }

  .segments-container {
    display: grid;
    gap: 1rem;
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
</style>
