// Shared mutable state + API base.
// ES module bindings are read-only for importers — export a mutable
// state object instead of module-level `let` variables.

export const state = {
    isAuthenticated: false,
    ws: null,
    logsInterval: null,
    metricsInterval: null,
    servicesInterval: null,
    kpiInterval: null,
    pipelineInterval: null,
    currentExecId: null,
};

// API base URL — rutas relativas para funcionar detrás de Nginx
export const API_BASE = '/api';
