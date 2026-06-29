/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // BACKEND_URL is a server-side build var (set in Vercel env vars)
    // NEXT_PUBLIC_API_URL is client-side only — not reliable in next.config.js
    const backendUrl = (
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://127.0.0.1:8000'
    ).replace(/\/$/, '') // strip trailing slash if any

    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
