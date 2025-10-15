<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { uploadAudioFile, getJobs, formatDate, getStatusColor } from '$lib/api.js';

  let file = null;
  let uploading = false;
  let uploadError = '';
  let jobs = [];
  let loading = true;
  let error = '';
  let pollInterval = null;

  onMount(async () => {
    await loadJobs();

    // Start polling every 5 seconds if there are jobs in progress
    startPollingIfNeeded();
  });

  onDestroy(() => {
    if (pollInterval) {
      clearInterval(pollInterval);
    }
  });

  function startPollingIfNeeded() {
    // Check if any jobs are in PROCESSING or PENDING status
    const hasActiveJobs = jobs.some(job =>
      job.status === 'PROCESSING' || job.status === 'PENDING'
    );

    if (hasActiveJobs && !pollInterval) {
      pollInterval = setInterval(async () => {
        await loadJobs(true); // Silent refresh

        // Stop polling if no more active jobs
        const stillHasActiveJobs = jobs.some(job =>
          job.status === 'PROCESSING' || job.status === 'PENDING'
        );

        if (!stillHasActiveJobs && pollInterval) {
          clearInterval(pollInterval);
          pollInterval = null;
        }
      }, 5000);
    } else if (!hasActiveJobs && pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  async function loadJobs(silent = false) {
    try {
      if (!silent) {
        loading = true;
      }
      error = '';
      const response = await getJobs();
      jobs = response.jobs;

      // Update polling status after loading jobs
      if (silent) {
        startPollingIfNeeded();
      }
    } catch (e) {
      error = e.message;
    } finally {
      if (!silent) {
        loading = false;
      }
    }
  }

  function handleFileSelect(event) {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      file = selectedFile;
      uploadError = '';
    }
  }

  async function handleUpload() {
    if (!file) {
      uploadError = 'Please select a file';
      return;
    }

    try {
      uploading = true;
      uploadError = '';
      const result = await uploadAudioFile(file);

      // Redirect to job detail page
      goto(`/job/${result.job_id}`);
    } catch (e) {
      uploadError = e.message;
      uploading = false;
    }
  }
</script>

<svelte:head>
  <title>Audio Processing Pipeline</title>
</svelte:head>

<article>
  <header>
    <h1>Upload Audio File</h1>
  </header>

  <form on:submit|preventDefault={handleUpload}>
    <label for="audioFile">
      Select an audio file to process
      <input
        type="file"
        id="audioFile"
        accept="audio/*"
        on:change={handleFileSelect}
        disabled={uploading}
      />
    </label>

    {#if file}
      <p>Selected file: <strong>{file.name}</strong> ({(file.size / 1024 / 1024).toFixed(2)} MB)</p>
    {/if}

    {#if uploadError}
      <p style="color: var(--del-color);">{uploadError}</p>
    {/if}

    <button type="submit" disabled={!file || uploading} aria-busy={uploading}>
      {uploading ? 'Uploading...' : 'Upload and Process'}
    </button>
  </form>
</article>

<article style="margin-top: 2rem;">
  <header style="display: flex; justify-content: space-between; align-items: center;">
    <h2>Processing History</h2>
    <button on:click={loadJobs} class="secondary" disabled={loading}>
      Refresh
    </button>
  </header>

  {#if loading}
    <p aria-busy="true">Loading jobs...</p>
  {:else if error}
    <p style="color: var(--del-color);">{error}</p>
  {:else if jobs.length === 0}
    <p>No jobs found. Upload an audio file to get started.</p>
  {:else}
    <figure>
      <table role="grid">
        <thead>
          <tr>
            <th>Job ID</th>
            <th>Filename</th>
            <th>Status</th>
            <th>Created At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each jobs as job}
            <tr>
              <td><code style="font-size: 0.8rem;">{job.id.substring(0, 8)}...</code></td>
              <td>{job.filename}</td>
              <td>
                <mark class={getStatusColor(job.status)}>{job.status}</mark>
              </td>
              <td>{formatDate(job.created_at)}</td>
              <td>
                <a href="/job/{job.id}" role="button" class="secondary outline" style="margin: 0; padding: 0.5rem 1rem;">
                  View Details
                </a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </figure>
  {/if}
</article>

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
</style>
