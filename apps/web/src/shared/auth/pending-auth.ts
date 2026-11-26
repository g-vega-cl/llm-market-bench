const AUTH_STARTED_KEY = 'benchify_auth_started';

export function markPendingGoogleAuth(): void {
    if (typeof window === 'undefined') return;
    try {
        window.sessionStorage.setItem(AUTH_STARTED_KEY, 'google');
    } catch {
        // Storage can be blocked in private browsing or restricted iframes; OAuth still proceeds.
    }
}

export function clearPendingGoogleAuth(): void {
    if (typeof window === 'undefined') return;
    try {
        window.sessionStorage.removeItem(AUTH_STARTED_KEY);
    } catch {
        // Ignore storage access failures in restricted environments.
    }
}

export function consumePendingGoogleAuth(): string | null {
    if (typeof window === 'undefined') return null;
    try {
        const provider = window.sessionStorage.getItem(AUTH_STARTED_KEY);
        if (!provider) return null;
        window.sessionStorage.removeItem(AUTH_STARTED_KEY);
        return provider;
    } catch {
        return null;
    }
}
