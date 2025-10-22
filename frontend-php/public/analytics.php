<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$pageTitle = 'Analytics Dashboard';
$error = null;
$overview = null;
$competitors = [];
$selectedCompetitor = null;
$competitorDetails = null;

// Date filtering
$dateFilter = $_GET['days'] ?? '30';
$customStartDate = $_GET['start_date'] ?? '';
$customEndDate = $_GET['end_date'] ?? '';

// Calculate date range
$startDate = null;
$endDate = null;

if ($customStartDate && $customEndDate) {
    $startDate = $customStartDate;
    $endDate = $customEndDate;
} elseif (is_numeric($dateFilter)) {
    $endDate = date('Y-m-d');
    $startDate = date('Y-m-d', strtotime("-{$dateFilter} days"));
}

// Load overview data
try {
    $api = getOrchestratorApi();
    $params = [];
    if ($startDate) $params['start_date'] = $startDate;
    if ($endDate) $params['end_date'] = $endDate;

    $overview = $api->get('/analytics/overview', $params);
} catch (Exception $e) {
    $error = 'Failed to load analytics: ' . $e->getMessage();
}

// Load competitors list
try {
    $api = getOrchestratorApi();
    $params = [];
    if ($startDate) $params['start_date'] = $startDate;
    if ($endDate) $params['end_date'] = $endDate;

    $competitorsResponse = $api->get('/analytics/competitors/list', $params);
    $competitors = $competitorsResponse['competitors'] ?? [];
} catch (Exception $e) {
    // Non-fatal, just log
    error_log('Failed to load competitors: ' . $e->getMessage());
}

// Load specific competitor details if requested
if (isset($_GET['competitor'])) {
    $selectedCompetitor = $_GET['competitor'];
    try {
        $api = getOrchestratorApi();
        $params = [];
        if ($startDate) $params['start_date'] = $startDate;
        if ($endDate) $params['end_date'] = $endDate;

        $competitorDetails = $api->get('/analytics/competitor/' . urlencode($selectedCompetitor), $params);
    } catch (Exception $e) {
        $error = 'Failed to load competitor details: ' . $e->getMessage();
    }
}

require_once __DIR__ . '/../src/includes/header.php';
?>

<h1>Analytics Dashboard</h1>

<?php if ($error): ?>
    <div class="error-message">
        <?php echo htmlspecialchars($error); ?>
    </div>
<?php endif; ?>

<!-- Date Filter Form -->
<section>
    <h2>Date Range Filter</h2>
    <form method="GET" action="/analytics.php">
        <div class="grid">
            <div>
                <label>
                    Quick Select:
                    <select name="days" id="quickSelect" onchange="toggleCustomDates()">
                        <option value="7" <?php echo $dateFilter === '7' ? 'selected' : ''; ?>>Last 7 days</option>
                        <option value="30" <?php echo $dateFilter === '30' ? 'selected' : ''; ?>>Last 30 days</option>
                        <option value="90" <?php echo $dateFilter === '90' ? 'selected' : ''; ?>>Last 90 days</option>
                        <option value="365" <?php echo $dateFilter === '365' ? 'selected' : ''; ?>>Last 365 days</option>
                        <option value="custom" <?php echo ($customStartDate || $customEndDate) ? 'selected' : ''; ?>>Custom Range</option>
                    </select>
                </label>
            </div>
            <div id="customDates" style="<?php echo ($customStartDate || $customEndDate) ? '' : 'display: none;'; ?>">
                <label>
                    Start Date:
                    <input type="date" name="start_date" value="<?php echo htmlspecialchars($customStartDate); ?>">
                </label>
            </div>
            <div id="customDatesEnd" style="<?php echo ($customStartDate || $customEndDate) ? '' : 'display: none;'; ?>">
                <label>
                    End Date:
                    <input type="date" name="end_date" value="<?php echo htmlspecialchars($customEndDate); ?>">
                </label>
            </div>
        </div>
        <button type="submit">Apply Filter</button>
    </form>
</section>

<!-- Overview Analytics -->
<?php if ($overview): ?>
<section class="mt-2">
    <h2>Overview</h2>
    <div class="grid">
        <div class="card">
            <h3>Total Jobs</h3>
            <p style="font-size: 2rem; margin: 0;">
                <?php echo number_format($overview['total_jobs'] ?? 0); ?>
            </p>
        </div>
        <div class="card">
            <h3>Total Mentions</h3>
            <p style="font-size: 2rem; margin: 0;">
                <?php echo number_format($overview['total_mentions'] ?? 0); ?>
            </p>
        </div>
        <div class="card">
            <h3>Unique Competitors</h3>
            <p style="font-size: 2rem; margin: 0;">
                <?php echo number_format($overview['unique_competitors'] ?? 0); ?>
            </p>
        </div>
    </div>

    <!-- Sentiment Distribution -->
    <?php if (isset($overview['sentiment_distribution'])): ?>
        <div class="mt-2">
            <h3>Sentiment Distribution</h3>
            <div class="grid">
                <?php
                $dist = $overview['sentiment_distribution'];
                $total = ($dist['positive'] ?? 0) + ($dist['negative'] ?? 0) + ($dist['neutral'] ?? 0);
                ?>
                <div class="card">
                    <span class="sentiment-badge sentiment-positive">Positive</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0;">
                        <?php echo $dist['positive'] ?? 0; ?>
                    </p>
                    <?php if ($total > 0): ?>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['positive'] / $total) * 100); ?>%; background-color: #4caf50;"></div>
                        </div>
                    <?php endif; ?>
                </div>
                <div class="card">
                    <span class="sentiment-badge sentiment-negative">Negative</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0;">
                        <?php echo $dist['negative'] ?? 0; ?>
                    </p>
                    <?php if ($total > 0): ?>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['negative'] / $total) * 100); ?>%; background-color: #f44336;"></div>
                        </div>
                    <?php endif; ?>
                </div>
                <div class="card">
                    <span class="sentiment-badge sentiment-neutral">Neutral</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0;">
                        <?php echo $dist['neutral'] ?? 0; ?>
                    </p>
                    <?php if ($total > 0): ?>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['neutral'] / $total) * 100); ?>%; background-color: #9e9e9e;"></div>
                        </div>
                    <?php endif; ?>
                </div>
            </div>
        </div>
    <?php endif; ?>
</section>
<?php endif; ?>

<!-- Top Competitors -->
<?php if (!empty($competitors)): ?>
<section class="mt-2">
    <h2>Top Competitors</h2>
    <div class="overflow-x-auto">
        <table>
            <thead>
                <tr>
                    <th>Competitor</th>
                    <th>Mentions</th>
                    <th>Positive</th>
                    <th>Negative</th>
                    <th>Neutral</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($competitors as $comp): ?>
                    <tr>
                        <td><strong><?php echo htmlspecialchars($comp['name']); ?></strong></td>
                        <td><?php echo number_format($comp['mention_count'] ?? 0); ?></td>
                        <td>
                            <span class="sentiment-badge sentiment-positive">
                                <?php echo $comp['positive'] ?? 0; ?>
                            </span>
                        </td>
                        <td>
                            <span class="sentiment-badge sentiment-negative">
                                <?php echo $comp['negative'] ?? 0; ?>
                            </span>
                        </td>
                        <td>
                            <span class="sentiment-badge sentiment-neutral">
                                <?php echo $comp['neutral'] ?? 0; ?>
                            </span>
                        </td>
                        <td>
                            <a href="?competitor=<?php echo urlencode($comp['name']); ?>&days=<?php echo urlencode($dateFilter); ?><?php echo $customStartDate ? '&start_date=' . urlencode($customStartDate) : ''; ?><?php echo $customEndDate ? '&end_date=' . urlencode($customEndDate) : ''; ?>" class="btn-small" role="button">View Details</a>
                        </td>
                    </tr>
                <?php endforeach; ?>
            </tbody>
        </table>
    </div>
</section>
<?php endif; ?>

<!-- Competitor Details -->
<?php if ($selectedCompetitor && $competitorDetails): ?>
<section class="mt-2">
    <h2>Details: <?php echo htmlspecialchars($selectedCompetitor); ?></h2>
    <p>
        <a href="/analytics.php?days=<?php echo urlencode($dateFilter); ?><?php echo $customStartDate ? '&start_date=' . urlencode($customStartDate) : ''; ?><?php echo $customEndDate ? '&end_date=' . urlencode($customEndDate) : ''; ?>">← Back to Overview</a>
    </p>

    <div class="grid">
        <div class="card">
            <h3>Total Mentions</h3>
            <p style="font-size: 2rem; margin: 0;">
                <?php echo number_format($competitorDetails['total_mentions'] ?? 0); ?>
            </p>
        </div>
        <div class="card">
            <h3>Sentiment Summary</h3>
            <p>
                <span class="sentiment-badge sentiment-positive">
                    Positive: <?php echo $competitorDetails['sentiment_counts']['positive'] ?? 0; ?>
                </span><br>
                <span class="sentiment-badge sentiment-negative">
                    Negative: <?php echo $competitorDetails['sentiment_counts']['negative'] ?? 0; ?>
                </span><br>
                <span class="sentiment-badge sentiment-neutral">
                    Neutral: <?php echo $competitorDetails['sentiment_counts']['neutral'] ?? 0; ?>
                </span>
            </p>
        </div>
    </div>

    <?php if (isset($competitorDetails['segments']) && !empty($competitorDetails['segments'])): ?>
        <h3 class="mt-2">Individual Mentions</h3>
        <?php foreach ($competitorDetails['segments'] as $segment): ?>
            <div class="segment-card">
                <div class="segment-header">
                    <span class="sentiment-badge sentiment-<?php echo strtolower(htmlspecialchars($segment['sentiment'] ?? 'neutral')); ?>">
                        <?php echo htmlspecialchars($segment['sentiment'] ?? 'Neutral'); ?>
                    </span>
                    <span class="detection-method">
                        <?php echo htmlspecialchars($segment['detection_method'] ?? 'Unknown'); ?>
                    </span>
                </div>

                <div class="segment-text">
                    <?php echo htmlspecialchars($segment['segment_text'] ?? 'No text'); ?>
                </div>

                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
                    <small>
                        Job: <a href="/job.php?id=<?php echo urlencode($segment['job_id'] ?? ''); ?>">
                            <?php echo htmlspecialchars(substr($segment['job_id'] ?? 'N/A', 0, 8)); ?>...
                        </a>
                    </small>
                    <?php if (isset($segment['created_at'])): ?>
                        <small><?php echo htmlspecialchars($segment['created_at']); ?></small>
                    <?php endif; ?>
                </div>
            </div>
        <?php endforeach; ?>
    <?php endif; ?>
</section>
<?php endif; ?>

<script>
    function toggleCustomDates() {
        const select = document.getElementById('quickSelect');
        const customDates = document.getElementById('customDates');
        const customDatesEnd = document.getElementById('customDatesEnd');

        if (select.value === 'custom') {
            customDates.style.display = 'block';
            customDatesEnd.style.display = 'block';
        } else {
            customDates.style.display = 'none';
            customDatesEnd.style.display = 'none';
        }
    }
</script>

<?php require_once __DIR__ . '/../src/includes/footer.php'; ?>
