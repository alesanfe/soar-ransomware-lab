// Live log streaming over WebSocket (WEB-AUTH-001/002/007).

import {API_BASE, state} from '../state.js';
import {getAuthHeaders, showMessage} from '../util.js';

export function toggleLogs() {
    const toggleText = document.getElementById('logsToggleText');

    if (state.ws) {
        // Stop logs
        state.ws.close();
        state.ws = null;
        if (state.logsInterval) clearInterval(state.logsInterval);
        toggleText.textContent = 'Start Live Logs';
    } else {
        // Start logs
        startWebSocketLogs();
        toggleText.textContent = 'Stop Live Logs';
    }
}

async function startWebSocketLogs() {
    // WEB-AUTH-001: obtain a single-use, short-lived ticket first.
    // The primary JWT never goes on the WS URL (WEB-AUTH-007).
    let ticket;
    try {
        const resp = await fetch(`${API_BASE}/auth/ws-ticket`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
        if (resp.status === 401) {
            showMessage('Session expired — please log in again', 'error');
            return;
        }
        if (resp.status === 403) {
            showMessage('No permission to stream logs', 'error');
            return;
        }
        if (!resp.ok) {
            showMessage('Could not start log stream', 'error');
            return;
        }
        const data = await resp.json();
        ticket = data.ticket;
    } catch (e) {
        showMessage('Network error starting log stream', 'error');
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/logs?ticket=${encodeURIComponent(ticket)}`;

    state.ws = new WebSocket(wsUrl);

    state.ws.onopen = function () {
        console.log('WebSocket connection established');
    };

    state.ws.onmessage = function (event) {
        const logData = JSON.parse(event.data);
        appendLog(logData);
    };

    state.ws.onerror = function (error) {
        console.error('WebSocket error:', error);
        showMessage('Failed to connect to logs stream', 'error');
    };

    state.ws.onclose = function (event) {
        // WEB-AUTH-002: distinguish auth/authorization/limit/internal closes.
        const reasons = {
            4401: 'Log stream rejected: authentication required',
            4403: 'Log stream rejected: insufficient permissions',
            4408: 'Log stream ticket expired — retry',
            4429: 'Too many log streams open',
            4500: 'Log stream internal error',
        };
        if (reasons[event.code]) showMessage(reasons[event.code], 'error');
        console.log('WebSocket connection closed');
        state.ws = null;
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

export function clearLogs() {
    document.getElementById('logsOutput').innerHTML = '';
}
