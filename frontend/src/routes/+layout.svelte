<script>
  import '@picocss/pico/css/pico.min.css';
</script>

<main class="container">
  <header>
    <nav>
      <ul>
        <li><strong>Audio Processing Pipeline</strong></li>
      </ul>
      <ul>
        <li><a href="/">Home</a></li>
      </ul>
    </nav>
  </header>

  <slot />

  <footer style="margin-top: 3rem; text-align: center; padding: 2rem 0; border-top: 1px solid var(--muted-border-color);">
    <small>Audio Processing Microservice Architecture</small>
  </footer>
</main>

<style>
  :global(body) {
    padding: 1rem;
  }

  header {
    margin-bottom: 2rem;
  }
</style>
