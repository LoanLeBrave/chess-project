import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Chess Robot — Documentation',
  tagline: 'Robot UR7e joueur d\'échecs autonome',
  favicon: 'img/logo_doc.png',

  future: {
    v4: true,
  },

  url: 'http://localhost',
  baseUrl: '/',

  organizationName: 'junia',
  projectName: 'chess-robot',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'fr',
    locales: ['fr'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Chess Robot',
      logo: {
        alt: 'Chess Robot Logo',
        src: 'img/logo_doc.jpeg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'mainSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          to: '/concepts',
          position: 'left',
          label: 'Concepts clés',
        },
        {
          href: 'https://github.com/LoanLeBrave/chess-project',
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
            {label: 'Introduction', to: '/'},
            {label: 'Architecture', to: '/architecture/overview'},
            {label: 'Référence API', to: '/api-reference/endpoints'},
          ],
        },
        {
          title: 'Guides',
          items: [
            {label: 'Démarrage rapide', to: '/guides/quickstart'},
            {label: 'Calibration', to: '/guides/calibration'},
            {label: 'Dépannage', to: '/guides/troubleshooting'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Junia — Chess Robot Project. Documentation Chess Robot.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
