// SOAR Lab Management UI JavaScript

// Global variables
let isAuthenticated = false;
let ws = null;
let logsInterval = null;
let metricsInterval = null;
let servicesInterval = null;

// API base URL — rutas relativas para funcionar detrás de Nginx
const API_BASE = '/api';

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    initializeApp();
});

function initializeApp() {
    // Load saved theme
    loadTheme();

    // Check authentication status
    checkAuthStatus();

    // Setup event listeners
    setupEventListeners();

    // Start periodic updates if authenticated
    if (isAuthenticated) {
        startPeriodicUpdates();
    }
}

function setupEventListeners() {
    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Authentication
    document.getElementById('loginBtn').addEventListener('click', login);
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // Enter key for login
    document.getElementById('password').addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            login();
        }
    });
}

// Theme toggle function
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update toggle button icon
    const toggleButton = document.getElementById('themeToggle');
    toggleButton.textContent = newTheme === 'light' ? '☀️' : '🌙';
}

// Load saved theme on page load
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const toggleButton = document.getElementById('themeToggle');
    if (toggleButton) {
        toggleButton.textContent = savedTheme === 'light' ? '☀️' : '🌙';
    }
}

// Authentication functions
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showMessage('Please enter username and password', 'error');
        return;
    }

    try {
        showLoading(true);
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({username, password})
        });

        if (response.ok) {
            const data = await response.json();
            isAuthenticated = true;
            localStorage.setItem('auth_token', data.token);
            showMainContent();
            startPeriodicUpdates();
            showMessage('Login successful', 'success');
        } else {
            throw new Error('Invalid credentials');
        }
    } catch (error) {
        showMessage('Login failed: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function logout() {
    isAuthenticated = false;
    localStorage.removeItem('auth_token');
    hideMainContent();
    stopPeriodicUpdates();
    showMessage('Logged out successfully', 'success');
}

function checkAuthStatus() {
    const token = localStorage.getItem('auth_token');
    if (token) {
        // Verify token with server - use POST method
        fetch(`${API_BASE}/auth/verify`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => {
            if (response.ok) {
                isAuthenticated = true;
                showMainContent();
                startPeriodicUpdates();
            } else {
                localStorage.removeItem('auth_token');
            }
        }).catch(() => {
            localStorage.removeItem('auth_token');
        });
    }
}

function showMainContent() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'inline-block';
    document.getElementById('mainContent').style.display = 'block';
}

function hideMainContent() {
    document.getElementById('authSection').style.display = 'flex';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('mainContent').style.display = 'none';
}

// Periodic updates
function startPeriodicUpdates() {
    // Update metrics every 5 seconds
    metricsInterval = setInterval(updateMetrics, 5000);

    // Update services status every 10 seconds
    servicesInterval = setInterval(updateServicesStatus, 10000);

    // Update KPIs every 30 seconds
    setInterval(loadKPIs, 30000);

    // Initial updates
    updateMetrics();
    updateServicesStatus();
    loadKPIs();
    updateTestCoverage();
}

function stopPeriodicUpdates() {
    if (metricsInterval) clearInterval(metricsInterval);
    if (servicesInterval) clearInterval(servicesInterval);
    if (logsInterval) clearInterval(logsInterval);

    if (ws) {
        ws.close();
        ws = null;
    }
}

// Metrics functions
async function updateMetrics() {
    try {
        const response = await fetch(`${API_BASE}/analytics/metrics`, {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();

            // Update CPU usage
            document.getElementById('cpuUsage').style.width = `${data.cpu}%`;
            document.getElementById('cpuPercent').textContent = `${data.cpu}%`;

            // Update RAM usage
            document.getElementById('ramUsage').style.width = `${data.memory}%`;
            document.getElementById('ramPercent').textContent = `${data.memory}%`;

            // Update Disk usage
            document.getElementById('diskUsage').style.width = `${data.disk}%`;
            document.getElementById('diskPercent').textContent = `${data.disk}%`;
        }
    } catch (error) {
        console.error('Failed to update metrics:', error);
    }
}

// Services status functions
async function updateServicesStatus() {
    try {
        const response = await fetch(`${API_BASE}/services/status`, {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();

            // The API now returns services in a "services" field
            const services = data.services || {};

            // Update service status indicators
            Object.keys(services).forEach(service => {
                const statusElement = document.querySelector(`[data-service="${service}"]`);
                if (statusElement) {
                    statusElement.className = `status ${services[service] ? 'online' : 'offline'}`;
                }
            });

            // Update overall services status
            const onlineCount = Object.values(services).filter(status => status).length;
            const offlineCount = Object.values(services).filter(status => !status).length;
            const totalCount = Object.keys(services).length;
            const servicesStatus = document.getElementById('servicesStatus');

            // Update summary
            document.getElementById('totalServices').textContent = totalCount;
            document.getElementById('onlineServices').textContent = onlineCount;
            document.getElementById('offlineServices').textContent = offlineCount;
            document.getElementById('servicesSummary').style.display = 'flex';

            if (onlineCount === totalCount) {
                servicesStatus.innerHTML = '<span class="status-dot online"></span><span>All services online</span>';
            } else {
                servicesStatus.innerHTML = `<span class="status-dot offline"></span><span>${onlineCount}/${totalCount} services online</span>`;
            }
        }
    } catch (error) {
        console.error('Failed to update services status:', error);
    }
}

// KPI functions
async function loadKPIs() {
    try {
        const response = await fetch(`${API_BASE}/analytics/kpis`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) return;
        const data = await response.json();

        // Map actual API response fields to UI elements
        // The API returns comprehensive KPIs with nested structure
        const mttr = data.mttr_metrics || {};
        const perf = data.performance_kpis || {};
        const health = data.health_score || {};

        const mapping = {
            'kpiMttr': mttr.mean !== undefined ? `${Number(mttr.mean).toFixed(1)} min` : '—',
            'kpiTotalAlerts': perf.total_alerts !== undefined ? perf.total_alerts : '—',
            'kpiMalicious': perf.malicious !== undefined ? perf.malicious : '—',
            'kpiBenign': perf.benign !== undefined ? perf.benign : '—',
            'kpiDetectionRate': perf.detection_rate !== undefined ? `${perf.detection_rate}%` : '—',
        };

        Object.entries(mapping).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        });
    } catch (error) {
        console.error('Failed to load KPIs:', error);
    }
}

// Test coverage functions
async function updateTestCoverage() {
    // Coverage is not available as a separate endpoint
    // It's returned when running tests via /tests/run
    // This function is kept for compatibility but does nothing
    console.log('Coverage data should be obtained from /tests/run response');
}

// Test execution functions
async function runTests(category) {
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/tests/run`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({category})
        });

        if (response.ok) {
            const data = await response.json();
            displayTestResults(data);
        } else {
            throw new Error('Failed to run tests');
        }
    } catch (error) {
        showMessage('Failed to run tests: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function displayTestResults(results) {
    const resultsSection = document.getElementById('testResults');
    resultsSection.style.display = 'block';

    // Update summary
    document.getElementById('passedCount').textContent = results.passed;
    document.getElementById('failedCount').textContent = results.failed;
    document.getElementById('skippedCount').textContent = results.skipped;
    document.getElementById('testCoverage').textContent = `${results.coverage}%`;

    // Update detailed output
    const outputElement = document.getElementById('resultsOutput');
    outputElement.textContent = results.output || 'No output available';

    // Update dashboard coverage card with last run data
    const coverageEl = document.getElementById('coveragePercent');
    if (coverageEl) coverageEl.textContent = `${results.coverage}%`;
    const lastRunEl = document.getElementById('lastRunTime');
    if (lastRunEl) lastRunEl.textContent = new Date().toLocaleTimeString();
    const categoryEl = document.getElementById('lastTestCategory');
    if (categoryEl) categoryEl.textContent = results.category || '—';
    const durationEl = document.getElementById('lastTestDuration');
    if (durationEl) durationEl.textContent = results.duration ? `${results.duration.toFixed(1)}s` : '—';

    // Scroll to results
    resultsSection.scrollIntoView({behavior: 'smooth'});
}

// Logs functions
function toggleLogs() {
    const toggleText = document.getElementById('logsToggleText');

    if (ws) {
        // Stop logs
        ws.close();
        ws = null;
        if (logsInterval) clearInterval(logsInterval);
        toggleText.textContent = 'Start Live Logs';
    } else {
        // Start logs
        startWebSocketLogs();
        toggleText.textContent = 'Stop Live Logs';
    }
}

function startWebSocketLogs() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs`;

    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
        console.log('WebSocket connection established');
    };

    ws.onmessage = function (event) {
        const logData = JSON.parse(event.data);
        appendLog(logData);
    };

    ws.onerror = function (error) {
        console.error('WebSocket error:', error);
        showMessage('Failed to connect to logs stream', 'error');
    };

    ws.onclose = function () {
        console.log('WebSocket connection closed');
        ws = null;
        document.getElementById('logsToggleText').textContent = 'Start Live Logs';
    };
}

function appendLog(logData) {
    const logsOutput = document.getElementById('logsOutput');
    const logLevel = document.getElementById('logLevel').value;

    // Filter logs by level
    if (logLevel !== 'all') {
        if (logLevel === 'error' && logData.level !== 'ERROR') return;
        if (logLevel === 'warning' && !['ERROR', 'WARNING'].includes(logData.level)) return;
        if (logLevel === 'info' && !['ERROR', 'WARNING', 'INFO'].includes(logData.level)) return;
    }

    const logElement = document.createElement('div');
    logElement.className = `log-${logData.level.toLowerCase()}`;
    logElement.textContent = `[${logData.timestamp}] ${logData.level}: ${logData.message}`;

    logsOutput.appendChild(logElement);

    // Auto-scroll to bottom
    logsOutput.scrollTop = logsOutput.scrollHeight;

    // Limit log history
    while (logsOutput.children.length > 1000) {
        logsOutput.removeChild(logsOutput.firstChild);
    }
}

function clearLogs() {
    document.getElementById('logsOutput').innerHTML = '';
}

// Backup functions
async function createBackup() {
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/backup/create`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();
            showBackupStatus(`Backup created successfully: ${data.backup_name || data.filename || 'OK'}`, 'success');
            listBackups();
        } else {
            throw new Error('Failed to create backup');
        }
    } catch (error) {
        showBackupStatus('Failed to create backup: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

async function listBackups() {
    try {
        const response = await fetch(`${API_BASE}/backup/list`, {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            const data = await response.json();
            const backupList = document.getElementById('backupList');

            // Clear existing options
            backupList.innerHTML = '<option value="">Select backup...</option>';

            // Add backup options — API returns a plain string array of names
            data.backups.forEach(backup => {
                const option = document.createElement('option');
                const name = typeof backup === 'object' ? backup.name : backup;
                option.value = name;
                option.textContent = typeof backup === 'object'
                    ? `${backup.name} (${backup.size || ''}, ${backup.date || ''})`
                    : name;
                backupList.appendChild(option);
            });
        }
    } catch (error) {
        showBackupStatus('Failed to list backups: ' + error.message, 'error');
    }
}

async function restoreBackup() {
    const backupName = document.getElementById('backupList').value;

    if (!backupName) {
        showBackupStatus('Please select a backup to restore', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to restore backup "${backupName}"? This will replace current data.`)) {
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/backup/restore`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({backup_name: backupName})
        });

        if (response.ok) {
            const data = await response.json();
            showBackupStatus(`Backup restored successfully: ${data.message}`, 'success');
        } else {
            throw new Error('Failed to restore backup');
        }
    } catch (error) {
        showBackupStatus('Failed to restore backup: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function showBackupStatus(message, type) {
    const statusElement = document.getElementById('backupStatus');
    statusElement.textContent = message;
    statusElement.className = `backup-status text-${type}`;

    // Clear status after 5 seconds
    setTimeout(() => {
        statusElement.textContent = '';
        statusElement.className = 'backup-status';
    }, 5000);
}

// Utility functions
function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    return token ? {'Authorization': `Bearer ${token}`} : {};
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showMessage(message, type) {
    // Create a temporary message element
    const messageElement = document.createElement('div');
    messageElement.className = `text-${type}`;
    messageElement.textContent = message;
    messageElement.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem;
        background: white;
        border-radius: 0.375rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1001;
        max-width: 300px;
    `;

    document.body.appendChild(messageElement);

    // Remove after 3 seconds
    setTimeout(() => {
        document.body.removeChild(messageElement);
    }, 3000);
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        stopPeriodicUpdates();
    } else if (isAuthenticated) {
        startPeriodicUpdates();
    }
});

// Handle connection errors
window.addEventListener('online', function () {
    if (isAuthenticated) {
        startPeriodicUpdates();
    }
});

window.addEventListener('offline', function () {
    stopPeriodicUpdates();
    showMessage('Connection lost', 'error');
});
