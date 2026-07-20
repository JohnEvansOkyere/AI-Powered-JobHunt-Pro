import type { MetadataRoute } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_APP_URL || 'https://veloxahire.org'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/auth/', '/dashboard/', '/profile/', '/register'],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  }
}
