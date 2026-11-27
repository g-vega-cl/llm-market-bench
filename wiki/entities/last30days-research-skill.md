---
tags: [research, skill, tooling, agents, last30days]
category: entity
---

# last30days Research Skill

Third-party agent skill (`mvanhorn/last30days-skill`) that researches any topic across Reddit, X, YouTube, TikTok, Instagram, Hacker News, Polymarket, GitHub, arXiv, Techmeme, Digg, DEV Community, DripStack, and the open web, scores results by real engagement rather than editorial choice, and synthesizes one cited brief for a 30-day window. Installed on this workstation for the three agent hosts in use — Hermes, Pi, and Antigravity — as a general research tool for work outside this repo's own pipeline.

## Install layout

One canonical copy, symlinked into each host so a single update covers all three:

```sh
npx skills add mvanhorn/last30days-skill -g -y -s last30days \
  -a hermes-agent -a pi -a antigravity
```

- `~/.agents/skills/last30days` — canonical copy; Pi reads this directory natively
- `~/.hermes/skills/last30days` — symlink, registered by Hermes (`hermes skills list` shows `last30days | local | enabled`)
- `~/.gemini/config/skills/last30days` — symlink, Antigravity's global skills directory

Update with `npx skills update last30days -g`; remove with `npx skills remove last30days -g`. Skill updates replace the skill directory only — `~/.config/last30days/.env` and the binaries in `~/.local/bin` are untouched.

## Configuration

All runtime config lives in `~/.config/last30days/.env` (mode 600). The engine reads it on every run; nothing of it is exported into an interactive shell.

| Key | Purpose |
| :--- | :--- |
| `BRAVE_API_KEY` | Web search backend (free tier). Also enables entity resolution — without a web backend the engine logs `No web search backend available, skipping resolve`, so handles/sites for people and companies are never looked up |
| `SCRAPECREATORS_API_KEY` | 10,000 free calls: TikTok, Instagram, Threads, Pinterest, Meta ads, Telegram; Reddit search backfill; YouTube search backfill; YouTube transcript rescue |
| `AUTH_TOKEN` + `CT0` | X/Twitter search through the `bird` backend, taken from the Firefox `x.com` session cookies |
| `LAST30DAYS_REDDIT_SC_MIN_ITEMS=0` | Reddit calls ScrapeCreators only when the free path returns nothing, instead of below the default 5-item floor |
| `LAST30DAYS_YT_SC_MIN_ITEMS=0` | Same for YouTube search backfill (default floor is 3 videos) |
| `INCLUDE_SOURCES=devto,dripstack` | Keyless opt-ins that are otherwise off: DEV Community articles, DripStack financial newsletters |
| `BROWSER_CONSENT=true` | Written by `setup --allow-browser-cookies`; authorises cookie reads for sources that need a login |
| `SETUP_COMPLETE=true` | Written by `setup`; suppresses the first-run gate |

Secrets belong only in that file. The skill's own secret scanner and this repo's [[entities/secret-scanner]] both fail on tokens pasted into tracked files, so documenting key names — never values — is the rule.

## X authentication needs static tokens

`setup --allow-browser-cookies` reports `No complete X login was found in the scanned browser profiles` even with a live x.com session, because the engine snapshots Firefox's `cookies.sqlite` through SQLite's backup API with a hard-coded 1-second deadline. With Firefox running, the WAL is being written continuously and the snapshot times out (`Timed out taking browser database snapshot` in the reader's debug log).

The working path is to write the two session cookies into the config directly:

```sh
# copy cookies.sqlite AND its -wal sidecar, then read auth_token + ct0 for host x.com
sqlite3 cookies.sqlite "select name, value from moz_cookies where name in ('auth_token','ct0') and host in ('x.com','.x.com');"
```

The engine prefers explicit `AUTH_TOKEN`/`CT0` over any browser read (`never overwritten`), so research runs never touch the cookie database. Values rotate when the account is logged out or the password changes — re-extract and update the file when X posts stop coming back.

## Free source CLIs

YouTube runs on `yt-dlp` (installed via `pipx`, binary in `~/.local/bin`). arXiv, Techmeme, Yahoo Finance, Digg, and Trustpilot run on Go binaries from the Printing Press library, built into `~/.local/bin` as `*-pp-cli`.

Go is required to build them and lives at `~/.local/go/bin/go` — deliberately not on `PATH`, since it is only needed when rebuilding a CLI.

Every one of those modules pins `github.com/enetx/http3 v1.0.7`, a version that no longer resolves from GitHub or the module proxy, so the stock installer fails with `go: downloading github.com/enetx/http3 v1.0.7 … could not read Username for 'https://github.com'`. The binaries are built from a clone instead:

```sh
git clone --depth 1 https://github.com/mvanhorn/printing-press-library.git
cd printing-press-library/library/<category>/<cli>
go mod edit -droprequire github.com/enetx/http3 \
  -require github.com/enetx/surf@v1.0.256 -require github.com/enetx/g@v1.1.1
go build -o ~/.local/bin/<cli>-pp-cli ./cmd/<cli>-pp-cli
```

`printing-press-library update` will keep failing for these five CLIs; rebuild them with the recipe above rather than debugging the installer.

## Trustpilot stays opt-in

`trustpilot-pp-cli` needs an interactive `trustpilot-pp-cli auth login` (it opens a browser) and a research run only uses it within 3 minutes of that login. It is therefore installed but absent from `INCLUDE_SOURCES`; reach for it per run with `--search trustpilot --trustpilot-domain <domain>`. Adding it to `INCLUDE_SOURCES` only produces a skipped-source line on every company run.

## Verification

Run these from `~/.agents/skills/last30days`:

```sh
python3 scripts/last30days.py --preflight   # planned reads/writes, no live research
python3 scripts/last30days.py --diagnose    # JSON: available sources, credentials, external CLIs
python3 scripts/last30days.py doctor        # per-source health plus printed fixes
```

A configured full-depth run reports `✓ Research complete` with these sources active: arXiv, dev.to, Digg, Web, Hacker News, Instagram, Reddit, Techmeme, TikTok, X, YouTube.

## Credit and privacy behaviour

ScrapeCreators credits are spent by TikTok/Instagram search, Reddit backfill under the floor, YouTube backfill under the floor, and YouTube transcript rescue — the rescue path is not gated by `LAST30DAYS_YT_SC_MIN_ITEMS`, so a YouTube run with failing free transcripts still spends calls.

Reranking of results (`auto` mode) inherits `OPENAI_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, or `GEMINI_API_KEY` from the shell and sends the topic plus shortlisted snippets to that provider. With none of them set, scoring stays local and only the source APIs see traffic — the same posture as this repo's [[entities/free-llm-proxy]] routes, where keys stay out of the interactive shell.

## Known gaps

- Reddit's direct site search returns `HTTP 403: Blocked` from this network; coverage comes from the Arctic Shift archive path plus ScrapeCreators. A logged-in Reddit session (`setup --reddit-session`) is the untaken option and may breach Reddit's terms.
- Keyless web search (DuckDuckGo HTML, Startpage) is unusable here — DuckDuckGo answers HTTP 202 with a bot challenge — so `BRAVE_API_KEY` is load-bearing, not optional.
- Digg's CLI has no score-free fallback and stays unlisted unless `digg-pp-cli` is on `PATH`, which the local build satisfies.

## Related

- [[entities/free-llm-proxy]] — provider pool behind this repo's own LLM calls; the same "no keys in the shell" posture keeps last30days reranking local
- [[concepts/deepseek-web-search]] — the repo's own web-search integration for agents
- [[entities/agent-rules]] — agent instruction precedence, including the QMD-first search mandate
- [[entities/verify-skill]] — verification protocol used before committing changes
