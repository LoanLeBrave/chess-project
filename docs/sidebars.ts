import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  mainSidebar: [
    {
      type: 'doc',
      id: 'index',
      label: 'Introduction',
    },
    {
      type: 'category',
      label: 'Architecture',
      collapsed: false,
      items: [
        'architecture/overview',
        'architecture/components',
        'architecture/data-flow',
      ],
    },
    {
      type: 'category',
      label: 'Modules principaux',
      collapsed: false,
      items: [
        'core/chess-manager',
        'core/robot-controller',
        'core/vision-service',
        'core/config',
      ],
    },
    {
      type: 'category',
      label: 'Fonctionnalités',
      collapsed: true,
      items: [
        'features/game-flow',
        'features/pause-resume',
        'features/castling',
        'features/promotion',
        'features/replacement',
        'features/leaderboard',
      ],
    },
    {
      type: 'category',
      label: 'Robot UR5e',
      collapsed: true,
      items: [
        'robot/movements',
        'robot/gripper',
        'robot/calibration',
      ],
    },
    {
      type: 'category',
      label: 'Vision par ordinateur',
      collapsed: true,
      items: [
        'chess-vision/aruco',
        'chess-vision/grid',
        'chess-vision/synchronization',
      ],
    },
    {
      type: 'category',
      label: 'Référence API',
      collapsed: true,
      items: [
        'api-reference/endpoints',
        'api-reference/websocket',
        'api-reference/game-routes',
        'api-reference/robot-routes',
        'api-reference/leaderboard-routes',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      collapsed: true,
      items: [
        'guides/quickstart',
        'guides/calibration',
        'guides/troubleshooting',
      ],
    },
  ],
};

export default sidebars;
