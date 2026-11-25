# Benchify Launch Readiness

**Site:** https://benchify.dev  
**Repo:** `llm-market-bench`  
**Snapshot:** 2026-11-25

Assumption: "publicizing" means getting strangers to visit, sign up, and try the bot builder — not just sharing a demo with friends.

Verdict: the site works and the core flow is credible, but it is **not ready for a broad public push**. Finish P0, then do a soft launch. Finish P1 before the big announcement.

---

## P0 — Blockers before publicizing

- [x] **Privacy Policy** — say what is collected (account email, usage analytics, bot drafts), what providers receive it (Supabase, PostHog), retention, and deletion rights.
  - Done when: linked in footer, signup, and login; readable on mobile; no vague "we may collect data" filler.
- [x] **Terms of Service** — beta status, acceptable use, limitation of liability, account responsibilities.
  - Done when: linked wherever signup happens; acceptance is explicit or clearly implied by account creation.
- [x] **Financial disclaimer** — not financial advice, paper trading by default, no return guarantees, past backtests do not predict future results.
  - Done when: visible on landing page, builder, leaderboard, and in the footer.
- [x] **Cookie/analytics notice** — disclose PostHog and whether consent is required.
  - Done when: notice matches actual tracking behavior in `apps/web/src/routes/__root.tsx`.
- [x] **Legal links in footer + auth surfaces** — not buried in code.
  - Done when: Privacy, Terms, Disclaimer links are reachable from every page including `/login` and `/signup`.
- [x] **Verify production deploy matches `main`** — repo was 1 commit ahead of `origin/main` at snapshot time.
  - Done when: Netlify deploy is built from the intended commit and the live page reflects it.
- [x] **Fix SEO identity** — titles/descriptions should consistently say "Benchify: build and backtest trading bots".
  - Done when: root `head`, homepage, `/build`, `/personality`, and `/leaderboard` metadata agree.
- [x] **Remove placeholder metadata** — `twitter:creator` / `twitter:site` currently point to `@tannerlinsley`.
  - Done when: replaced with the real Benchify account or removed.
- [x] **Add `sitemap.xml`** — currently 404s.
  - Done when: `/sitemap.xml` returns valid XML with canonical public routes.
- [x] **Fix `robots.txt`** — currently only content-signal comments.
  - Done when: includes `User-agent: *`, `Allow: /`, and `Sitemap: https://benchify.dev/sitemap.xml`.
- [x] **Add OG image + canonical URL** — required for decent link previews on X, LinkedIn, Reddit, and Slack.
  - Done when: `og:image`, `twitter:image`, `twitter:card`, and `link rel="canonical"` render in page source.
- [x] **Define activation metric** — e.g. "user compiled a bot and ran a backtest", not just signup.
  - Done when: a named PostHog event exists and a funnel can be reported from visit → activation.

### P0 completion notes (2026-11-25)

- **Deploy evidence:** Netlify builds were stopped (`stop_builds: true`) and had been stuck on commit `6fc031b` since 2026-11-23. Builds were re-enabled and a production deploy was triggered for `ddf07def` (deploy `6b0743fe8ef30301a09a8651`, state `ready`, published 20:25 UTC). The self-hosted watcher behind `benchify.dev` also advanced to `ddf07def`. Live `benchify.dev`, `www.benchify.dev`, and `main--benchify.netlify.app` all serve the new title and the new legal routes.
- **Final wording verification:** commit `20b6e63e` (explicit no-return-guarantee wording) was also deployed and verified live on both `benchify.dev` and `main--benchify.netlify.app`.
- **Live page checks:** `/`, `/build`, `/personality`, `/leaderboard`, `/privacy`, `/terms`, `/disclaimer`, `/login`, and `/signup?next=%2F` return the expected titles, canonical links, OG tags, footer, disclaimer bar, and legal links. No `tannerlinsley` metadata remains.
- **Static files:** `/robots.txt` includes `User-agent: *`, `Allow: /`, and the sitemap directive. `/sitemap.xml` returns valid XML with the nine public routes. `/og-image.png` returns `image/png` at 1200×630.
- **Activation funnel:** `$pageview` → `user_signed_up` → `builder_opened` → `builder_compiled` → `bot_activated` → `run_queued`. `bot_activated` fires once per browser session from `track()` on the first `run_queued` event, with `source: backtest_queued` and the `recipeId`/`jobId` props. The event name is in the live JS bundle.
- **Verification:** 1536 web tests pass, `pnpm --filter web build` (including `tsc --noEmit`) passes, and targeted Biome checks are clean. The new bundle hash containing `bot_activated` is live.
- **Follow-up outside P0:** have the legal copy reviewed by counsel and confirm `privacy@benchify.dev` / `hello@benchify.dev` mailboxes are monitored before the public push.

---

## P1 — Needed for credible conversion

- [ ] **Landing page proof** — show real bot performance, methodology, timestamps, and paper/live labels.
- [ ] **Clear explanation of the product** — one sentence, who it is for, what it does, why it is different.
- [ ] **FAQ / How it works** — answer "is this real money?", "where does data come from?", "how are bots scored?"
- [ ] **Getting-started guide** — 3 steps from signup to first backtest.
- [ ] **Contact/support path** — email, GitHub issues, or Discord.
- [ ] **Leaderboard trust** — explain ranking, sample size, date range, survivorship bias, and failures.
- [ ] **Builder success + failure states** — users should never hit a dead end without explanation.
- [ ] **Email capture outside paywall** — newsletter/waitlist for users who are not ready to sign up.
- [ ] **Analytics funnel dashboard** — visit → signup → draft → compile → backtest → Live → return.

---

## P2 — Quality and scale

- [ ] **Lighthouse pass** — mobile, performance, accessibility, best practices, SEO.
- [ ] **Voxel scene fallback** — reduced-motion and low-end device handling.
- [ ] **Rate limiting + abuse checks** — signup, compile, LLM-backed endpoints.
- [ ] **Secrets scan** — verify no keys in client bundle or public config.
- [ ] **Error monitoring alerts** — PostHog/Sentry-style alerting for server failures.
- [ ] **Rollback plan** — know how to revert a bad deploy quickly.
- [ ] **Load test builder flow** — especially compile/backtest endpoints.
- [ ] **Docs for models/data sources** — explain what tools and providers are used.

---

## P3 — Launch assets

- [ ] **Social preview image**
- [ ] **30–60s demo video or GIF** of sentence → bot → backtest
- [ ] **Launch post** for X / LinkedIn / Reddit / HN
- [ ] **3 supporting posts** about benchmark methodology, failures, and lessons
- [ ] **Feedback loop** — in-app "what confused you?" prompt
- [ ] **Weekly review ritual** — activation, retention, signup conversion, top drop-offs

---

## Recommended sequence

1. Finish P0.
2. Soft launch to 20–50 people.
3. Watch activation and drop-offs.
4. Finish P1.
5. Public announcement.
