<script>
  import { onMount } from 'svelte';
  import {
    getPositivePatterns,
    getNegativePatterns,
    addPositivePattern,
    addNegativePattern,
    deletePositivePattern,
    deleteNegativePattern,
    replacePositivePatterns,
    replaceNegativePatterns
  } from '$lib/api.js';

  let positivePatterns = [];
  let negativePatterns = [];
  let loading = true;
  let error = '';

  // Add single pattern
  let newPositivePattern = '';
  let newNegativePattern = '';
  let addingPositive = false;
  let addingNegative = false;

  // Bulk upload
  let bulkPositiveText = '';
  let bulkNegativeText = '';
  let uploadingPositive = false;
  let uploadingNegative = false;

  // Bulk delete
  let selectedPositive = new Set();
  let selectedNegative = new Set();
  let deletingPositive = false;
  let deletingNegative = false;

  // Search/filter
  let positiveSearchTerm = '';
  let negativeSearchTerm = '';

  onMount(async () => {
    await loadPatterns();
  });

  async function loadPatterns() {
    try {
      loading = true;
      error = '';

      const [posData, negData] = await Promise.all([
        getPositivePatterns(),
        getNegativePatterns()
      ]);

      positivePatterns = posData.patterns || [];
      negativePatterns = negData.patterns || [];
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function handleAddPositive() {
    if (!newPositivePattern.trim()) return;

    try {
      addingPositive = true;
      error = '';
      const result = await addPositivePattern(newPositivePattern.trim());
      positivePatterns = result.patterns || [];
      newPositivePattern = '';
    } catch (e) {
      error = e.message;
    } finally {
      addingPositive = false;
    }
  }

  async function handleAddNegative() {
    if (!newNegativePattern.trim()) return;

    try {
      addingNegative = true;
      error = '';
      const result = await addNegativePattern(newNegativePattern.trim());
      negativePatterns = result.patterns || [];
      newNegativePattern = '';
    } catch (e) {
      error = e.message;
    } finally {
      addingNegative = false;
    }
  }

  async function handleBulkUploadPositive() {
    if (!bulkPositiveText.trim()) return;

    try {
      uploadingPositive = true;
      error = '';

      // Split by newlines and filter empty lines
      const patterns = bulkPositiveText.split('\n')
        .map(p => p.trim())
        .filter(p => p && !p.startsWith('#'));

      // Merge with existing patterns
      const allPatterns = [...new Set([...positivePatterns, ...patterns])];

      const result = await replacePositivePatterns(allPatterns);
      positivePatterns = result.patterns || [];
      bulkPositiveText = '';
    } catch (e) {
      error = e.message;
    } finally {
      uploadingPositive = false;
    }
  }

  async function handleBulkUploadNegative() {
    if (!bulkNegativeText.trim()) return;

    try {
      uploadingNegative = true;
      error = '';

      // Split by newlines and filter empty lines
      const patterns = bulkNegativeText.split('\n')
        .map(p => p.trim())
        .filter(p => p && !p.startsWith('#'));

      // Merge with existing patterns
      const allPatterns = [...new Set([...negativePatterns, ...patterns])];

      const result = await replaceNegativePatterns(allPatterns);
      negativePatterns = result.patterns || [];
      bulkNegativeText = '';
    } catch (e) {
      error = e.message;
    } finally {
      uploadingNegative = false;
    }
  }

  async function handleDeletePositive(pattern) {
    try {
      error = '';
      await deletePositivePattern(pattern);
      positivePatterns = positivePatterns.filter(p => p !== pattern);
    } catch (e) {
      error = e.message;
    }
  }

  async function handleDeleteNegative(pattern) {
    try {
      error = '';
      await deleteNegativePattern(pattern);
      negativePatterns = negativePatterns.filter(p => p !== pattern);
    } catch (e) {
      error = e.message;
    }
  }

  async function handleBulkDeletePositive() {
    if (selectedPositive.size === 0) return;

    try {
      deletingPositive = true;
      error = '';

      // Remove selected patterns
      const remainingPatterns = positivePatterns.filter(p => !selectedPositive.has(p));

      const result = await replacePositivePatterns(remainingPatterns);
      positivePatterns = result.patterns || [];
      selectedPositive.clear();
      selectedPositive = selectedPositive; // Trigger reactivity
    } catch (e) {
      error = e.message;
    } finally {
      deletingPositive = false;
    }
  }

  async function handleBulkDeleteNegative() {
    if (selectedNegative.size === 0) return;

    try {
      deletingNegative = true;
      error = '';

      // Remove selected patterns
      const remainingPatterns = negativePatterns.filter(p => !selectedNegative.has(p));

      const result = await replaceNegativePatterns(remainingPatterns);
      negativePatterns = result.patterns || [];
      selectedNegative.clear();
      selectedNegative = selectedNegative; // Trigger reactivity
    } catch (e) {
      error = e.message;
    } finally {
      deletingNegative = false;
    }
  }

  function togglePositiveSelection(pattern) {
    if (selectedPositive.has(pattern)) {
      selectedPositive.delete(pattern);
    } else {
      selectedPositive.add(pattern);
    }
    selectedPositive = selectedPositive; // Trigger reactivity
  }

  function toggleNegativeSelection(pattern) {
    if (selectedNegative.has(pattern)) {
      selectedNegative.delete(pattern);
    } else {
      selectedNegative.add(pattern);
    }
    selectedNegative = selectedNegative; // Trigger reactivity
  }

  function selectAllPositive() {
    const filtered = getFilteredPositive();
    selectedPositive = new Set(filtered);
  }

  function selectAllNegative() {
    const filtered = getFilteredNegative();
    selectedNegative = new Set(filtered);
  }

  function deselectAllPositive() {
    selectedPositive.clear();
    selectedPositive = selectedPositive;
  }

  function deselectAllNegative() {
    selectedNegative.clear();
    selectedNegative = selectedNegative;
  }

  function getFilteredPositive() {
    if (!positiveSearchTerm.trim()) return positivePatterns;
    const term = positiveSearchTerm.toLowerCase();
    return positivePatterns.filter(p => p.toLowerCase().includes(term));
  }

  function getFilteredNegative() {
    if (!negativeSearchTerm.trim()) return negativePatterns;
    const term = negativeSearchTerm.toLowerCase();
    return negativePatterns.filter(p => p.toLowerCase().includes(term));
  }

  $: filteredPositive = getFilteredPositive();
  $: filteredNegative = getFilteredNegative();
</script>

<svelte:head>
  <title>Sentiment Pattern Management</title>
</svelte:head>

<nav aria-label="breadcrumb">
  <ul>
    <li><a href="/">Home</a></li>
    <li>Sentiment Pattern Management</li>
  </ul>
</nav>

<article>
  <header>
    <h1>Sentiment Pattern Management</h1>
    <button on:click={loadPatterns} class="secondary" disabled={loading}>
      Refresh
    </button>
  </header>

  {#if loading}
    <p aria-busy="true">Loading patterns...</p>
  {:else if error}
    <p style="color: var(--del-color);">{error}</p>
  {:else}
    <div class="patterns-grid">
      <!-- Positive Patterns Column -->
      <article class="pattern-column positive-column">
        <header>
          <h2>Positive Patterns</h2>
          <span class="count">{positivePatterns.length} patterns</span>
        </header>

        <!-- Add Single Pattern -->
        <div class="add-pattern">
          <input
            type="text"
            bind:value={newPositivePattern}
            placeholder="Add new positive pattern..."
            on:keydown={(e) => e.key === 'Enter' && handleAddPositive()}
          />
          <button on:click={handleAddPositive} disabled={addingPositive || !newPositivePattern.trim()}>
            {addingPositive ? 'Adding...' : 'Add'}
          </button>
        </div>

        <!-- Bulk Upload -->
        <details>
          <summary>Bulk Upload</summary>
          <textarea
            bind:value={bulkPositiveText}
            placeholder="Paste multiple patterns (one per line)&#10;Lines starting with # are ignored"
            rows="5"
          ></textarea>
          <button
            on:click={handleBulkUploadPositive}
            disabled={uploadingPositive || !bulkPositiveText.trim()}
            class="secondary"
          >
            {uploadingPositive ? 'Uploading...' : 'Upload Patterns'}
          </button>
        </details>

        <!-- Search -->
        <input
          type="search"
          bind:value={positiveSearchTerm}
          placeholder="Search positive patterns..."
        />

        <!-- Bulk Actions -->
        <div class="bulk-actions">
          <button on:click={selectAllPositive} class="outline" style="padding: 0.5rem;">
            Select All ({filteredPositive.length})
          </button>
          <button on:click={deselectAllPositive} class="outline" style="padding: 0.5rem;">
            Deselect All
          </button>
          <button
            on:click={handleBulkDeletePositive}
            disabled={deletingPositive || selectedPositive.size === 0}
            class="contrast"
            style="padding: 0.5rem;"
          >
            {deletingPositive ? 'Deleting...' : `Delete Selected (${selectedPositive.size})`}
          </button>
        </div>

        <!-- Pattern List -->
        <div class="pattern-list">
          {#each filteredPositive as pattern}
            <div class="pattern-item positive-pattern" class:selected={selectedPositive.has(pattern)}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedPositive.has(pattern)}
                  on:change={() => togglePositiveSelection(pattern)}
                />
                <span class="pattern-text">{pattern}</span>
              </label>
              <button
                on:click={() => handleDeletePositive(pattern)}
                class="delete-btn"
                aria-label="Delete pattern"
              >
                ×
              </button>
            </div>
          {/each}
        </div>
      </article>

      <!-- Negative Patterns Column -->
      <article class="pattern-column negative-column">
        <header>
          <h2>Negative Patterns</h2>
          <span class="count">{negativePatterns.length} patterns</span>
        </header>

        <!-- Add Single Pattern -->
        <div class="add-pattern">
          <input
            type="text"
            bind:value={newNegativePattern}
            placeholder="Add new negative pattern..."
            on:keydown={(e) => e.key === 'Enter' && handleAddNegative()}
          />
          <button on:click={handleAddNegative} disabled={addingNegative || !newNegativePattern.trim()}>
            {addingNegative ? 'Adding...' : 'Add'}
          </button>
        </div>

        <!-- Bulk Upload -->
        <details>
          <summary>Bulk Upload</summary>
          <textarea
            bind:value={bulkNegativeText}
            placeholder="Paste multiple patterns (one per line)&#10;Lines starting with # are ignored"
            rows="5"
          ></textarea>
          <button
            on:click={handleBulkUploadNegative}
            disabled={uploadingNegative || !bulkNegativeText.trim()}
            class="secondary"
          >
            {uploadingNegative ? 'Uploading...' : 'Upload Patterns'}
          </button>
        </details>

        <!-- Search -->
        <input
          type="search"
          bind:value={negativeSearchTerm}
          placeholder="Search negative patterns..."
        />

        <!-- Bulk Actions -->
        <div class="bulk-actions">
          <button on:click={selectAllNegative} class="outline" style="padding: 0.5rem;">
            Select All ({filteredNegative.length})
          </button>
          <button on:click={deselectAllNegative} class="outline" style="padding: 0.5rem;">
            Deselect All
          </button>
          <button
            on:click={handleBulkDeleteNegative}
            disabled={deletingNegative || selectedNegative.size === 0}
            class="contrast"
            style="padding: 0.5rem;"
          >
            {deletingNegative ? 'Deleting...' : `Delete Selected (${selectedNegative.size})`}
          </button>
        </div>

        <!-- Pattern List -->
        <div class="pattern-list">
          {#each filteredNegative as pattern}
            <div class="pattern-item negative-pattern" class:selected={selectedNegative.has(pattern)}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedNegative.has(pattern)}
                  on:change={() => toggleNegativeSelection(pattern)}
                />
                <span class="pattern-text">{pattern}</span>
              </label>
              <button
                on:click={() => handleDeleteNegative(pattern)}
                class="delete-btn"
                aria-label="Delete pattern"
              >
                ×
              </button>
            </div>
          {/each}
        </div>
      </article>
    </div>
  {/if}
</article>

<style>
  .patterns-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-top: 1rem;
  }

  @media (max-width: 768px) {
    .patterns-grid {
      grid-template-columns: 1fr;
    }
  }

  .pattern-column {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .pattern-column header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .pattern-column header h2 {
    margin: 0;
  }

  .count {
    font-size: 0.875rem;
    color: var(--muted-color);
  }

  .positive-column {
    border-left: 4px solid var(--ins-color);
  }

  .negative-column {
    border-left: 4px solid var(--del-color);
  }

  .add-pattern {
    display: flex;
    gap: 0.5rem;
  }

  .add-pattern input {
    flex: 1;
    margin: 0;
  }

  .add-pattern button {
    margin: 0;
    white-space: nowrap;
  }

  details {
    margin: 0;
  }

  details summary {
    cursor: pointer;
    font-weight: 600;
    padding: 0.5rem;
    background-color: var(--card-background-color);
    border-radius: 0.25rem;
  }

  details[open] summary {
    margin-bottom: 0.5rem;
  }

  textarea {
    margin-bottom: 0.5rem;
  }

  .bulk-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .bulk-actions button {
    margin: 0;
    font-size: 0.875rem;
  }

  .pattern-list {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid var(--muted-border-color);
    border-radius: 0.25rem;
    padding: 0.5rem;
  }

  .pattern-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem;
    margin-bottom: 0.25rem;
    border-radius: 0.25rem;
    transition: background-color 0.2s ease;
  }

  .pattern-item:hover {
    background-color: var(--muted-border-color);
  }

  .pattern-item.selected {
    background-color: var(--primary-focus);
  }

  .positive-pattern {
    border-left: 3px solid var(--ins-color);
  }

  .negative-pattern {
    border-left: 3px solid var(--del-color);
  }

  .pattern-item label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    margin: 0;
    cursor: pointer;
  }

  .pattern-item input[type="checkbox"] {
    margin: 0;
  }

  .pattern-text {
    font-family: monospace;
    font-size: 0.875rem;
  }

  .delete-btn {
    background: none;
    border: none;
    color: var(--del-color);
    font-size: 1.5rem;
    font-weight: bold;
    cursor: pointer;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 0.25rem;
    transition: background-color 0.2s ease;
  }

  .delete-btn:hover {
    background-color: var(--del-color);
    color: white;
  }
</style>
