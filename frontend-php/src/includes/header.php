<?php
if (!defined('API_URL')) {
    require_once __DIR__ . '/../../config/config.php';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo isset($pageTitle) ? htmlspecialchars($pageTitle) . ' - ' : ''; ?><?php echo APP_NAME; ?></title>

    <!-- Pico CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">

    <!-- Custom Styles -->
    <style>
        :root {
            --spacing: 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--spacing);
        }

        nav ul {
            list-style: none;
            padding: 0;
            display: flex;
            gap: 1rem;
        }

        nav a {
            text-decoration: none;
        }

        nav a:hover {
            text-decoration: underline;
        }

        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .status-pending { background-color: #ffc107; color: #000; }
        .status-processing { background-color: #2196f3; color: #fff; }
        .status-completed { background-color: #4caf50; color: #fff; }
        .status-failed { background-color: #f44336; color: #fff; }

        .sentiment-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .sentiment-positive { background-color: #4caf50; color: #fff; }
        .sentiment-negative { background-color: #f44336; color: #fff; }
        .sentiment-neutral { background-color: #9e9e9e; color: #fff; }

        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }

        .progress-fill {
            height: 100%;
            background-color: #2196f3;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.75rem;
        }

        .error-message {
            background-color: #ffebee;
            border-left: 4px solid #f44336;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }

        .success-message {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }

        .segment-card {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            margin: 0.5rem 0;
            background-color: #fafafa;
        }

        .segment-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }

        .segment-text {
            background-color: #fff;
            padding: 0.75rem;
            border-left: 3px solid #2196f3;
            margin: 0.5rem 0;
            font-style: italic;
        }

        .detection-method {
            font-size: 0.75rem;
            color: #666;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        table th {
            text-align: left;
            background-color: #f5f5f5;
        }

        .btn-small {
            padding: 0.25rem 0.5rem;
            font-size: 0.875rem;
        }

        .text-center {
            text-align: center;
        }

        .mt-2 { margin-top: 2rem; }
        .mb-2 { margin-bottom: 2rem; }

        details {
            margin: 1rem 0;
        }

        summary {
            cursor: pointer;
            font-weight: 600;
            padding: 0.5rem;
            background-color: #f5f5f5;
            border-radius: 4px;
        }

        summary:hover {
            background-color: #e0e0e0;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }

        .card {
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            background-color: #fff;
        }

        .pattern-list {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 0.5rem;
        }

        .pattern-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem;
            border-bottom: 1px solid #eee;
        }

        .pattern-item:last-child {
            border-bottom: none;
        }

        .tabs {
            display: flex;
            gap: 0.5rem;
            border-bottom: 2px solid #ddd;
            margin-bottom: 1rem;
        }

        .tab-button {
            padding: 0.5rem 1rem;
            border: none;
            background: none;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
        }

        .tab-button.active {
            border-bottom-color: #2196f3;
            font-weight: 600;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        .overflow-x-auto {
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <nav class="container-fluid">
        <ul>
            <li><strong><?php echo APP_NAME; ?></strong></li>
        </ul>
        <ul>
            <li><a href="/index.php">Home</a></li>
            <li><a href="/analytics.php">Analytics</a></li>
            <li><a href="/patterns.php">Patterns</a></li>
            <li><a href="/admin.php">Admin</a></li>
        </ul>
    </nav>

    <main class="container">
