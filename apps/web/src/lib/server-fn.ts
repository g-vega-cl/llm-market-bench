/**
 * TanStack Start's client resolves a server-function response that is not a
 * `{ result, error, context }` envelope to `undefined` instead of throwing — an
 * edge 502, a request cut off at the origin, a WAF JSON body. Every consumer then
 * reads a property of `undefined` and reports the TypeError instead of the
 * transport failure, or worse, renders an empty state over live data.
 *
 * Call this at the server-function boundary so a missing payload fails loudly and
 * stays retryable (a throwing queryFn keeps TanStack Query's last good data).
 */
export function assertServerFnResult<T>(value: T | undefined, what: string): T {
    if (value === undefined) {
        throw new Error(
            `${what} did not come back — the request was cut off before it finished. Try again.`,
        );
    }
    return value;
}
