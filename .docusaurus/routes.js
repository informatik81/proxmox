import React from 'react';
import ComponentCreator from '@docusaurus/ComponentCreator';

export default [
  {
    path: '/__docusaurus/debug',
    component: ComponentCreator('/__docusaurus/debug', '5ff'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/config',
    component: ComponentCreator('/__docusaurus/debug/config', '5ba'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/content',
    component: ComponentCreator('/__docusaurus/debug/content', 'a2b'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/globalData',
    component: ComponentCreator('/__docusaurus/debug/globalData', 'c3c'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/metadata',
    component: ComponentCreator('/__docusaurus/debug/metadata', '156'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/registry',
    component: ComponentCreator('/__docusaurus/debug/registry', '88c'),
    exact: true
  },
  {
    path: '/__docusaurus/debug/routes',
    component: ComponentCreator('/__docusaurus/debug/routes', '000'),
    exact: true
  },
  {
    path: '/docs',
    component: ComponentCreator('/docs', 'b41'),
    routes: [
      {
        path: '/docs',
        component: ComponentCreator('/docs', 'ea1'),
        routes: [
          {
            path: '/docs',
            component: ComponentCreator('/docs', '125'),
            routes: [
              {
                path: '/docs/installation/pbs-installation',
                component: ComponentCreator('/docs/installation/pbs-installation', '7a5'),
                exact: true,
                sidebar: "tutorials"
              },
              {
                path: '/docs/installation/proxmox-ve',
                component: ComponentCreator('/docs/installation/proxmox-ve', '932'),
                exact: true
              },
              {
                path: '/docs/intro',
                component: ComponentCreator('/docs/intro', '853'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/architecture-pbs',
                component: ComponentCreator('/docs/sauvegarde/architecture-pbs', 'daf'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/cas-utilisation-pbs',
                component: ComponentCreator('/docs/sauvegarde/cas-utilisation-pbs', '57d'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/configuration-pbs',
                component: ComponentCreator('/docs/sauvegarde/configuration-pbs', '701'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/depannage-pbs',
                component: ComponentCreator('/docs/sauvegarde/depannage-pbs', 'c5f'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/fonctionnalites-avancees-pbs',
                component: ComponentCreator('/docs/sauvegarde/fonctionnalites-avancees-pbs', 'a65'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/installation-pbs',
                component: ComponentCreator('/docs/sauvegarde/installation-pbs', '6d8'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/intro-pbs',
                component: ComponentCreator('/docs/sauvegarde/intro-pbs', '43b'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/pbs-synology',
                component: ComponentCreator('/docs/sauvegarde/pbs-synology', '8be'),
                exact: true,
                sidebar: "tutorials"
              },
              {
                path: '/docs/sauvegarde/securite-pbs',
                component: ComponentCreator('/docs/sauvegarde/securite-pbs', 'c94'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/tutorials',
                component: ComponentCreator('/docs/sauvegarde/tutorials', 'ad4'),
                exact: true
              },
              {
                path: '/docs/sauvegarde/utilisation-pbs',
                component: ComponentCreator('/docs/sauvegarde/utilisation-pbs', '92c'),
                exact: true
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/',
    component: ComponentCreator('/', '2e1'),
    exact: true
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
