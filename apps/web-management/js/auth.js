// Login/logout/session-verify + auth-gated content visibility.

import {startPeriodicUpdates, stopPeriodicUpdates} from './lifecycle.js';
import {API_BASE, state} from './state.js';
import {showLoading, showMessage} from './util.js';

export async function login() {
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
            state.isAuthenticated = true;
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

export function logout() {
    state.isAuthenticated = false;
    localStorage.removeItem('auth_token');
    hideMainContent();
    stopPeriodicUpdates();
    showMessage('Logged out successfully', 'success');
}

export function checkAuthStatus() {
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
                state.isAuthenticated = true;
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

export function showMainContent() {
    document.getElementById('authSection').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'inline-block';
    document.getElementById('mainContent').style.display = 'block';
}

export function hideMainContent() {
    document.getElementById('authSection').style.display = 'flex';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('mainContent').style.display = 'none';
}
