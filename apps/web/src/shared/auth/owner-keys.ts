/**
 * Owner keys for the token ledger.
 *
 * Lives apart from `guest-cookie.ts` on purpose: that module signs cookies with
 * `node:crypto`, and the quota API that needs these helpers is part of the
 * client graph. Importing the signer there fails the production build with
 * "createHmac is not exported by __vite-browser-external".
 *
 * One prefix per audience, defined once — the ledger, the RPCs and the balance
 * read all key on these strings, and a mismatch between them is silent.
 */

export function guestOwnerKey(sessionId: string): string {
    return `guest:${sessionId}`;
}

export function userOwnerKey(id: string): string {
    return `user:${id}`;
}
