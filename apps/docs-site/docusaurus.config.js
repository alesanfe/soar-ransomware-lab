const {themes} = require('prism-react-renderer');
const lightCodeTheme = themes.github;
const darkCodeTheme = themes.dracula;

/** @type {import('@docusaurus/types').Config} */
const config = {
    title: 'SOAR Ransomware Lab',
    tagline: 'Security Orchestration, Automation and Response Laboratory',
    favicon: 'img/favicon.ico',

    // GitHub Pages deployment
    url: 'https://alesanfe.github.io',
    baseUrl: '/soar-ransomware-lab/',
    organizationName: 'alesanfe',
    projectName: 'soar-ransomware-lab',
    trailingSlash: false,

    onBrokenLinks: 'warn',
    onBrokenMarkdownLinks: 'warn',

    i18n: {
        defaultLocale: 'en',
        locales: ['en'],
    },

    presets: [
        [
            'classic',
            /** @type {import('@docusaurus/preset-classic').Options} */
            ({
                docs: {
                    sidebarPath: require.resolve('./sidebars.js'),
                    sidebarCollapsed: false,
                    editUrl: 'https://github.com/alesanfe/soar-ransomware-lab/tree/main/docs/',
                },
                blog: false,
                theme: {
                    customCss: require.resolve('./src/css/custom.css'),
                },
            }),
        ],
    ],
    markdown: {
        format: 'md',
    },

    themeConfig:
        /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
        ({
            navbar: {
                title: 'SOAR Lab',
                logo: {
                    alt: 'SOAR Lab Logo',
                    src: 'img/logo.svg',
                },
                items: [
                    {
                        type: 'docSidebar',
                        sidebarId: 'tutorialSidebar',
                        position: 'left',
                        label: 'Documentation',
                    },
                    {
                        type: 'docSidebar',
                        sidebarId: 'reportsSidebar',
                        position: 'left',
                        label: 'Reports',
                    },
                    {
                        href: 'https://github.com/alesanfe/soar-ransomware-lab',
                        label: 'GitHub',
                        position: 'right',
                    },
                ],
            },
            footer: {
                style: 'dark',
                links: [
                    {
                        title: 'Documentation',
                        items: [
                            {
                                label: 'Getting Started',
                                to: '/docs/intro',
                            },
                            {
                                label: 'Architecture',
                                to: '/docs/architecture/overview',
                            },
                        ],
                    },
                    {
                        title: 'Reports',
                        items: [
                            {
                                label: 'Quality',
                                to: '/docs/reports/quality/quality-summary',
                            },
                            {
                                label: 'Test Review',
                                to: '/docs/reports/test-review/test_review_report',
                            },
                            {
                                label: 'Holistic Review',
                                to: '/docs/reports/holistic/holistic_review_report',
                            },
                        ],
                    },
                    {
                        title: 'Community',
                        items: [
                            {
                                label: 'GitHub',
                                href: 'https://github.com/alesanfe/soar-ransomware-lab',
                            },
                        ],
                    },
                ],
                copyright: `Copyright © ${new Date().getFullYear()} SOAR Ransomware Lab. Built with Docusaurus.`,
            },
            prism: {
                theme: lightCodeTheme,
                darkTheme: darkCodeTheme,
            },
        }),
};

module.exports = config;
