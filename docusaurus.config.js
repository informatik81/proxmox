// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Documentation Proxmox',
  tagline: 'Base de connaissances avancée sur Proxmox VE et Proxmox Backup Server',
  favicon: 'img/favicon.ico',

  // Set the production url of your site here
  url: 'https://votre-domaine.fr',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/site/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'informatik81', // Usually your GitHub org/user name.
  projectName: 'site', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'fr',
    locales: ['fr'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/votre-organisation/proxmox-docs/tree/main/',
        },
        blog: {
          showReadingTime: true,
          editUrl:
            'https://github.com/votre-organisation/proxmox-docs/tree/main/blog/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/proxmox-social-card.jpg',
      navbar: {
        title: 'Documentation Proxmox',
        logo: {
          alt: 'Logo Proxmox',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: "docSidebar",
            sidebarId: "tutorials",
            position: "left",
            label: "Documentation"
          },
          {
            to: '/docs/sauvegarde/intro-pbs',
            label: 'Proxmox Backup Server',
            position: 'left',
          },
          {
            to: '/blog',
            label: 'Blog',
            position: 'left',
          },
          {
            to: '/admin',
            label: 'Admin',
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
                label: 'Installation',
                to: '/docs/installation/proxmox-ve',
              },
              {
                label: 'Configuration',
                to: '/docs/configuration/reseau-avance',
              },
              {
                label: 'Sauvegarde',
                to: '/docs/sauvegarde/intro-pbs',
              },
            ],
          },
          {
            title: 'Communauté',
            items: [
              {
                label: 'Forum Proxmox',
                href: 'https://forum.proxmox.com/',
              },
              {
                label: 'Reddit',
                href: 'https://www.reddit.com/r/Proxmox/',
              },
            ],
          },
          {
            title: 'Ressources',
            items: [
              {
                label: 'Tutoriels Vidéo',
                to: '/docs/tutos-video/liens-videos',
              },
              {
                label: 'FAQ',
                to: '/docs/faq/erreurs-frequentes',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Documentation Proxmox. Créé avec Docusaurus.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
    }),
    
  // Plugins désactivés temporairement pour le démarrage initial
  plugins: [
    // Décommentez et installez le plugin PWA si nécessaire
    // [
    //   '@docusaurus/plugin-pwa',
    //   {
    //     debug: true,
    //     offlineModeActivationStrategies: [
    //       'appInstalled',
    //       'standalone',
    //       'queryString',
    //     ],
    //     pwaHead: [
    //       {
    //         tagName: 'link',
    //         rel: 'icon',
    //         href: '/img/logo.svg',
    //       },
    //       {
    //         tagName: 'link',
    //         rel: 'manifest',
    //         href: '/manifest.json',
    //       },
    //       {
    //         tagName: 'meta',
    //         name: 'theme-color',
    //         content: '#e2001a',
    //       },
    //     ],
    //   },
    // ],
  ],
};

module.exports = config;