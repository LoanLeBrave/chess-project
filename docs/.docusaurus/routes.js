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
    path: '/markdown-page',
    component: ComponentCreator('/markdown-page', '3d7'),
    exact: true
  },
  {
    path: '/',
    component: ComponentCreator('/', '6cf'),
    routes: [
      {
        path: '/',
        component: ComponentCreator('/', '6d2'),
        routes: [
          {
            path: '/',
            component: ComponentCreator('/', '6f7'),
            routes: [
              {
                path: '/api-reference/endpoints',
                component: ComponentCreator('/api-reference/endpoints', 'e21'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/api-reference/game-routes',
                component: ComponentCreator('/api-reference/game-routes', '302'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/api-reference/leaderboard-routes',
                component: ComponentCreator('/api-reference/leaderboard-routes', 'd13'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/api-reference/robot-routes',
                component: ComponentCreator('/api-reference/robot-routes', '167'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/api-reference/websocket',
                component: ComponentCreator('/api-reference/websocket', 'c05'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/architecture/components',
                component: ComponentCreator('/architecture/components', '1f7'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/architecture/data-flow',
                component: ComponentCreator('/architecture/data-flow', '3e8'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/architecture/overview',
                component: ComponentCreator('/architecture/overview', 'fd5'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/chess-vision/aruco',
                component: ComponentCreator('/chess-vision/aruco', '78b'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/chess-vision/grid',
                component: ComponentCreator('/chess-vision/grid', 'a47'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/chess-vision/synchronization',
                component: ComponentCreator('/chess-vision/synchronization', '1da'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/core/chess-manager',
                component: ComponentCreator('/core/chess-manager', '06b'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/core/config',
                component: ComponentCreator('/core/config', '188'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/core/robot-controller',
                component: ComponentCreator('/core/robot-controller', '2d2'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/core/vision-service',
                component: ComponentCreator('/core/vision-service', '16e'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/castling',
                component: ComponentCreator('/features/castling', '6be'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/game-flow',
                component: ComponentCreator('/features/game-flow', '184'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/leaderboard',
                component: ComponentCreator('/features/leaderboard', 'ccc'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/pause-resume',
                component: ComponentCreator('/features/pause-resume', '436'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/promotion',
                component: ComponentCreator('/features/promotion', '323'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/features/replacement',
                component: ComponentCreator('/features/replacement', 'a9b'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/guides/calibration',
                component: ComponentCreator('/guides/calibration', '3ac'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/guides/quickstart',
                component: ComponentCreator('/guides/quickstart', '070'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/guides/troubleshooting',
                component: ComponentCreator('/guides/troubleshooting', 'e44'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/robot/calibration',
                component: ComponentCreator('/robot/calibration', 'f46'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/robot/gripper',
                component: ComponentCreator('/robot/gripper', '0a6'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/robot/movements',
                component: ComponentCreator('/robot/movements', 'c12'),
                exact: true,
                sidebar: "mainSidebar"
              },
              {
                path: '/',
                component: ComponentCreator('/', 'c02'),
                exact: true,
                sidebar: "mainSidebar"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '*',
    component: ComponentCreator('*'),
  },
];
