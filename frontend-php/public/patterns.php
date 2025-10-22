<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$pageTitle = 'Sentiment Patterns';
$error = null;
$success = null;
$positivePatterns = [];
$negativePatterns = [];

// Handle pattern operations
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $api = getSentimentApi();

    try {
        $action = $_POST['action'] ?? '';

        switch ($action) {
            case 'add_positive':
                $pattern = trim($_POST['pattern'] ?? '');
                if ($pattern) {
                    $api->post('/patterns/positive', ['pattern' => $pattern]);
                    $success = 'Positive pattern added successfully';
                }
                break;

            case 'add_negative':
                $pattern = trim($_POST['pattern'] ?? '');
                if ($pattern) {
                    $api->post('/patterns/negative', ['pattern' => $pattern]);
                    $success = 'Negative pattern added successfully';
                }
                break;

            case 'bulk_add_positive':
                $bulkText = $_POST['bulk_patterns'] ?? '';
                $patterns = array_filter(array_map('trim', explode("\n", $bulkText)));
                // Remove comments
                $patterns = array_filter($patterns, function($p) {
                    return !empty($p) && $p[0] !== '#';
                });
                if (!empty($patterns)) {
                    $api->put('/patterns/positive', ['patterns' => $patterns]);
                    $success = count($patterns) . ' positive patterns uploaded';
                }
                break;

            case 'bulk_add_negative':
                $bulkText = $_POST['bulk_patterns'] ?? '';
                $patterns = array_filter(array_map('trim', explode("\n", $bulkText)));
                // Remove comments
                $patterns = array_filter($patterns, function($p) {
                    return !empty($p) && $p[0] !== '#';
                });
                if (!empty($patterns)) {
                    $api->put('/patterns/negative', ['patterns' => $patterns]);
                    $success = count($patterns) . ' negative patterns uploaded';
                }
                break;

            case 'delete_positive':
                $pattern = $_POST['pattern'] ?? '';
                if ($pattern) {
                    $api->delete('/patterns/positive/' . urlencode($pattern));
                    $success = 'Positive pattern deleted';
                }
                break;

            case 'delete_negative':
                $pattern = $_POST['pattern'] ?? '';
                if ($pattern) {
                    $api->delete('/patterns/negative/' . urlencode($pattern));
                    $success = 'Negative pattern deleted';
                }
                break;

            case 'bulk_delete_positive':
                $patterns = $_POST['selected_patterns'] ?? [];
                if (!empty($patterns)) {
                    foreach ($patterns as $pattern) {
                        $api->delete('/patterns/positive/' . urlencode($pattern));
                    }
                    $success = count($patterns) . ' positive patterns deleted';
                }
                break;

            case 'bulk_delete_negative':
                $patterns = $_POST['selected_patterns'] ?? [];
                if (!empty($patterns)) {
                    foreach ($patterns as $pattern) {
                        $api->delete('/patterns/negative/' . urlencode($pattern));
                    }
                    $success = count($patterns) . ' negative patterns deleted';
                }
                break;
        }

        // Redirect to prevent form resubmission
        header('Location: /patterns.php?success=1');
        exit;
    } catch (Exception $e) {
        $error = 'Operation failed: ' . $e->getMessage();
    }
}

// Load patterns
try {
    $api = getSentimentApi();
    $positiveResponse = $api->get('/patterns/positive');
    $negativeResponse = $api->get('/patterns/negative');

    $positivePatterns = $positiveResponse['patterns'] ?? [];
    $negativePatterns = $negativeResponse['patterns'] ?? [];
} catch (Exception $e) {
    $error = 'Failed to load patterns: ' . $e->getMessage();
}

// Check for success from redirect
if (isset($_GET['success']) && $_GET['success'] == '1') {
    $success = 'Operation completed successfully';
}

require_once __DIR__ . '/../src/includes/header.php';
?>

<h1>Sentiment Pattern Management</h1>

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

<p>Manage positive and negative sentiment patterns used for rule-based sentiment detection.</p>

<div class="grid-2">
    <!-- Positive Patterns -->
    <div class="card">
        <h2>Positive Patterns</h2>
        <p><strong>Total:</strong> <span id="positiveCount"><?php echo count($positivePatterns); ?></span></p>

        <!-- Add Single Pattern -->
        <form method="POST" style="margin-bottom: 1rem;">
            <input type="hidden" name="action" value="add_positive">
            <label>
                Add Single Pattern:
                <input type="text" name="pattern" placeholder="Enter positive pattern" required>
            </label>
            <button type="submit" class="btn-small">Add</button>
        </form>

        <!-- Bulk Upload -->
        <details>
            <summary>Bulk Upload</summary>
            <form method="POST" style="margin-top: 1rem;">
                <input type="hidden" name="action" value="bulk_add_positive">
                <label>
                    Enter patterns (one per line, # for comments):
                    <textarea name="bulk_patterns" rows="10" placeholder="excellent&#10;great product&#10;# This is a comment"></textarea>
                </label>
                <button type="submit">Upload All</button>
            </form>
        </details>

        <!-- Search -->
        <label style="margin-top: 1rem;">
            Search:
            <input type="text" id="positiveSearch" placeholder="Filter patterns..." onkeyup="filterPatterns('positive')">
        </label>

        <!-- Pattern List -->
        <div class="pattern-list" id="positiveList">
            <form method="POST" id="positiveDeleteForm">
                <input type="hidden" name="action" value="bulk_delete_positive">
                <div style="margin-bottom: 0.5rem;">
                    <button type="button" onclick="selectAllPositive()" class="btn-small">Select All</button>
                    <button type="button" onclick="deselectAllPositive()" class="btn-small">Deselect All</button>
                    <button type="submit" class="btn-small" onclick="return confirm('Delete selected patterns?')">Delete Selected</button>
                </div>

                <?php foreach ($positivePatterns as $pattern): ?>
                    <div class="pattern-item" data-pattern="<?php echo htmlspecialchars($pattern); ?>">
                        <label>
                            <input type="checkbox" name="selected_patterns[]" value="<?php echo htmlspecialchars($pattern); ?>" class="positive-checkbox">
                            <?php echo htmlspecialchars($pattern); ?>
                        </label>
                        <form method="POST" style="display: inline;" onsubmit="return confirm('Delete this pattern?')">
                            <input type="hidden" name="action" value="delete_positive">
                            <input type="hidden" name="pattern" value="<?php echo htmlspecialchars($pattern); ?>">
                            <button type="submit" class="btn-small" style="padding: 0.125rem 0.25rem;">×</button>
                        </form>
                    </div>
                <?php endforeach; ?>

                <?php if (empty($positivePatterns)): ?>
                    <p>No positive patterns found.</p>
                <?php endif; ?>
            </form>
        </div>
    </div>

    <!-- Negative Patterns -->
    <div class="card">
        <h2>Negative Patterns</h2>
        <p><strong>Total:</strong> <span id="negativeCount"><?php echo count($negativePatterns); ?></span></p>

        <!-- Add Single Pattern -->
        <form method="POST" style="margin-bottom: 1rem;">
            <input type="hidden" name="action" value="add_negative">
            <label>
                Add Single Pattern:
                <input type="text" name="pattern" placeholder="Enter negative pattern" required>
            </label>
            <button type="submit" class="btn-small">Add</button>
        </form>

        <!-- Bulk Upload -->
        <details>
            <summary>Bulk Upload</summary>
            <form method="POST" style="margin-top: 1rem;">
                <input type="hidden" name="action" value="bulk_add_negative">
                <label>
                    Enter patterns (one per line, # for comments):
                    <textarea name="bulk_patterns" rows="10" placeholder="terrible&#10;bad service&#10;# This is a comment"></textarea>
                </label>
                <button type="submit">Upload All</button>
            </form>
        </details>

        <!-- Search -->
        <label style="margin-top: 1rem;">
            Search:
            <input type="text" id="negativeSearch" placeholder="Filter patterns..." onkeyup="filterPatterns('negative')">
        </label>

        <!-- Pattern List -->
        <div class="pattern-list" id="negativeList">
            <form method="POST" id="negativeDeleteForm">
                <input type="hidden" name="action" value="bulk_delete_negative">
                <div style="margin-bottom: 0.5rem;">
                    <button type="button" onclick="selectAllNegative()" class="btn-small">Select All</button>
                    <button type="button" onclick="deselectAllNegative()" class="btn-small">Deselect All</button>
                    <button type="submit" class="btn-small" onclick="return confirm('Delete selected patterns?')">Delete Selected</button>
                </div>

                <?php foreach ($negativePatterns as $pattern): ?>
                    <div class="pattern-item" data-pattern="<?php echo htmlspecialchars($pattern); ?>">
                        <label>
                            <input type="checkbox" name="selected_patterns[]" value="<?php echo htmlspecialchars($pattern); ?>" class="negative-checkbox">
                            <?php echo htmlspecialchars($pattern); ?>
                        </label>
                        <form method="POST" style="display: inline;" onsubmit="return confirm('Delete this pattern?')">
                            <input type="hidden" name="action" value="delete_negative">
                            <input type="hidden" name="pattern" value="<?php echo htmlspecialchars($pattern); ?>">
                            <button type="submit" class="btn-small" style="padding: 0.125rem 0.25rem;">×</button>
                        </form>
                    </div>
                <?php endforeach; ?>

                <?php if (empty($negativePatterns)): ?>
                    <p>No negative patterns found.</p>
                <?php endif; ?>
            </form>
        </div>
    </div>
</div>

<script>
    function filterPatterns(type) {
        const searchInput = document.getElementById(type + 'Search');
        const searchTerm = searchInput.value.toLowerCase();
        const patternItems = document.querySelectorAll('#' + type + 'List .pattern-item');

        let visibleCount = 0;
        patternItems.forEach(item => {
            const pattern = item.getAttribute('data-pattern').toLowerCase();
            if (pattern.includes(searchTerm)) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });

        // Update count
        document.getElementById(type + 'Count').textContent = visibleCount;
    }

    function selectAllPositive() {
        const checkboxes = document.querySelectorAll('.positive-checkbox');
        checkboxes.forEach(cb => {
            if (cb.closest('.pattern-item').style.display !== 'none') {
                cb.checked = true;
            }
        });
    }

    function deselectAllPositive() {
        const checkboxes = document.querySelectorAll('.positive-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
    }

    function selectAllNegative() {
        const checkboxes = document.querySelectorAll('.negative-checkbox');
        checkboxes.forEach(cb => {
            if (cb.closest('.pattern-item').style.display !== 'none') {
                cb.checked = true;
            }
        });
    }

    function deselectAllNegative() {
        const checkboxes = document.querySelectorAll('.negative-checkbox');
        checkboxes.forEach(cb => cb.checked = false);
    }
</script>

<?php require_once __DIR__ . '/../src/includes/footer.php'; ?>
