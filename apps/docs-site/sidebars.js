/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'README',
    {
        type: 'category',
        label: 'Getting Started',
        items: [
            'getting_started/overview',
            'getting_started/installation_guide',
            'getting_started/user_guide',
        ],
    },
      {
      type: 'category',
      label: 'Architecture',
      items: [
          'architecture/overview',
          'architecture/docker_architecture',
          'architecture/security',
      ],
    },
    {
      type: 'category',
        label: 'Operations',
      items: [
          'operations/configuration_manual',
          'operations/troubleshooting',
          {
              type: 'category',
              label: 'Playbooks',
              items: [
                  'operations/playbooks/ransomware_playbook_e2e',
              ],
          },
      ],
    },
    {
      type: 'category',
        label: 'Integrations',
      items: [
          'integrations/api_contracts',
      ],
    },
    {
      type: 'category',
      label: 'Testing',
      items: [
          'testing/README',
          'testing/test_suite',
          'testing/docker_testing_strategy',
      ],
    },
    {
      type: 'category',
        label: 'Project',
      items: [
          'project/objectives',
          'project/plan',
          'project/scope',
          'project/risks',
      ],
    },
    {
      type: 'category',
        label: 'Thesis',
      items: [
          'thesis/executive_summary',
          'thesis/introduction',
          'thesis/state_of_the_art',
          'thesis/objectives_and_methodology',
          'thesis/specific_development',
          'thesis/conclusions_and_future_work',
          'thesis/bibliographic_references',
          'thesis/appendix_a',
          'thesis/acknowledgments',
          'thesis/abbreviations_list',
          'thesis/figures_tables_list',
          'thesis/originality_declaration',
          'thesis/comparative_tables',
          'thesis/data_visualizations',
          'thesis/tfm',
          'thesis/table_of_contents',
      ],
    },
  ],
};

module.exports = sidebars;
