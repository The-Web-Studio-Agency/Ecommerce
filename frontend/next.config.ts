import type { NextConfig } from 'next';

/**
 * Product images are served from wherever the catalogue points: the
 * backend's own /media mount for uploads, and picsum.photos in the seeded
 * development catalogue. The API host is derived from the configured URL so
 * this does not have to be kept in sync by hand.
 */
function apiImagePattern() {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (!raw) return [];

  try {
    const url = new URL(raw);
    return [
      {
        protocol: url.protocol.replace(':', '') as 'http' | 'https',
        hostname: url.hostname,
        port: url.port || undefined,
        pathname: '/media/**',
      },
    ];
  } catch {
    return [];
  }
}

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'picsum.photos', pathname: '/**' },
      { protocol: 'https', hostname: 'fastly.picsum.photos', pathname: '/**' },
      ...apiImagePattern(),
    ],
  },
};

export default nextConfig;
