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

      {#each job.sentiment_results as result}
        <details open>
          <summary>
            <strong>{result.competitor_name}</strong>
            {#if result.result_json.overall_sentiment}
              - <mark class={getSentimentColor(result.result_json.overall_sentiment)}>
                {result.result_json.overall_sentiment}
              </mark>
            {/if}
          </summary>

          <article style="margin-top: 1rem;">
            <h4>Analysis Details</h4>
            <pre style="background-color: var(--code-background-color); padding: 1rem; border-radius: 0.25rem; overflow-x: auto; max-height: 400px; overflow-y: auto;"><code>{JSON.stringify(result.result_json, null, 2)}</code></pre>
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
</style>
