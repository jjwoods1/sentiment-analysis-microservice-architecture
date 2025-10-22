<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$pageTitle = 'Admin Database Viewer';
$error = null;
$jobs = [];
$sentimentResults = [];
$storageFiles = [];

// Load data based on active tab
$activeTab = $_GET['tab'] ?? 'jobs';

try {
    $api = getOrchestratorApi();

    switch ($activeTab) {
        case 'jobs':
            $response = $api->get('/admin/database/jobs');
            $jobs = $response['jobs'] ?? [];
            break;

        case 'sentiment':
            $response = $api->get('/admin/database/sentiment_results');
            $sentimentResults = $response['sentiment_results'] ?? [];
            break;

        case 'storage':
            $response = $api->get('/admin/storage/files');
            $storageFiles = $response['files'] ?? [];
            break;
    }
} catch (Exception $e) {
    $error = 'Failed to load data: ' . $e->getMessage();
}

require_once __DIR__ . '/../src/includes/header.php';
?>

<h1>Admin Database Viewer</h1>

<?php if ($error): ?>
    <div class="error-message">
        <?php echo htmlspecialchars($error); ?>
    </div>
<?php endif; ?>

<p>View raw database tables and storage files.</p>

<!-- Tabs -->
<div class="tabs">
    <button class="tab-button <?php echo $activeTab === 'jobs' ? 'active' : ''; ?>" onclick="location.href='?tab=jobs'">
        Jobs (<?php echo count($jobs); ?>)
    </button>
    <button class="tab-button <?php echo $activeTab === 'sentiment' ? 'active' : ''; ?>" onclick="location.href='?tab=sentiment'">
        Sentiment Results (<?php echo count($sentimentResults); ?>)
    </button>
    <button class="tab-button <?php echo $activeTab === 'storage' ? 'active' : ''; ?>" onclick="location.href='?tab=storage'">
        Storage Files (<?php echo count($storageFiles); ?>)
    </button>
</div>

<!-- Search Box -->
<div style="margin-bottom: 1rem;">
    <label>
        Search:
        <input type="text" id="searchBox" placeholder="Search table data..." onkeyup="searchTable()">
    </label>
</div>

<!-- Jobs Tab -->
<?php if ($activeTab === 'jobs'): ?>
    <div class="tab-content active">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2>Jobs Table</h2>
            <button onclick="exportToJson('jobs')" class="btn-small">Export JSON</button>
        </div>

        <?php if (empty($jobs)): ?>
            <p>No jobs found.</p>
        <?php else: ?>
            <div class="overflow-x-auto">
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Source File</th>
                            <th>Status</th>
                            <th>Created At</th>
                            <th>Updated At</th>
                            <th>Completed At</th>
                            <th>Error Message</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($jobs as $job): ?>
                            <tr>
                                <td>
                                    <small><?php echo htmlspecialchars($job['id']); ?></small>
                                    <button onclick="copyToClipboard('<?php echo htmlspecialchars($job['id']); ?>')" class="btn-small" style="padding: 0.125rem 0.25rem;">Copy</button>
                                </td>
                                <td><?php echo htmlspecialchars($job['source_file'] ?? 'N/A'); ?></td>
                                <td>
                                    <span class="status-badge status-<?php echo strtolower(htmlspecialchars($job['status'])); ?>">
                                        <?php echo htmlspecialchars($job['status']); ?>
                                    </span>
                                </td>
                                <td><small><?php echo htmlspecialchars($job['created_at'] ?? 'N/A'); ?></small></td>
                                <td><small><?php echo htmlspecialchars($job['updated_at'] ?? 'N/A'); ?></small></td>
                                <td><small><?php echo htmlspecialchars($job['completed_at'] ?? 'N/A'); ?></small></td>
                                <td><small><?php echo htmlspecialchars($job['error_message'] ?? ''); ?></small></td>
                                <td>
                                    <a href="/job.php?id=<?php echo urlencode($job['id']); ?>" class="btn-small" role="button">View</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
<?php endif; ?>

<!-- Sentiment Results Tab -->
<?php if ($activeTab === 'sentiment'): ?>
    <div class="tab-content active">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2>Sentiment Results Table</h2>
            <button onclick="exportToJson('sentiment')" class="btn-small">Export JSON</button>
        </div>

        <?php if (empty($sentimentResults)): ?>
            <p>No sentiment results found.</p>
        <?php else: ?>
            <div class="overflow-x-auto">
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Job ID</th>
                            <th>Competitor</th>
                            <th>Sentiment</th>
                            <th>Method</th>
                            <th>Segment Text</th>
                            <th>Confidence</th>
                            <th>Created At</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($sentimentResults as $result): ?>
                            <tr>
                                <td><?php echo htmlspecialchars($result['id']); ?></td>
                                <td>
                                    <small><?php echo htmlspecialchars(substr($result['job_id'] ?? '', 0, 8)); ?>...</small>
                                    <a href="/job.php?id=<?php echo urlencode($result['job_id'] ?? ''); ?>" class="btn-small" style="padding: 0.125rem 0.25rem;">View</a>
                                </td>
                                <td><?php echo htmlspecialchars($result['competitor_name'] ?? 'N/A'); ?></td>
                                <td>
                                    <span class="sentiment-badge sentiment-<?php echo strtolower(htmlspecialchars($result['sentiment'] ?? 'neutral')); ?>">
                                        <?php echo htmlspecialchars($result['sentiment'] ?? 'Neutral'); ?>
                                    </span>
                                </td>
                                <td><small><?php echo htmlspecialchars($result['detection_method'] ?? 'N/A'); ?></small></td>
                                <td><small><?php echo htmlspecialchars(substr($result['segment_text'] ?? '', 0, 100)); ?>...</small></td>
                                <td><?php echo isset($result['confidence']) ? round($result['confidence'] * 100) . '%' : 'N/A'; ?></td>
                                <td><small><?php echo htmlspecialchars($result['created_at'] ?? 'N/A'); ?></small></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
<?php endif; ?>

<!-- Storage Files Tab -->
<?php if ($activeTab === 'storage'): ?>
    <div class="tab-content active">
        <h2>Storage Files</h2>

        <?php if (empty($storageFiles)): ?>
            <p>No storage files found.</p>
        <?php else: ?>
            <div class="overflow-x-auto">
                <table id="dataTable">
                    <thead>
                        <tr>
                            <th>Path</th>
                            <th>Size</th>
                            <th>Last Modified</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($storageFiles as $file): ?>
                            <tr>
                                <td>
                                    <small><?php echo htmlspecialchars($file['path'] ?? 'N/A'); ?></small>
                                    <button onclick="copyToClipboard('<?php echo htmlspecialchars($file['path'] ?? ''); ?>')" class="btn-small" style="padding: 0.125rem 0.25rem;">Copy</button>
                                </td>
                                <td><?php echo isset($file['size']) ? number_format($file['size']) . ' bytes' : 'N/A'; ?></td>
                                <td><small><?php echo htmlspecialchars($file['last_modified'] ?? 'N/A'); ?></small></td>
                                <td>
                                    <?php if (strpos($file['path'] ?? '', 'transcript') !== false): ?>
                                        <a href="<?php echo API_URL; ?>/admin/storage/download/<?php echo urlencode($file['path'] ?? ''); ?>" class="btn-small" role="button" target="_blank">Download</a>
                                    <?php endif; ?>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
<?php endif; ?>

<script>
    const currentData = <?php
        if ($activeTab === 'jobs') {
            echo json_encode($jobs);
        } elseif ($activeTab === 'sentiment') {
            echo json_encode($sentimentResults);
        } else {
            echo json_encode($storageFiles);
        }
    ?>;

    function searchTable() {
        const searchTerm = document.getElementById('searchBox').value.toLowerCase();
        const table = document.getElementById('dataTable');
        const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const cells = row.getElementsByTagName('td');
            let found = false;

            for (let j = 0; j < cells.length; j++) {
                const cellText = cells[j].textContent || cells[j].innerText;
                if (cellText.toLowerCase().indexOf(searchTerm) > -1) {
                    found = true;
                    break;
                }
            }

            row.style.display = found ? '' : 'none';
        }
    }

    function exportToJson(type) {
        const dataStr = JSON.stringify(currentData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = type + '_' + new Date().toISOString().split('T')[0] + '.json';
        link.click();
        URL.revokeObjectURL(url);
    }

    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                alert('Copied to clipboard!');
            }).catch(err => {
                console.error('Failed to copy:', err);
                fallbackCopyToClipboard(text);
            });
        } else {
            fallbackCopyToClipboard(text);
        }
    }

    function fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            alert('Copied to clipboard!');
        } catch (err) {
            console.error('Failed to copy:', err);
            alert('Failed to copy to clipboard');
        }
        document.body.removeChild(textArea);
    }
</script>

<?php require_once __DIR__ . '/../src/includes/footer.php'; ?>
