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

// Helper function to convert sentiment distribution array to associative array
function processSentimentDistribution($sentimentArray) {
    $result = ['positive' => 0, 'negative' => 0, 'neutral' => 0, 'unknown' => 0];
    if (is_array($sentimentArray)) {
        foreach ($sentimentArray as $item) {
            if (isset($item['sentiment']) && isset($item['count'])) {
                $sentiment = strtolower($item['sentiment']);
                $result[$sentiment] = $item['count'];
            }
        }
    }
    return $result;
}

// Helper function to convert sentiment breakdown array to associative array
function processSentimentBreakdown($breakdownArray) {
    $result = ['positive' => 0, 'negative' => 0, 'neutral' => 0, 'unknown' => 0];
    if (is_array($breakdownArray)) {
        foreach ($breakdownArray as $item) {
            if (isset($item['sentiment']) && isset($item['count'])) {
                $sentiment = strtolower($item['sentiment']);
                $result[$sentiment] = $item['count'];
            }
        }
    }
    return $result;
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
<section class="card">
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
    <h2>Overview Statistics</h2>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        <div class="card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;">
            <h3 style="color: white; font-size: 0.9rem; margin-bottom: 0.5rem;">Total Jobs</h3>
            <p style="font-size: 2.5rem; margin: 0; font-weight: bold;">
                <?php echo number_format($overview['total_jobs'] ?? 0); ?>
            </p>
            <small style="opacity: 0.9;">Processing runs</small>
        </div>
        <div class="card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border: none;">
            <h3 style="color: white; font-size: 0.9rem; margin-bottom: 0.5rem;">Total Competitors</h3>
            <p style="font-size: 2.5rem; margin: 0; font-weight: bold;">
                <?php echo number_format($overview['total_competitors'] ?? 0); ?>
            </p>
            <small style="opacity: 0.9;">Unique mentions</small>
        </div>
        <div class="card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; border: none;">
            <h3 style="color: white; font-size: 0.9rem; margin-bottom: 0.5rem;">Total Mentions</h3>
            <p style="font-size: 2.5rem; margin: 0; font-weight: bold;">
                <?php
                // Calculate total mentions from sentiment distribution
                $totalMentions = 0;
                if (isset($overview['sentiment_distribution']) && is_array($overview['sentiment_distribution'])) {
                    foreach ($overview['sentiment_distribution'] as $item) {
                        $totalMentions += $item['count'] ?? 0;
                    }
                }
                echo number_format($totalMentions);
                ?>
            </p>
            <small style="opacity: 0.9;">Across all jobs</small>
        </div>
    </div>

    <!-- Sentiment Distribution -->
    <?php if (isset($overview['sentiment_distribution']) && is_array($overview['sentiment_distribution'])): ?>
        <div class="mt-2">
            <h3>Sentiment Distribution</h3>
            <?php
            $dist = processSentimentDistribution($overview['sentiment_distribution']);
            $total = $dist['positive'] + $dist['negative'] + $dist['neutral'] + $dist['unknown'];
            ?>

            <?php if ($total > 0): ?>
                <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                    <div class="card" style="border-left: 4px solid #4caf50;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="sentiment-badge sentiment-positive">Positive</span>
                            <strong style="font-size: 1.2rem;"><?php echo round(($dist['positive'] / $total) * 100); ?>%</strong>
                        </div>
                        <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #4caf50;">
                            <?php echo number_format($dist['positive']); ?>
                        </p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['positive'] / $total) * 100); ?>%; background-color: #4caf50;"></div>
                        </div>
                    </div>
                    <div class="card" style="border-left: 4px solid #f44336;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="sentiment-badge sentiment-negative">Negative</span>
                            <strong style="font-size: 1.2rem;"><?php echo round(($dist['negative'] / $total) * 100); ?>%</strong>
                        </div>
                        <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #f44336;">
                            <?php echo number_format($dist['negative']); ?>
                        </p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['negative'] / $total) * 100); ?>%; background-color: #f44336;"></div>
                        </div>
                    </div>
                    <div class="card" style="border-left: 4px solid #9e9e9e;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="sentiment-badge sentiment-neutral">Neutral</span>
                            <strong style="font-size: 1.2rem;"><?php echo round(($dist['neutral'] / $total) * 100); ?>%</strong>
                        </div>
                        <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #9e9e9e;">
                            <?php echo number_format($dist['neutral']); ?>
                        </p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['neutral'] / $total) * 100); ?>%; background-color: #9e9e9e;"></div>
                        </div>
                    </div>
                    <?php if ($dist['unknown'] > 0): ?>
                    <div class="card" style="border-left: 4px solid #ff9800;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="sentiment-badge" style="background-color: #ff9800;">Unknown</span>
                            <strong style="font-size: 1.2rem;"><?php echo round(($dist['unknown'] / $total) * 100); ?>%</strong>
                        </div>
                        <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #ff9800;">
                            <?php echo number_format($dist['unknown']); ?>
                        </p>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: <?php echo round(($dist['unknown'] / $total) * 100); ?>%; background-color: #ff9800;"></div>
                        </div>
                    </div>
                    <?php endif; ?>
                </div>
            <?php else: ?>
                <p>No sentiment data available for the selected date range.</p>
            <?php endif; ?>
        </div>
    <?php endif; ?>
</section>
<?php endif; ?>

<!-- Top Competitors -->
<?php if (!empty($competitors)): ?>
<section class="mt-2">
    <h2>Competitors Analysis</h2>
    <div class="overflow-x-auto">
        <table>
            <thead>
                <tr>
                    <th>Competitor</th>
                    <th>Total Mentions</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($competitors as $comp): ?>
                    <tr>
                        <td><strong><?php echo htmlspecialchars($comp['name']); ?></strong></td>
                        <td>
                            <span style="background: #e3f2fd; padding: 0.25rem 0.75rem; border-radius: 12px; font-weight: 600;">
                                <?php echo number_format($comp['mention_count'] ?? 0); ?>
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
<section class="mt-2" style="border: 2px solid #2196f3; border-radius: 8px; padding: 1.5rem; background: #f8f9fa;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2 style="margin: 0;">📊 <?php echo htmlspecialchars($selectedCompetitor); ?></h2>
        <a href="/analytics.php?days=<?php echo urlencode($dateFilter); ?><?php echo $customStartDate ? '&start_date=' . urlencode($customStartDate) : ''; ?><?php echo $customEndDate ? '&end_date=' . urlencode($customEndDate) : ''; ?>">← Back to Overview</a>
    </div>

    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
        <div class="card" style="background: white;">
            <h3 style="font-size: 0.9rem; color: #666;">Total Mentions</h3>
            <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #2196f3;">
                <?php echo number_format($competitorDetails['total_mentions'] ?? 0); ?>
            </p>
        </div>
        <div class="card" style="background: white;">
            <h3 style="font-size: 0.9rem; color: #666;">Unique Calls</h3>
            <p style="font-size: 2rem; margin: 0.5rem 0; font-weight: bold; color: #2196f3;">
                <?php echo number_format($competitorDetails['unique_calls'] ?? 0); ?>
            </p>
        </div>
    </div>

    <?php if (isset($competitorDetails['sentiment_breakdown']) && is_array($competitorDetails['sentiment_breakdown'])): ?>
        <h3 class="mt-2">Sentiment Breakdown</h3>
        <?php
        $breakdown = processSentimentBreakdown($competitorDetails['sentiment_breakdown']);
        $total = $breakdown['positive'] + $breakdown['negative'] + $breakdown['neutral'] + $breakdown['unknown'];
        ?>

        <?php if ($total > 0): ?>
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));">
                <div class="card" style="background: white; border-left: 4px solid #4caf50;">
                    <span class="sentiment-badge sentiment-positive">Positive</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0; font-weight: bold;">
                        <?php echo number_format($breakdown['positive']); ?>
                    </p>
                    <small><?php echo round(($breakdown['positive'] / $total) * 100); ?>%</small>
                </div>
                <div class="card" style="background: white; border-left: 4px solid #f44336;">
                    <span class="sentiment-badge sentiment-negative">Negative</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0; font-weight: bold;">
                        <?php echo number_format($breakdown['negative']); ?>
                    </p>
                    <small><?php echo round(($breakdown['negative'] / $total) * 100); ?>%</small>
                </div>
                <div class="card" style="background: white; border-left: 4px solid #9e9e9e;">
                    <span class="sentiment-badge sentiment-neutral">Neutral</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0; font-weight: bold;">
                        <?php echo number_format($breakdown['neutral']); ?>
                    </p>
                    <small><?php echo round(($breakdown['neutral'] / $total) * 100); ?>%</small>
                </div>
                <?php if ($breakdown['unknown'] > 0): ?>
                <div class="card" style="background: white; border-left: 4px solid #ff9800;">
                    <span class="sentiment-badge" style="background-color: #ff9800;">Unknown</span>
                    <p style="font-size: 1.5rem; margin: 0.5rem 0; font-weight: bold;">
                        <?php echo number_format($breakdown['unknown']); ?>
                    </p>
                    <small><?php echo round(($breakdown['unknown'] / $total) * 100); ?>%</small>
                </div>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    <?php endif; ?>

    <?php if (isset($competitorDetails['segments']) && !empty($competitorDetails['segments'])): ?>
        <h3 class="mt-2">Individual Mentions (<?php echo count($competitorDetails['segments']); ?>)</h3>
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

                <div style="display: flex; justify-content: space-between; margin-top: 0.5rem; flex-wrap: wrap; gap: 0.5rem;">
                    <small>
                        Job: <a href="/job.php?id=<?php echo urlencode($segment['job_id'] ?? ''); ?>">
                            <?php echo htmlspecialchars(substr($segment['job_id'] ?? 'N/A', 0, 8)); ?>...
                        </a>
                    </small>
                    <?php if (isset($segment['start_time']) && isset($segment['end_time'])): ?>
                        <small>
                            Time: <?php echo htmlspecialchars($segment['start_time']); ?> - <?php echo htmlspecialchars($segment['end_time']); ?>
                        </small>
                    <?php endif; ?>
                    <?php if (isset($segment['created_at'])): ?>
                        <small><?php echo htmlspecialchars(date('M j, Y g:i A', strtotime($segment['created_at']))); ?></small>
                    <?php endif; ?>
                </div>

                <?php if (isset($segment['detection_details']) && $segment['detection_details']): ?>
                    <details style="margin-top: 0.5rem;">
                        <summary style="cursor: pointer; color: #666;">Detection Details</summary>
                        <p style="margin-top: 0.5rem;"><small><?php echo htmlspecialchars($segment['detection_details']); ?></small></p>
                    </details>
                <?php endif; ?>
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
