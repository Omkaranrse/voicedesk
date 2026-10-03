import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  eslint: {
    // Warning instead of error so Prettier import order does not block Vercel deployment
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
