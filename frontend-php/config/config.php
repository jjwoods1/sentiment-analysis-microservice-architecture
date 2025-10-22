<?php
/**
 * Application Configuration
 */

// API Endpoints
define('API_URL', getenv('API_URL') ?: 'http://10.1.0.35:8100');
define('SENTIMENT_API_URL', getenv('SENTIMENT_API_URL') ?: 'http://10.1.0.35:8008');

// Application Settings
define('APP_NAME', 'Sentiment Analysis');
define('APP_VERSION', '1.0.0');
define('ITEMS_PER_PAGE', 50);

// Timezone
date_default_timezone_set('UTC');

// Error Reporting (disable in production)
if (getenv('APP_ENV') === 'production') {
    error_reporting(0);
    ini_set('display_errors', '0');
} else {
    error_reporting(E_ALL);
    ini_set('display_errors', '1');
}

// Session Configuration
ini_set('session.cookie_httponly', 1);
ini_set('session.use_strict_mode', 1);
if (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') {
    ini_set('session.cookie_secure', 1);
}

// Start session if not already started
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
