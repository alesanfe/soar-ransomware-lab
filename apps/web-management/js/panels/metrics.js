// Dashboard panels: host metrics, services status, KPIs.

import {API_BASE} from '../state.js';
import {getAuthHeaders} from '../util.js';

export async function updateMetrics() {
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

export async function updateServicesStatus() {
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

export async function loadKPIs() {
    try {
        const response = await fetch(`${API_BASE}/analytics/kpis`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) return;
        const data = await response.json();

        // Aggregated KPIs carry the alert-side numbers (Elasticsearch-backed);
        // comprehensive KPIs carry MTTR + last-run coverage.
        let agg = {};
        try {
            const aggResp = await fetch(`${API_BASE}/analytics/kpis/aggregated`, {
                headers: getAuthHeaders()
            });
            if (aggResp.ok) agg = await aggResp.json();
        } catch (e) { /* aggregated endpoint optional */ }

        // Verdict counts from the live decision feed.
        let verdicts = {};
        try {
            const decResp = await fetch(`${API_BASE}/soar/shuffle/decisions`, {
                headers: getAuthHeaders()
            });
            if (decResp.ok) {
                const dec = await decResp.json();
                (dec.executions || []).forEach((ex) => {
                    const v = (ex.decision && ex.decision.verdict) || 'unknown';
                    verdicts[v] = (verdicts[v] || 0) + 1;
                });
            }
        } catch (e) { /* decisions endpoint optional */ }

        const mttrStats = agg.mttr_statistics || data.mttr || {};
        const perf = data.performance || {};
        const totalAlerts = agg.total_alerts;
        const executed = mttrStats.total_executions || 0;
        const detectionRate = totalAlerts
            ? Math.min(100, (executed / totalAlerts) * 100)
            : undefined;

        const mttrMinutes = mttrStats.mttr_minutes !== undefined
            ? mttrStats.mttr_minutes
            : (mttrStats.mean !== undefined ? mttrStats.mean / 60 : undefined);

        const mapping = {
            'kpiMttr': mttrMinutes !== undefined ? `${Number(mttrMinutes).toFixed(1)} min` : '—',
            'kpiTotalAlerts': totalAlerts !== undefined ? totalAlerts : '—',
            'kpiMalicious': verdicts.malicious !== undefined ? verdicts.malicious
                : (Object.keys(verdicts).length ? 0 : '—'),
            'kpiBenign': verdicts.benign !== undefined ? verdicts.benign
                : (Object.keys(verdicts).length ? 0 : '—'),
            'kpiDetectionRate': detectionRate !== undefined
                ? `${detectionRate.toFixed(1)}%` : '—',
        };

        Object.entries(mapping).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        });

        // Hydrate the coverage card from the last recorded run until the
        // operator triggers a fresh /tests/run.
        const coverageEl = document.getElementById('coveragePercent');
        if (coverageEl && coverageEl.textContent === '—' &&
                perf.average_coverage !== undefined && perf.average_coverage > 0) {
            coverageEl.textContent = `${perf.average_coverage}%`;
        }
    } catch (error) {
        console.error('Failed to load KPIs:', error);
    }
}
