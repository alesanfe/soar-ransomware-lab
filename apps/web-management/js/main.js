// SOAR Lab Management UI — entry point (ES module, CSP script-src 'self').

import {checkAuthStatus, login, logout} from './auth.js';
import {closeExecModal, copyExecId} from './exec.js';
import {startPeriodicUpdates, stopPeriodicUpdates} from './lifecycle.js';
import {createBackup, listBackups, restoreBackup} from './panels/backups.js';
import {clearLogs, toggleLogs} from './panels/logs.js';
import {loadDecisions} from './panels/pipeline.js';
import {runTests} from './panels/tests.js';
import {routeHash} from './router.js';
import {state} from './state.js';
import {toggleTheme, loadTheme} from './theme.js';
import {showMessage} from './util.js';

function initializeApp() {
    // Load saved theme
    loadTheme();

    // Check authentication status
    checkAuthStatus();

    // Setup event listeners
    setupEventListeners();

    // Start periodic updates if authenticated
    if (state.isAuthenticated) {
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

    // Delegated actions — no inline onclick handlers (CSP script-src 'self')
    const actions = {
        loadDecisions,
        toggleLogs,
        clearLogs,
        createBackup,
        listBackups,
        restoreBackup,
        closeExec: closeExecModal,
        copyExecId: copyExecId,
    };
    document.addEventListener('click', function (e) {
        const el = e.target.closest('[data-action]');
        if (!el) return;
        const action = actions[el.dataset.action];
        if (el.dataset.action === 'runTests') {
            runTests(el.dataset.category);
        } else if (action) {
            action();
        }
    });

    // Deep-link routing (WEB-DEEPLINK-001)
    window.addEventListener('hashchange', routeHash);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    initializeApp();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        stopPeriodicUpdates();
    } else if (state.isAuthenticated) {
        startPeriodicUpdates();
    }
});

// Handle connection errors
window.addEventListener('online', function () {
    if (state.isAuthenticated) {
        startPeriodicUpdates();
    }
});

window.addEventListener('offline', function () {
    stopPeriodicUpdates();
    showMessage('Connection lost', 'error');
});
