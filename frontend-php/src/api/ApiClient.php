<?php
/**
 * API Client for communicating with backend services
 */

class ApiClient {
    private $baseUrl;
    private $timeout;

    public function __construct($baseUrl, $timeout = 30) {
        $this->baseUrl = rtrim($baseUrl, '/');
        $this->timeout = $timeout;
    }

    /**
     * Make a GET request
     */
    public function get($endpoint, $params = []) {
        $url = $this->baseUrl . $endpoint;

        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }

        return $this->request('GET', $url);
    }

    /**
     * Make a POST request
     */
    public function post($endpoint, $data = null, $isFormData = false) {
        $url = $this->baseUrl . $endpoint;
        return $this->request('POST', $url, $data, $isFormData);
    }

    /**
     * Make a PUT request
     */
    public function put($endpoint, $data = null) {
        $url = $this->baseUrl . $endpoint;
        return $this->request('PUT', $url, $data);
    }

    /**
     * Make a DELETE request
     */
    public function delete($endpoint) {
        $url = $this->baseUrl . $endpoint;
        return $this->request('DELETE', $url);
    }

    /**
     * Execute HTTP request using cURL
     */
    private function request($method, $url, $data = null, $isFormData = false) {
        $ch = curl_init();

        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

        $headers = [];

        if ($data !== null && !$isFormData) {
            $jsonData = json_encode($data);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $jsonData);
            $headers[] = 'Content-Type: application/json';
            $headers[] = 'Content-Length: ' . strlen($jsonData);
        } elseif ($data !== null && $isFormData) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
            // Let cURL set Content-Type for multipart/form-data
        }

        if (!empty($headers)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        }

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);

        curl_close($ch);

        if ($error) {
            throw new Exception("cURL Error: " . $error);
        }

        $result = json_decode($response, true);

        if ($httpCode >= 400) {
            $errorMessage = isset($result['detail']) ? $result['detail'] : 'Request failed';
            throw new Exception($errorMessage, $httpCode);
        }

        return $result;
    }

    /**
     * Upload a file
     */
    public function uploadFile($endpoint, $fileFieldName, $filePath) {
        $url = $this->baseUrl . $endpoint;

        if (!file_exists($filePath)) {
            throw new Exception("File not found: " . $filePath);
        }

        $cfile = new CURLFile($filePath, mime_content_type($filePath), basename($filePath));
        $data = [$fileFieldName => $cfile];

        return $this->request('POST', $url, $data, true);
    }
}

/**
 * Helper function to get Orchestrator API client
 */
function getOrchestratorApi() {
    return new ApiClient(API_URL);
}

/**
 * Helper function to get Sentiment API client
 */
function getSentimentApi() {
    return new ApiClient(SENTIMENT_API_URL);
}
