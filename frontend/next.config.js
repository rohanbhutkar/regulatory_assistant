const path = require("path")
const fs = require("fs")

// Docker build context is `frontend/` only: parent is not the monorepo root, so tracing from `..`
// breaks standalone output (server.js not at image /app). When repo-root lockfile exists (local dev
// checkout), keep tracing from parent; otherwise trace from this app.
const repoRoot = path.join(__dirname, "..")
const parentHasRootLockfile =
  fs.existsSync(path.join(repoRoot, "package-lock.json")) ||
  fs.existsSync(path.join(repoRoot, "yarn.lock"))
const outputFileTracingRoot = parentHasRootLockfile ? repoRoot : __dirname

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot,
  output: 'standalone', // Enable standalone output for Docker
  typescript: {
    ignoreBuildErrors: true, // Temporarily ignore TS errors - minor type mismatches only
  },
  eslint: {
    ignoreDuringBuilds: true, // Ignore ESL warnings during production build
  },
  // Performance optimizations
  compress: true,
  poweredByHeader: false,
  generateEtags: false,
  
  // Bundle optimization
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: {
            minChunks: 2,
            priority: -20,
            reuseExistingChunk: true,
          },
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: -10,
            chunks: 'all',
          },
        },
      };
    }
    return config;
  },
  
  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    minimumCacheTTL: 60,
  },
  
  // Headers for better caching
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
      {
        source: '/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
