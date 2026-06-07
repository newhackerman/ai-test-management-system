const CracoLessPlugin = require('craco-less');
const CracoAliasPlugin = require('craco-alias');

module.exports = {
  plugins: [
    {
      plugin: CracoLessPlugin,
      options: {
        lessLoaderOptions: {
          lessOptions: {
            modifyVars: {
              '@primary-color': '#1890ff',
              '@border-radius-base': '4px',
              '@font-size-base': '14px',
              '@heading-color': 'rgba(0, 0, 0, 0.85)',
              '@text-color': 'rgba(0, 0, 0, 0.65)',
              '@text-color-secondary': 'rgba(0, 0, 0, 0.45)',
              '@disabled-color': 'rgba(0, 0, 0, 0.25)',
              '@border-color-base': '#d9d9d9',
              '@box-shadow-base': '0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
            },
            javascriptEnabled: true,
          },
        },
      },
    },
    {
      plugin: CracoAliasPlugin,
      options: {
        source: 'jsconfig',
        // baseUrl 与 jsconfig 中的保持一致
        baseUrl: './',
        // 别名配置，与 jsconfig 中的 paths 保持一致
        aliases: {
          '@': './src',
          '@/components': './src/components',
          '@/pages': './src/pages',
          '@/utils': './src/utils',
          '@/services': './src/services',
          '@/store': './src/store',
          '@/hooks': './src/hooks',
          '@/types': './src/types',
          '@/assets': './src/assets',
        },
      },
    },
  ],
};