const AUTH_SELF_PATHS = new Set(['/', '/login', '/signup', '/logout', '/auth/callback']);

export function sanitizeRedirectPath(raw: unknown): string {
    if (typeof raw !== 'string') return '/';
    const trimmed = raw.trim();
    if (
        !trimmed.startsWith('/') ||
        trimmed.startsWith('//') ||
        trimmed.startsWith('/\\') ||
        // Reject ASCII control characters (tabs/newlines) that WHATWG URL strips before '//'
        // biome-ignore lint/suspicious/noControlCharactersInRegex: deliberate open-redirect control-char rejection
        /[\u0000-\u001F\u007F]/.test(trimmed)
    ) {
        return '/';
    }
    return trimmed;
}

export function resolveCurrentReturnPath(): string {
    if (typeof window === 'undefined') return '/';
    const candidate = `${window.location.pathname || '/'}${window.location.search || ''}`;
    const safe = sanitizeRedirectPath(candidate);
    return AUTH_SELF_PATHS.has(window.location.pathname || '/') ? '/' : safe;
}

export function buildOAuthCallbackUrl(origin: string, currentPath?: string): string {
    const cleanOrigin = origin.replace(/\/$/, '');
    const safeNext = sanitizeRedirectPath(currentPath);
    const barePath = safeNext.split('?')[0] ?? '/';
    if (AUTH_SELF_PATHS.has(barePath)) {
        return `${cleanOrigin}/auth/callback`;
    }
    return `${cleanOrigin}/auth/callback?next=${encodeURIComponent(safeNext)}`;
}
