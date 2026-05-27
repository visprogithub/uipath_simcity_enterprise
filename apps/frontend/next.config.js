/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@pixi/react'],
  webpack: (config) => {
    // Ensure PixiJS can be bundled correctly
    config.resolve.alias = {
      ...config.resolve.alias,
    };
    return config;
  },
};

module.exports = nextConfig;
