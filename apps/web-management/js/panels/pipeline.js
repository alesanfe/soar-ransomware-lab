// SOAR pipeline panels: admission queue + decisions feed.

import {openExecModal} from '../exec.js';
import {API_BASE} from '../state.js';
import {escapeHtml, fmtTs, getAuthHeaders} from '../util.js';

export function updatePipeline() {
    updateQueue();
    loadDecisions();
}

async function updateQueue() {
    try {
        const response = await fetch(`${API_BASE}/v1/queue/metrics`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) return;
        const data = await response.json();

        const mapping = {
            'queueDepth': data.queue_depth,
            'queueStreamLen': data.stream_length,
            'queueLag': data.consumer_lag,
            'queuePending': data.pending,
            'queueDlq': data.dlq_size,
        };
        Object.entries(mapping).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value !== null && value !== undefined ? value : '—';
        });
        const dlqEl = document.getElementById('queueDlq');
        if (dlqEl) dlqEl.classList.toggle('dlq-alert', (data.dlq_size || 0) > 0);
    } catch (error) {
        console.error('Failed to load queue metrics:', error);
    }
}

export async function loadDecisions() {
    const list = document.getElementById('decisionsList');
    if (!list) return;
    try {
        const response = await fetch(`${API_BASE}/soar/shuffle/decisions?limit=10`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            list.innerHTML = `<span class="muted decision-error">Decisions unavailable (HTTP ${response.status})</span>`;
            return;
        }
        const data = await response.json();
        renderDecisions(list, data.executions || []);
    } catch (error) {
        console.error('Failed to load decisions:', error);
        list.innerHTML = '<span class="muted decision-error">Decisions unavailable (network)</span>';
    }
}

function renderDecisions(list, executions) {
    if (!executions.length) {
        list.innerHTML = '<span class="muted">No executions yet</span>';
        return;
    }
    list.innerHTML = executions.map(exec => {
        const d = exec.decision || {};
        const verdict = d.verdict || 'pending';
        const score = d.score !== undefined ? d.score : '—';
        const action = d.decision || '—';
        const factors = Array.isArray(d.factors) && d.factors.length
            ? `<div class="decision-factors">${escapeHtml(d.factors.join(' · '))}</div>`
            : '';
        const id8 = (exec.execution_id || '').slice(0, 8);
        const status = (exec.status || 'unknown').toLowerCase();
        const ts = fmtTs(exec.started_at || exec.completed_at);
        return `<div class="decision-row decision-link" data-exec="${escapeHtml(exec.execution_id || '')}" title="${escapeHtml(exec.execution_id || '')}" role="button" tabindex="0">
            <span class="decision-id" title="${escapeHtml(exec.workflow_name || '')}">${escapeHtml(id8)}</span>
            <span class="decision-ts">${escapeHtml(ts)}</span>
            <span class="decision-status status-${escapeHtml(status)}">${escapeHtml(status)}</span>
            <span class="decision-score">${escapeHtml(String(score))}</span>
            <span class="decision-verdict verdict-${escapeHtml(verdict)}">${escapeHtml(verdict)}</span>
            <span class="decision-action">${escapeHtml(action)}</span>
            ${factors}
        </div>`;
    }).join('');

    // Rows open the execution detail drawer + hash deep-link
    list.querySelectorAll('.decision-link').forEach(row => {
        row.addEventListener('click', () => openExecModal(row.dataset.exec));
        row.addEventListener('keypress', e => {
            if (e.key === 'Enter') openExecModal(row.dataset.exec);
        });
    });
}
