// Execution detail drawer (WEB-DETAIL-001).

import {API_BASE, state} from './state.js';
import {escapeHtml, fmtTs, getAuthHeaders, showMessage} from './util.js';

export async function openExecModal(execId) {
    if (!execId) return;
    state.currentExecId = execId;
    const modal = document.getElementById('execModal');
    const body = document.getElementById('execModalBody');
    const title = document.getElementById('execModalTitle');
    const link = document.getElementById('execShuffleLink');
    title.textContent = `Execution ${execId.slice(0, 8)}…`;
    link.href = `http://localhost:8081/workflows?execution_id=${encodeURIComponent(execId)}`;
    body.innerHTML = '<span class="muted">Loading…</span>';
    modal.style.display = 'flex';
    history.replaceState(null, '', `#exec=${encodeURIComponent(execId)}`);

    try {
        const response = await fetch(
            `${API_BASE}/soar/shuffle/executions/${encodeURIComponent(execId)}/decision`,
            {headers: getAuthHeaders()}
        );
        if (!response.ok) {
            body.innerHTML = `<span class="muted decision-error">Detail unavailable (HTTP ${response.status})</span>`;
            return;
        }
        const rec = await response.json();
        body.innerHTML = renderExecDetail(rec);
    } catch (e) {
        body.innerHTML = '<span class="muted decision-error">Detail unavailable (network)</span>';
    }
}

function renderExecDetail(rec) {
    const d = rec.decision || {};
    const kv = (k, v) => `<div class="exec-kv"><span>${escapeHtml(k)}</span><span>${escapeHtml(String(v ?? '—'))}</span></div>`;
    const factors = Array.isArray(d.factors) && d.factors.length
        ? `<ul class="exec-factors">${d.factors.map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>`
        : '<span class="muted">—</span>';
    const result = rec.result ? escapeHtml(JSON.stringify(rec.result, null, 2)) : null;
    return `
        ${kv('execution_id', rec.execution_id)}
        ${kv('workflow', rec.workflow_name || rec.workflow_id)}
        ${kv('status', rec.status)}
        ${kv('started', fmtTs(rec.started_at))}
        ${kv('completed', fmtTs(rec.completed_at))}
        ${kv('verdict', d.verdict)}
        ${kv('score', d.score)}
        ${kv('decision', d.decision)}
        <h4>Factors</h4>${factors}
        ${result ? `<h4>Result</h4><pre class="exec-result">${result}</pre>` : ''}`;
}

export function closeExecModal() {
    const modal = document.getElementById('execModal');
    if (modal) modal.style.display = 'none';
    state.currentExecId = null;
    history.replaceState(null, '', window.location.pathname);
}

export function copyExecId() {
    if (!state.currentExecId) return;
    navigator.clipboard.writeText(state.currentExecId).then(
        () => showMessage('Execution ID copied', 'success'),
        () => showMessage('Copy failed', 'error')
    );
}
