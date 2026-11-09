// Test runner panel + coverage card.

import {API_BASE} from '../state.js';
import {getAuthHeaders, showLoading, showMessage} from '../util.js';

export function updateTestCoverage() {
    // Coverage is not available as a separate endpoint
    // It's returned when running tests via /tests/run
    // This function is kept for compatibility but does nothing
    console.log('Coverage data should be obtained from /tests/run response');
}

export async function runTests(category) {
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
