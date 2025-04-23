let userConfig = undefined
try {
  userConfig = await import('./v0-user-next.config')
} catch (e) {
  // ignore error
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  experimental: {
    webpackBuildWorker: true,
    parallelServerBuildTraces: true,
    parallelServerCompiles: true,
    asyncWebAssembly: true,
  },
  // Configure large body size limit for API routes
  serverRuntimeConfig: {
    // Will only be available on the server side
    maxBodySize: '100mb',
  },
  // Add CORS config for development
  async headers() {
    return [
      {
        // This allows the browser to make requests to the Python backend
        source: '/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
    ];
  },

  // Add webpack config
  webpack: (config, { isServer }) => {
    // Add WASM support using experiments
    config.experiments = { ...config.experiments, asyncWebAssembly: true, layers: true }; // layers might be needed by some WASM setups

    // Add fallback for node paths for client-side bundles
    // occt-import-js might implicitly depend on these, better to provide fallbacks
    config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false, // fs cannot be polyfilled client-side
        path: false, // path cannot be polyfilled client-side
        // crypto: false, // uncomment if needed
      };

    // Modify rules for WASM files
    config.module.rules.push({
      test: /\.wasm$/,
      type: 'asset/resource', // Treat WASM files as assets
      generator: {
          filename: 'static/wasm/[name].[hash][ext]', // Output WASM to static folder
      }
    });

    // Important: return the modified config
    return config;
  },
}

mergeConfig(nextConfig, userConfig)

function mergeConfig(nextConfig, userConfig) {
  if (!userConfig) {
    return
  }

  for (const key in userConfig) {
    if (
      typeof nextConfig[key] === 'object' &&
      !Array.isArray(nextConfig[key])
    ) {
      nextConfig[key] = {
        ...nextConfig[key],
        ...userConfig[key],
      }
    } else {
      nextConfig[key] = userConfig[key]
    }
  }
}

export default nextConfig
