--- 
tags: [privacy, legal, data-handling] 
category: source 
---

# Privacy Policy

The platform's privacy policy governs how user data is collected, stored, processed, and shared. Key provisions:

## Data Collection

- **Account data**: email address, password hash, and Google profile information (email, display name) obtained via Supabase Auth. Passwords are never stored in plaintext.
- **Product data**: bot descriptions, starter ideas, alignment answers, compiled strategies, backtest settings, and user-created results.
- **Usage data**: page views, clicks, feature interactions, and errors captured by PostHog. Session replay captures form inputs masked; on-page text including bot descriptions, compiled strategies, and chat messages is part of the replay. Browser console logs and unhandled errors are captured for debugging.
- **Technical and security data**: IP-derived coarse location, device/browser type, timestamps, and Cloudflare Turnstile abuse-prevention tokens.
- **Support communications**: messages sent when contacting us about the product.
- **Language-model providers**: When users describe a bot, answer alignment questions, compile a strategy, or use the research chat, the text is sent to third-party AI providers. Currently includes DeepSeek (direct chat), MiniMax (market commentary), and the model gateway that routes compilation and analysis, which fronts Groq, Google (Gemini), OpenRouter, Nous Research, NVIDIA, Kilo, and OpenCode. Those providers may process text outside the user's country, and the set of providers changes as models are added or retired.

## Data Storage

- **Browser storage**: Used for two purposes: keeping users signed in (Supabase auth cookies and storage) and remembering product state such as in-progress drafts. Product analytics does not use cookies or local storage — PostHog state is held in page memory for the duration of a visit, so a returning anonymous visitor is not recognised.
- **PostHog analytics**: State is held in page memory; aggregate usage data is stored in the United States and can no longer be linked to an individual account upon deletion.
- **No advertising cookies or data sales** to advertisers.

## Cookies and Local Storage

- Benchify uses browser storage for: keeping you signed in (Supabase auth cookies and storage) and remembering product state such as in-progress drafts. Product analytics does not use cookies or local storage — PostHog state is held in page memory for the duration of a visit.
- PostHog processes and stores analytics data in the United States.
- A generic third-party blocker will not stop analytics requests, which go through `https://benchify.dev/p/*`. Blocking that path or enabling browser tracking protection will.

## Your Choices and Deletion Rights

- You can request access to, correction of, or deletion of your account and product data by emailing privacy@benchify.dev. Requests are verified and responded to within 30 days.
- Browser-only drafts can be deleted by clearing site data.
- Analytics opt-out is achieved by blocking `https://benchify.dev/p/*` or enabling browser tracking protection.
- Deleting your account does not erase aggregate usage data that can no longer be linked to you.

## Related
- [[concepts/posthog-stealth-proxy]] — PostHog same-origin proxy architecture
- [[concepts/env-based-secrets]] — environment variable injection rules for secrets
- [[entities/web-app]] — dashboard consuming analytics and auth clients
- [[entities/database]] — schema and RLS details
