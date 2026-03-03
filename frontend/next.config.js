/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.BACKEND_URL || "http://localhost:8000",
    NEXT_PUBLIC_WS_URL: process.env.WS_URL || "ws://localhost:8000",
  },
};

module.exports = nextConfig;
