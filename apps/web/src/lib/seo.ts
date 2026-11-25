export const SITE_URL = 'https://benchify.dev';
export const DEFAULT_OG_IMAGE = `${SITE_URL}/og-image.png`;

export function canonicalUrl(path = '/'): string {
    const normalized = path.startsWith('/') ? path : `/${path}`;
    return `${SITE_URL}${normalized}`;
}

export const seo = ({
    title,
    description,
    keywords,
    image = DEFAULT_OG_IMAGE,
}: {
    title: string;
    description?: string;
    image?: string;
    keywords?: string;
}) => {
    return [
        { title },
        { name: 'description', content: description },
        ...(keywords ? [{ name: 'keywords', content: keywords }] : []),
        { name: 'robots', content: 'index,follow' },
        { property: 'og:site_name', content: 'Benchify' },
        { name: 'twitter:title', content: title },
        { name: 'twitter:description', content: description },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:image', content: image },
        { property: 'og:type', content: 'website' },
        { property: 'og:title', content: title },
        { property: 'og:description', content: description },
        { property: 'og:image', content: image },
    ];
};
