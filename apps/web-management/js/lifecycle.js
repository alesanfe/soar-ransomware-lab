// Periodic refresh lifecycle (WEB-LIFECYCLE-001: interval handles are
// cleared before re-arming so repeated starts never stack timers).

import {loadKPIs, updateMetrics, updateServicesStatus} from './panels/metrics.js';
import {updatePipeline} from './panels/pipeline.js';
import {updateTestCoverage} from './panels/tests.js';
import {routeHash} from './router.js';
import {state} from './state.js';

export function startPeriodicUpdates() {
    // Update metrics every 5 seconds
    state.metricsInterval = setInterval(updateMetrics, 5000);

    // Update services status every 10 seconds
    state.servicesInterval = setInterval(updateServicesStatus, 10000);

    // Update KPIs every 30 seconds — keep the handle so repeated
    // startPeriodicUpdates() calls never stack intervals (WEB-LIFECYCLE-001)
    if (state.kpiInterval !== null) {
        clearInterval(state.kpiInterval);
    }
    state.kpiInterval = setInterval(loadKPIs, 30000);

    // Update SOAR pipeline (queue + decisions) every 15 seconds
    if (state.pipelineInterval !== null) {
        clearInterval(state.pipelineInterval);
    }
    state.pipelineInterval = setInterval(updatePipeline, 15000);

    // Initial updates
    updateMetrics();
    updateServicesStatus();
    loadKPIs();
    updatePipeline();
    updateTestCoverage();
    routeHash();
}

export function stopPeriodicUpdates() {
    if (state.metricsInterval) { clearInterval(state.metricsInterval); state.metricsInterval = null; }
    if (state.servicesInterval) { clearInterval(state.servicesInterval); state.servicesInterval = null; }
    if (state.logsInterval) { clearInterval(state.logsInterval); state.logsInterval = null; }
    if (state.kpiInterval) { clearInterval(state.kpiInterval); state.kpiInterval = null; }
    if (state.pipelineInterval) { clearInterval(state.pipelineInterval); state.pipelineInterval = null; }

    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
}
