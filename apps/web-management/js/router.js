// Hash deep-link routing (WEB-DEEPLINK-001).

import {openExecModal} from './exec.js';

export const SECTION_IDS = [
    'sec-overview', 'sec-pipeline', 'sec-services', 'sec-tests', 'sec-logs', 'sec-backups',
];

export function routeHash() {
    const hash = decodeURIComponent(window.location.hash.slice(1));
    if (hash.startsWith('exec=')) {
        openExecModal(hash.slice(5));
        return;
    }
    if (SECTION_IDS.includes(hash)) {
        document.getElementById(hash)?.scrollIntoView({behavior: 'smooth'});
        highlightNav(hash);
    }
}

function highlightNav(activeId) {
    document.querySelectorAll('#sectionNav a').forEach(a => {
        a.classList.toggle('active', a.dataset.nav === activeId);
    });
}
