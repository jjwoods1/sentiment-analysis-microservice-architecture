<?php
require_once __DIR__ . '/../config/config.php';
require_once __DIR__ . '/../src/api/ApiClient.php';

$pageTitle = 'API Connectivity Test';
$results = [];

// Test Orchestrator API endpoints
$orchestratorTests = [
    'Health Check' => '/health',
    'Get Jobs' => '/jobs',
    'Get Analytics Overview' => '/analytics/overview',
    'Get Competitors List' => '/analytics/competitors/list',
    'Get Admin Jobs' => '/admin/database/jobs',
    'Get Admin Sentiment Results' => '/admin/database/sentiment_results',
    'Get Storage Files' => '/admin/storage/files',
];

// Test Sentiment API endpoints
$sentimentTests = [
    'Get Positive Patterns' => '/patterns/positive',
    'Get Negative Patterns' => '/patterns/negative',
];

echo "<!DOCTYPE html>\n";
echo "<html lang='en'>\n";
echo "<head>\n";
echo "    <meta charset='UTF-8'>\n";
echo "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n";
echo "    <title>API Connectivity Test</title>\n";
echo "    <link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css'>\n";
echo "    <style>\n";
echo "        .success { background-color: #e8f5e9; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid #4caf50; }\n";
echo "        .error { background-color: #ffebee; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid #f44336; }\n";
echo "        .info { background-color: #e3f2fd; padding: 1rem; margin: 0.5rem 0; border-left: 4px solid #2196f3; }\n";
echo "        pre { background-color: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; }\n";
echo "        .endpoint { font-family: monospace; font-weight: bold; }\n";
echo "    </style>\n";
echo "</head>\n";
echo "<body>\n";
echo "<main class='container'>\n";
echo "<h1>API Connectivity Test</h1>\n";
echo "<p><a href='/index.php'>← Back to Home</a></p>\n";

echo "<div class='info'>\n";
echo "    <strong>Configuration:</strong><br>\n";
echo "    Orchestrator API: <code>" . htmlspecialchars(API_URL) . "</code><br>\n";
echo "    Sentiment API: <code>" . htmlspecialchars(SENTIMENT_API_URL) . "</code>\n";
echo "</div>\n";

// Test Orchestrator API
echo "<h2>Orchestrator API Tests</h2>\n";

foreach ($orchestratorTests as $testName => $endpoint) {
    echo "<details>\n";
    echo "    <summary><strong>" . htmlspecialchars($testName) . "</strong> - <span class='endpoint'>" . htmlspecialchars($endpoint) . "</span></summary>\n";

    try {
        $api = getOrchestratorApi();
        $startTime = microtime(true);
        $result = $api->get($endpoint);
        $endTime = microtime(true);
        $duration = round(($endTime - $startTime) * 1000, 2);

        echo "    <div class='success'>\n";
        echo "        ✅ <strong>Success</strong> (Response time: {$duration}ms)<br>\n";
        echo "        Data received: " . count($result) . " fields<br>\n";

        // Show sample data
        if (is_array($result)) {
            if (isset($result['jobs'])) {
                echo "        Jobs count: " . count($result['jobs']) . "<br>\n";
            } elseif (isset($result['sentiment_results'])) {
                echo "        Sentiment results count: " . count($result['sentiment_results']) . "<br>\n";
            } elseif (isset($result['files'])) {
                echo "        Files count: " . count($result['files']) . "<br>\n";
            } elseif (isset($result['competitors'])) {
                echo "        Competitors count: " . count($result['competitors']) . "<br>\n";
            }
        }

        echo "        <details>\n";
        echo "            <summary>View Response Data</summary>\n";
        echo "            <pre>" . htmlspecialchars(json_encode($result, JSON_PRETTY_PRINT)) . "</pre>\n";
        echo "        </details>\n";
        echo "    </div>\n";

    } catch (Exception $e) {
        echo "    <div class='error'>\n";
        echo "        ❌ <strong>Error:</strong> " . htmlspecialchars($e->getMessage()) . "<br>\n";
        echo "        Code: " . $e->getCode() . "\n";
        echo "    </div>\n";
    }

    echo "</details>\n";
}

// Test Sentiment API
echo "<h2>Sentiment API Tests</h2>\n";

foreach ($sentimentTests as $testName => $endpoint) {
    echo "<details>\n";
    echo "    <summary><strong>" . htmlspecialchars($testName) . "</strong> - <span class='endpoint'>" . htmlspecialchars($endpoint) . "</span></summary>\n";

    try {
        $api = getSentimentApi();
        $startTime = microtime(true);
        $result = $api->get($endpoint);
        $endTime = microtime(true);
        $duration = round(($endTime - $startTime) * 1000, 2);

        echo "    <div class='success'>\n";
        echo "        ✅ <strong>Success</strong> (Response time: {$duration}ms)<br>\n";

        if (isset($result['patterns'])) {
            echo "        Patterns count: " . count($result['patterns']) . "<br>\n";
        }

        echo "        <details>\n";
        echo "            <summary>View Response Data</summary>\n";
        echo "            <pre>" . htmlspecialchars(json_encode($result, JSON_PRETTY_PRINT)) . "</pre>\n";
        echo "        </details>\n";
        echo "    </div>\n";

    } catch (Exception $e) {
        echo "    <div class='error'>\n";
        echo "        ❌ <strong>Error:</strong> " . htmlspecialchars($e->getMessage()) . "<br>\n";
        echo "        Code: " . $e->getCode() . "\n";
        echo "    </div>\n";
    }

    echo "</details>\n";
}

// PHP Configuration
echo "<h2>PHP Configuration</h2>\n";
echo "<details>\n";
echo "    <summary>View PHP Info</summary>\n";
echo "    <table>\n";
echo "        <tr><th>Setting</th><th>Value</th></tr>\n";
echo "        <tr><td>PHP Version</td><td>" . phpversion() . "</td></tr>\n";
echo "        <tr><td>cURL Enabled</td><td>" . (function_exists('curl_version') ? '✅ Yes' : '❌ No') . "</td></tr>\n";
if (function_exists('curl_version')) {
    $curlVersion = curl_version();
    echo "        <tr><td>cURL Version</td><td>" . $curlVersion['version'] . "</td></tr>\n";
}
echo "        <tr><td>allow_url_fopen</td><td>" . (ini_get('allow_url_fopen') ? 'On' : 'Off') . "</td></tr>\n";
echo "        <tr><td>upload_max_filesize</td><td>" . ini_get('upload_max_filesize') . "</td></tr>\n";
echo "        <tr><td>post_max_size</td><td>" . ini_get('post_max_size') . "</td></tr>\n";
echo "        <tr><td>max_execution_time</td><td>" . ini_get('max_execution_time') . "s</td></tr>\n";
echo "    </table>\n";
echo "</details>\n";

echo "</main>\n";
echo "</body>\n";
echo "</html>\n";
