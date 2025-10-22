<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$jobId = $_GET['id'] ?? null;

if (!$jobId) {
    header('Location: /index.php');
    exit;
}

$pageTitle = 'Job Details';
$error = null;
$job = null;
$sentimentResults = [];

try {
    $api = getOrchestratorApi();
    $job = $api->get('/jobs/' . urlencode($jobId));

    // Group sentiment results by competitor
    if (isset($job['sentiment_results']) && is_array($job['sentiment_results'])) {
        foreach ($job['sentiment_results'] as $result) {
            $competitor = $result['competitor_name'] ?? 'Unknown';
            if (!isset($sentimentResults[$competitor])) {
                $sentimentResults[$competitor] = [];
            }
            $sentimentResults[$competitor][] = $result;
        }
    }
} catch (Exception $e) {
    $error = 'Failed to load job: ' . $e->getMessage();
}

// Calculate progress
$progress = 0;
$currentStep = 'Initializing';
if ($job) {
    if ($job['status'] === 'COMPLETED') {
        $progress = 100;
        $currentStep = 'Completed';
    } elseif ($job['status'] === 'FAILED') {
        $currentStep = 'Failed';
    } elseif ($job['status'] === 'PROCESSING') {
        // Estimate progress based on sentiment results
        $totalCompetitors = count($sentimentResults);
        if ($totalCompetitors > 0) {
            $progress = min(90, 50 + ($totalCompetitors * 10));
            $currentStep = 'Analyzing sentiment (' . $totalCompetitors . ' competitors processed)';
        } else {
            $progress = 30;
            $currentStep = 'Processing audio';
        }
    } elseif ($job['status'] === 'PENDING') {
        $progress = 10;
        $currentStep = 'Queued';
    }
}

require_once __DIR__ . '/../src/includes/header.php';
?>

<div style="margin-bottom: 1rem;">
    <a href="/index.php">← Back to Jobs</a>
</div>

<h1>Job Details</h1>

<?php if ($error): ?>
    <div class="error-message">
        <?php echo htmlspecialchars($error); ?>
    </div>
<?php elseif ($job): ?>

    <!-- Job Status -->
    <section>
        <h2>Status:
            <span class="status-badge status-<?php echo strtolower(htmlspecialchars($job['status'])); ?>">
                <?php echo htmlspecialchars($job['status']); ?>
            </span>
        </h2>

        <?php if ($job['status'] === 'PROCESSING' || $job['status'] === 'PENDING'): ?>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar" style="width: <?php echo $progress; ?>%;">
                    <span id="progressText"><?php echo $progress; ?>%</span>
                </div>
            </div>
            <p id="currentStep"><small><?php echo htmlspecialchars($currentStep); ?></small></p>
        <?php endif; ?>

        <?php if (isset($job['error_message']) && $job['error_message']): ?>
            <div class="error-message">
                <strong>Error:</strong> <?php echo htmlspecialchars($job['error_message']); ?>
            </div>
        <?php endif; ?>
    </section>

    <!-- Basic Information -->
    <section class="mt-2">
        <h2>Basic Information</h2>
        <table>
            <tbody>
                <tr>
                    <th>Job ID</th>
                    <td><?php echo htmlspecialchars($job['id']); ?></td>
                </tr>
                <tr>
                    <th>Source File</th>
                    <td><?php echo htmlspecialchars($job['source_file'] ?? 'N/A'); ?></td>
                </tr>
                <tr>
                    <th>Created At</th>
                    <td><?php echo htmlspecialchars($job['created_at'] ?? 'N/A'); ?></td>
                </tr>
                <tr>
                    <th>Updated At</th>
                    <td><?php echo htmlspecialchars($job['updated_at'] ?? 'N/A'); ?></td>
                </tr>
                <?php if (isset($job['completed_at']) && $job['completed_at']): ?>
                <tr>
                    <th>Completed At</th>
                    <td><?php echo htmlspecialchars($job['completed_at']); ?></td>
                </tr>
                <?php endif; ?>
            </tbody>
        </table>
    </section>

    <!-- Sentiment Analysis Results -->
    <?php if ($job['status'] === 'COMPLETED' && !empty($sentimentResults)): ?>
        <section class="mt-2">
            <h2>Sentiment Analysis Results</h2>

            <p><strong>Competitors Found:</strong> <?php echo count($sentimentResults); ?></p>

            <?php foreach ($sentimentResults as $competitor => $results): ?>
                <details open>
                    <summary>
                        <?php echo htmlspecialchars($competitor); ?>
                        (<?php echo count($results); ?> mentions)
                    </summary>

                    <div style="margin-top: 1rem;">
                        <?php
                        // Count sentiments
                        $positive = 0;
                        $negative = 0;
                        $neutral = 0;
                        foreach ($results as $result) {
                            $sentiment = strtolower($result['sentiment'] ?? 'neutral');
                            if ($sentiment === 'positive') $positive++;
                            elseif ($sentiment === 'negative') $negative++;
                            else $neutral++;
                        }
                        ?>

                        <p>
                            <span class="sentiment-badge sentiment-positive">Positive: <?php echo $positive; ?></span>
                            <span class="sentiment-badge sentiment-negative">Negative: <?php echo $negative; ?></span>
                            <span class="sentiment-badge sentiment-neutral">Neutral: <?php echo $neutral; ?></span>
                        </p>

                        <?php foreach ($results as $result): ?>
                            <div class="segment-card">
                                <div class="segment-header">
                                    <span class="sentiment-badge sentiment-<?php echo strtolower(htmlspecialchars($result['sentiment'] ?? 'neutral')); ?>">
                                        <?php echo htmlspecialchars($result['sentiment'] ?? 'Neutral'); ?>
                                    </span>
                                    <span class="detection-method">
                                        <?php echo htmlspecialchars($result['detection_method'] ?? 'Unknown'); ?>
                                    </span>
                                </div>

                                <div class="segment-text">
                                    <?php echo htmlspecialchars($result['segment_text'] ?? 'No text'); ?>
                                </div>

                                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
                                    <small>
                                        Time:
                                        <?php
                                        if (isset($result['segment_start'])) {
                                            $start = floor($result['segment_start']);
                                            echo sprintf('%02d:%02d', floor($start / 60), $start % 60);
                                        } else {
                                            echo 'N/A';
                                        }
                                        ?> -
                                        <?php
                                        if (isset($result['segment_end'])) {
                                            $end = floor($result['segment_end']);
                                            echo sprintf('%02d:%02d', floor($end / 60), $end % 60);
                                        } else {
                                            echo 'N/A';
                                        }
                                        ?>
                                    </small>
                                    <?php if (isset($result['confidence'])): ?>
                                        <small>Confidence: <?php echo round($result['confidence'] * 100); ?>%</small>
                                    <?php endif; ?>
                                </div>

                                <?php if (isset($result['explanation']) && $result['explanation']): ?>
                                    <details style="margin-top: 0.5rem;">
                                        <summary>Detection Details</summary>
                                        <p><small><?php echo htmlspecialchars($result['explanation']); ?></small></p>
                                    </details>
                                <?php endif; ?>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </details>
            <?php endforeach; ?>
        </section>
    <?php elseif ($job['status'] === 'COMPLETED'): ?>
        <section class="mt-2">
            <p>No sentiment results found for this job.</p>
        </section>
    <?php endif; ?>

<?php endif; ?>

<script>
    const jobId = <?php echo json_encode($jobId); ?>;
    const currentStatus = <?php echo json_encode($job['status'] ?? 'UNKNOWN'); ?>;
    let pollInterval = null;

    async function refreshJobData() {
        try {
            const response = await fetch(`<?php echo API_URL; ?>/jobs/${encodeURIComponent(jobId)}`);
            if (!response.ok) throw new Error('Failed to fetch job data');

            const job = await response.json();

            // Update status badge
            const statusElements = document.querySelectorAll('.status-badge');
            statusElements.forEach(el => {
                el.className = `status-badge status-${job.status.toLowerCase()}`;
                el.textContent = job.status;
            });

            // Update progress if still processing
            if (job.status === 'PROCESSING' || job.status === 'PENDING') {
                let progress = 10;
                let currentStep = 'Initializing';

                if (job.status === 'PROCESSING') {
                    const competitorCount = job.sentiment_results ? job.sentiment_results.length : 0;
                    if (competitorCount > 0) {
                        progress = Math.min(90, 50 + (competitorCount * 10));
                        currentStep = `Analyzing sentiment (${competitorCount} competitors processed)`;
                    } else {
                        progress = 30;
                        currentStep = 'Processing audio';
                    }
                } else {
                    currentStep = 'Queued';
                }

                const progressBar = document.getElementById('progressBar');
                const progressText = document.getElementById('progressText');
                const stepEl = document.getElementById('currentStep');

                if (progressBar && progressText) {
                    progressBar.style.width = progress + '%';
                    progressText.textContent = progress + '%';
                }

                if (stepEl) {
                    stepEl.innerHTML = `<small>${escapeHtml(currentStep)}</small>`;
                }
            }

            // If status changed to COMPLETED or FAILED, reload page to show results
            if ((job.status === 'COMPLETED' || job.status === 'FAILED') &&
                (currentStatus === 'PROCESSING' || currentStatus === 'PENDING')) {
                location.reload();
            }

            // Stop polling if job is no longer active
            if (job.status !== 'PROCESSING' && job.status !== 'PENDING') {
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            }
        } catch (error) {
            console.error('Failed to refresh job data:', error);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Start polling if job is still processing
    if (currentStatus === 'PROCESSING' || currentStatus === 'PENDING') {
        pollInterval = setInterval(refreshJobData, 5000); // Poll every 5 seconds
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
    });
</script>

<?php require_once __DIR__ . '/../src/includes/footer.php'; ?>
