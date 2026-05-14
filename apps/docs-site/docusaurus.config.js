const { themes } = require('prism-react-renderer');
const lightCodeTheme = themes.github;
const darkCodeTheme = themes.dracula;

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'SOAR Ransomware Lab',
  tagline: 'Security Orchestration, Automation and Response Laboratory',
  favicon: 'img/favicon.ico',
  url: 'http://localhost:3000',
  baseUrl: '/',
  organizationName: 'soar-lab',
  projectName: 'soar-ransomware-lab',

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
          editUrl: 'https://github.com/soar-lab/soar-ransomware-lab/tree/main/docs/',
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
            to: '/api',
            label: 'API',
            position: 'left'
          },
          {
            href: 'http://localhost:8080',
            label: 'Management UI',
            position: 'right'
          },
          {
            href: 'https://github.com/soar-lab/soar-ransomware-lab',
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
                to: '/docs/architecture',
              },
              {
                label: 'API Reference',
                to: '/api',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/soar-lab/soar-ransomware-lab',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'Management UI',
                href: 'http://localhost:8080',
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
