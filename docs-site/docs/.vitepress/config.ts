import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'OnRamp',
  description: 'Azure Landing Zone Architect & Deployer',
  base: '/onramp/',
  ignoreDeadLinks: [
    /localhost/,
  ],
  themeConfig: {
    logo: '/logo.svg',
    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'API', link: '/api/' },
      { text: 'Development', link: '/development/' },
      { text: 'GitHub', link: 'https://github.com/JoshLuedeman/onramp' },
    ],
    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Quick Start', link: '/guide/quick-start' },
            { text: 'Deploy to Azure', link: '/guide/deploy-to-azure' },
          ],
        },
        {
          text: 'User Guide',
          items: [
            { text: 'Questionnaire', link: '/guide/questionnaire' },
            { text: 'Architecture', link: '/guide/architecture' },
            { text: 'Compliance', link: '/guide/compliance' },
            { text: 'Bicep Templates', link: '/guide/bicep' },
            { text: 'Deployment', link: '/guide/deployment' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/' },
            { text: 'Questionnaire', link: '/api/questionnaire' },
            { text: 'Architecture', link: '/api/architecture' },
            { text: 'Compliance', link: '/api/compliance' },
            { text: 'Bicep', link: '/api/bicep' },
            { text: 'Deployment', link: '/api/deployment' },
            { text: 'Projects', link: '/api/projects' },
          ],
        },
      ],
      '/development/': [
        {
          text: 'Development',
          items: [
            { text: 'Setup', link: '/development/' },
            { text: 'Architecture', link: '/development/architecture' },
            { text: 'Testing', link: '/development/testing' },
            { text: 'Contributing', link: '/development/contributing' },
          ],
        },
      ],
    },
    search: { provider: 'local' },
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024 OnRamp Contributors',
    },
  },
  markdown: {
    mermaid: false,
  },
})
