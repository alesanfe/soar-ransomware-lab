// Backup create/list/restore panel.

import {API_BASE} from '../state.js';
import {getAuthHeaders, showLoading} from '../util.js';

export async function createBackup() {
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

export async function listBackups() {
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

export async function restoreBackup() {
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
