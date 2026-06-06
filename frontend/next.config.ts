import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendPort = process.env.BACKEND_PORT || "8000";
    return [
      {
        source: "/api/:path*",
        destination: `http://localhost:${backendPort}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
