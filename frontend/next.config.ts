import type { NextConfig } from "next";

const BACKEND_URL = process.env.COGNICARE_BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // Proxy API calls to the FastAPI backend. In the Freebuff preview the
        // backend runs on the same machine, so proxying server-side means the
        // browser only ever talks to the Next.js origin.
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
