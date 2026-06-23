/** @type {import('next').NextConfig} */
const nextConfig = {
  // PixiJS owns a single long-lived WebGL context on the canvas. React Strict Mode's
  // dev-only double-mount destroys and reuses that canvas, whose dead GL context then
  // returns 0 for MAX_FRAGMENT_UNIFORM_VECTORS — crashing Pixi's shader check.
  // Disabling Strict Mode avoids the double-mount. (No effect on production builds.)
  reactStrictMode: false,
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
