import type { NextConfig } from "next";

const githubPages = process.env.GITHUB_ACTIONS === "true";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(githubPages
    ? {
        output: "export",
        basePath: "/WritlyxAI",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {}),
};

export default nextConfig;
