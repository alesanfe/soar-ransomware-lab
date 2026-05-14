/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  tutorialSidebar: [
    'README',
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture',
        'architecture/architecture',
      ],
    },
    {
      type: 'category',
      label: 'Docker',
      items: [
        'docker-ports-analysis-report',
        'docker-testing-explanation',
        'docker-testing-strategy',
      ],
    },
    {
      type: 'category',
      label: 'Project',
      items: [
        'objectives',
        'plan',
        'project-complete-status-report',
        'scope',
      ],
    },
    {
      type: 'category',
      label: 'Security',
      items: [
        'security',
        'security/security',
      ],
    },
    {
      type: 'category',
      label: 'Testing',
      items: [
        'testing/docker_tests',
        'testing/tests',
        'testing/unit_test_mapping',
      ],
    },
    {
      type: 'category',
      label: 'TFM',
      items: [
        'tfm/tfm',
        'tfm/introduccion',
        'tfm/objetivos_y_metodologia',
        'tfm/estado_del_arte',
        'tfm/desarrollo_especifico',
        'tfm/conclusiones_y_trabajo_futuro',
        'tfm/referencias_bibliograficas',
        'tfm/anexo_a',
        'tfm/agradecimientos',
        'tfm/declaracion_originalidad',
        'tfm/resumen_ejecutivo',
        'tfm/indice_general',
        'tfm/lista_figuras_tablas',
        'tfm/lista_abreviaturas',
        'tfm/tablas_comparativas',
        'tfm/visualizaciones_datos',
      ],
    },
    {
      type: 'category',
      label: 'User Guide',
      items: [
        'user_guide',
        'user-guide/user_guide',
      ],
    },
  ],
};

module.exports = sidebars;
