<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$pageTitle = 'Home';
$error = null;
$success = null;
$jobs = [];
$loading = true;

// Handle file upload
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['audio_file'])) {
    try {
        $uploadedFile = $_FILES['audio_file'];

        if ($uploadedFile['error'] !== UPLOAD_ERR_OK) {
            throw new Exception('File upload failed');
        }

        $api = getOrchestratorApi();
        $result = $api->uploadFile('/upload', 'file', $uploadedFile['tmp_name']);

        $success = 'File uploaded successfully! Job ID: ' . htmlspecialchars($result['job_id']);

        // Redirect to prevent form resubmission
        header('Location: /index.php?success=1');
        exit;
    } catch (Exception $e) {
        $error = 'Upload failed: ' . $e->getMessage();
    }
}

// Load jobs list
try {
    $api = getOrchestratorApi();
    $response = $api->get('/jobs', ['limit' => ITEMS_PER_PAGE]);
    $jobs = $response['jobs'] ?? [];
    $loading = false;
} catch (Exception $e) {
    $error = 'Failed to load jobs: ' . $e->getMessage();
    $loading = false;
}

// Check for success message from redirect
if (isset($_GET['success']) && $_GET['success'] == '1') {
    $success = 'File uploaded successfully!';
}

require_once __DIR__ . '/../src/includes/header.php';
?>

<h1>Audio Upload & Job Management</h1>

<?php if ($success): ?>
    <div class="success-message">
        <?php echo htmlspecialchars($success); ?>
    </div>
<?php endif; ?>

<?php if ($error): ?>
    <div class="error-message">
        <?php echo htmlspecialchars($error); ?>
    </div>
<?php endif; ?>

<!-- Upload Form -->
<section>
    <h2>Upload Audio File</h2>
    <form method="POST" enctype="multipart/form-data" id="uploadForm">
        <label for="audio_file">
            Select audio file to analyze:
            <input type="file" id="audio_file" name="audio_file" accept="audio/*" required>
        </label>
        <button type="submit">Upload & Process</button>
    </form>
</section>

<!-- Jobs List -->
<section class="mt-2">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>Recent Jobs</h2>
        <button onclick="refreshJobs()" class="btn-small">Refresh</button>
    </div>

    <div id="jobsContainer">
        <?php if ($loading): ?>
            <p aria-busy="true">Loading jobs...</p>
        <?php elseif (empty($jobs)): ?>
            <p>No jobs found. Upload an audio file to get started.</p>
        <?php else: ?>
            <div class="overflow-x-auto">
                <table>
                    <thead>
                        <tr>
                            <th>Job ID</th>
                            <th>Source File</th>
                            <th>Status</th>
                            <th>Created At</th>
                            <th>Progress</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="jobsTableBody">
                        <?php foreach ($jobs as $job): ?>
                            <tr data-job-id="<?php echo htmlspecialchars($job['id']); ?>" data-status="<?php echo htmlspecialchars($job['status']); ?>">
                                <td><?php echo htmlspecialchars($job['id']); ?></td>
                                <td><?php echo htmlspecialchars($job['source_file'] ?? 'N/A'); ?></td>
                                <td>
                                    <span class="status-badge status-<?php echo strtolower(htmlspecialchars($job['status'])); ?>">
                                        <?php echo htmlspecialchars($job['status']); ?>
                                    </span>
                                </td>
                                <td><?php echo htmlspecialchars($job['created_at'] ?? 'N/A'); ?></td>
                                <td>
                                    <?php if (isset($job['progress'])): ?>
                                        <?php echo htmlspecialchars($job['progress']); ?>%
                                    <?php else: ?>
                                        N/A
                                    <?php endif; ?>
                                </td>
                                <td>
                                    <a href="/job.php?id=<?php echo urlencode($job['id']); ?>" class="btn-small" role="button">View Details</a>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        <?php endif; ?>
    </div>
</section>

<script>
    // Auto-refresh for jobs with PENDING or PROCESSING status
    let pollInterval = null;

    function hasActiveJobs() {
        const rows = document.querySelectorAll('#jobsTableBody tr');
        for (let row of rows) {
            const status = row.getAttribute('data-status');
            if (status === 'PENDING' || status === 'PROCESSING') {
                return true;
            }
        }
        return false;
    }

    async function refreshJobs() {
        try {
            const response = await fetch('<?php echo API_URL; ?>/jobs?limit=<?php echo ITEMS_PER_PAGE; ?>');
            if (!response.ok) throw new Error('Failed to fetch jobs');

            const data = await response.json();
            const jobs = data.jobs || [];

            const tbody = document.getElementById('jobsTableBody');
            if (jobs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No jobs found.</td></tr>';
            } else {
                tbody.innerHTML = jobs.map(job => `
                    <tr data-job-id="${escapeHtml(job.id)}" data-status="${escapeHtml(job.status)}">
                        <td>${escapeHtml(job.id)}</td>
                        <td>${escapeHtml(job.source_file || 'N/A')}</td>
                        <td>
                            <span class="status-badge status-${job.status.toLowerCase()}">
                                ${escapeHtml(job.status)}
                            </span>
                        </td>
                        <td>${escapeHtml(job.created_at || 'N/A')}</td>
                        <td>${job.progress !== undefined ? escapeHtml(job.progress) + '%' : 'N/A'}</td>
                        <td>
                            <a href="/job.php?id=${encodeURIComponent(job.id)}" class="btn-small" role="button">View Details</a>
                        </td>
                    </tr>
                `).join('');
            }

            startPollingIfNeeded();
        } catch (error) {
            console.error('Failed to refresh jobs:', error);
        }
    }

    function startPollingIfNeeded() {
        if (hasActiveJobs()) {
            if (!pollInterval) {
                pollInterval = setInterval(refreshJobs, 5000); // Poll every 5 seconds
            }
        } else {
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Start polling on page load if needed
    startPollingIfNeeded();

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
    });
</script>

<?php require_once __DIR__ . '/../src/includes/footer.php'; ?>
