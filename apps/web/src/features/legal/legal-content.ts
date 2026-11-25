export interface LegalSection {
    heading: string;
    paragraphs?: string[];
    bullets?: string[];
}

export interface LegalDocument {
    title: string;
    updated: string;
    intro: string;
    sections: LegalSection[];
}

export const privacyPolicy: LegalDocument = {
    title: 'Privacy Policy',
    updated: '2026-11-25',
    intro: 'This policy explains what Benchify collects, why we collect it, who receives it, and how to ask us to delete it. Benchify is a product of the llm-market-bench project and is provided as a beta research and benchmarking tool.',
    sections: [
        {
            heading: 'Information we collect',
            paragraphs: [
                'We collect only the information needed to run the site, keep accounts secure, and understand which parts of the product are useful.',
            ],
            bullets: [
                'Account information: email address, password hash, and, if you sign in with Google, the basic profile information Google returns (such as your email and display name). Passwords are handled by Supabase Auth; we never store your plaintext password.',
                'Product data: bot descriptions, starter ideas, alignment answers, compiled strategies, backtest settings, and results you create in the builder.',
                'Usage data: page views, clicks, feature interactions, and errors captured by PostHog. Session replay is enabled with form inputs masked, but other text on the page — including bot descriptions, compiled strategies, and chat messages — is captured as part of the replay. Browser console logs and unhandled errors are also captured for debugging.',
                'Technical and security data: IP-derived coarse location, device/browser type, timestamps, and abuse-prevention tokens from Cloudflare Turnstile.',
                'Support communications: messages you send when you contact us about the product.',
            ],
        },
        {
            heading: 'Who receives your information',
            paragraphs: [
                'We do not sell your personal information. We use a small set of service providers to operate Benchify:',
            ],
            bullets: [
                'Supabase — authentication and the Postgres database that stores accounts and product data.',
                'PostHog — product analytics, session replay, console logs, and error monitoring.',
                'Netlify — site hosting, builds, and deployment logs.',
                'Cloudflare — Turnstile abuse prevention on signup and login forms.',
                'Google Fonts — fonts loaded by the browser when you view the site.',
                'Language-model providers — when you describe a bot, answer alignment questions, compile a strategy, or use the research chat, the text you write is sent to third-party AI providers so they can produce the reply or the compiled bot. These currently include DeepSeek (direct chat), MiniMax (market commentary), and the model gateway that compilation and analysis are routed through, which currently fronts Groq, Google (Gemini), OpenRouter, Nous Research, NVIDIA, Kilo and OpenCode. Those providers may process your text outside your country, and the set of providers behind the gateway changes as models are added or retired.',
            ],
        },
        {
            heading: 'Cookies and local storage',
            paragraphs: [
                'Benchify uses browser storage for two purposes: keeping you signed in (Supabase auth cookies and storage) and remembering product state such as in-progress drafts. Product analytics does not use cookies or local storage — PostHog state is held in page memory for the duration of a visit, so a returning anonymous visitor is not recognised. We do not use advertising cookies or sell data to advertisers.',
            ],
        },
        {
            heading: 'How long we keep information',
            paragraphs: [
                'Account and product data are kept while your account is active, so you can return to your bots and results. Drafts stored only in your browser remain until you clear them. Usage and diagnostic data are kept for as long as needed to understand product usage and investigate errors, subject to our PostHog project retention settings. We may retain limited records longer where required for security, abuse prevention, or legal reasons.',
            ],
        },
        {
            heading: 'Your choices and deletion rights',
            paragraphs: [
                'You can request access to, correction of, or deletion of your account and product data by emailing privacy@benchify.dev. We will verify the request and respond within 30 days. You can also delete browser-only drafts by clearing site data. Analytics requests are sent through our own domain (https://benchify.dev/p/*) rather than a third-party script, so a generic third-party blocker will not stop them; blocking that path, or enabling your browser’s tracking protection, will. PostHog processes and stores analytics data in the United States. Deleting your account does not erase aggregate usage data that can no longer be linked to you.',
            ],
        },
        {
            heading: 'Children',
            paragraphs: [
                'Benchify is not directed at children under 16. If you believe a child has created an account, contact us and we will remove it.',
            ],
        },
        {
            heading: 'Changes to this policy',
            paragraphs: [
                'We may update this policy as the product changes. The “Updated” date at the top shows the current version. Material changes will be announced on the site before they take effect where practical.',
            ],
        },
        {
            heading: 'Contact',
            paragraphs: [
                'Benchify is run under the Benchify name by the independent llm-market-bench project, established in Ontario, Canada. Questions about privacy or data deletion: privacy@benchify.dev — this address reaches the operator directly.',
            ],
        },
    ],
};

export const termsOfService: LegalDocument = {
    title: 'Terms of Service',
    updated: '2026-11-25',
    intro: 'These terms govern your use of benchify.dev. By creating an account or using the site, you agree to them. Benchify is a beta product, so expect rough edges and changing behavior.',
    sections: [
        {
            heading: 'Who runs Benchify',
            paragraphs: [
                'Benchify is run under the Benchify name by the independent llm-market-bench project, established in Ontario, Canada. “We” in these terms means whoever operates that project.',
            ],
        },
        {
            heading: 'What Benchify is',
            paragraphs: [
                'Benchify lets you describe a trading strategy, compile it into a runnable recipe, and backtest it against point-in-time data. Results are simulations and research outputs, not investment recommendations. See the Financial Disclaimer for important limits.',
            ],
        },
        {
            heading: 'Beta status',
            paragraphs: [
                'The site is in public beta. Features may change, break, or be removed. Backtests and scheduled runs may be delayed, throttled, or unavailable. We do not promise uninterrupted or error-free service.',
            ],
        },
        {
            heading: 'Your account',
            paragraphs: [
                'You are responsible for keeping your credentials secure and for activity that happens under your account. Use an email you control. If you believe your account has been compromised, contact us promptly.',
            ],
        },
        {
            heading: 'Eligibility',
            paragraphs: [
                'You must be at least 16 years old to create an account. If you are under the age of majority where you live, use Benchify only with the involvement of a parent or guardian.',
            ],
        },
        {
            heading: 'Acceptable use',
            paragraphs: [
                'Use Benchify only for lawful purposes. Do not attempt to access other users’ data, overload the service, scrape it beyond normal use, reverse-engineer credentials, submit unlawful or harmful content, or use the output as a basis for unauthorised financial activity.',
            ],
            bullets: [
                'Do not run automated requests that degrade availability for others.',
                'Do not impersonate another person or misrepresent the origin of a strategy.',
                'Do not use Benchify to provide regulated financial advice to third parties.',
            ],
        },
        {
            heading: 'Your content',
            paragraphs: [
                'You retain ownership of the strategies and text you submit. You grant us a limited licence to store and process that content to provide the service. Published bots and leaderboard entries may be shown publicly with their names, summaries, and results; do not publish anything you are not comfortable sharing.',
            ],
        },
        {
            heading: 'Intellectual property',
            paragraphs: [
                'Benchify and its underlying code, design, and documentation remain the property of the project. These terms do not give you ownership of the site or its brand.',
            ],
        },
        {
            heading: 'Limitation of liability',
            paragraphs: [
                'To the maximum extent permitted by law, Benchify and its contributors are not liable for indirect, incidental, special, or consequential damages, lost profits, or trading losses arising from use of the site or its outputs. You use the service at your own risk.',
            ],
        },
        {
            heading: 'Consumer rights',
            paragraphs: [
                'Nothing in these terms removes or limits a right you have under mandatory consumer protection law in your country of residence. If a provision is unenforceable against you for that reason, it is severed to that extent and the rest of these terms stays in force.',
            ],
        },
        {
            heading: 'Changes and termination',
            paragraphs: [
                'We may suspend or terminate accounts that violate these terms or abuse the service. We may update these terms as the product evolves; the “Updated” date shows the current version. Continued use after a change means you accept the revised terms.',
            ],
        },
        {
            heading: 'Governing law and venue',
            paragraphs: [
                'These terms are governed by the laws of Ontario, Canada. The courts of Ontario have exclusive jurisdiction, except that if you are a consumer you may bring proceedings in the courts of your own country of residence where local law gives you that right.',
            ],
        },
        {
            heading: 'General',
            paragraphs: [
                'If any provision of these terms is found unenforceable, the remaining provisions stay in effect. These terms, together with the Privacy Policy and the Financial Disclaimer, are the entire agreement between you and us about the site. A failure to enforce a provision is not a waiver of it. You may not assign your rights under these terms; we may assign ours if the project changes hands.',
            ],
        },
        {
            heading: 'Contact',
            paragraphs: ['Questions about these terms: hello@benchify.dev.'],
        },
    ],
};

export const financialDisclaimer: LegalDocument = {
    title: 'Financial Disclaimer',
    updated: '2026-11-25',
    intro: 'Benchify is an educational research and benchmarking tool. Nothing on this site is financial, investment, legal, or tax advice. No returns are guaranteed.',
    sections: [
        {
            heading: 'No advice or recommendation',
            paragraphs: [
                'Bot descriptions, backtests, leaderboard rankings, model commentary, and generated newsletters are outputs of software and language models. They are not recommendations to buy, sell, or hold any security. Do not treat them as personalised advice.',
            ],
        },
        {
            heading: 'Paper trading by default',
            paragraphs: [
                'Strategies shown on the site are evaluated with paper cash unless explicitly labelled otherwise. No real money is placed at risk by Benchify. Any “Live” mode refers to scheduled paper execution on current market data, not a brokerage account controlled by the site.',
            ],
        },
        {
            heading: 'Backtests are simulations',
            paragraphs: [
                'Point-in-time backtests are simplified models of historical conditions. They can suffer from look-ahead bias, survivorship bias, data gaps, delays, slippage, fees, and execution assumptions that differ from real markets. Past performance does not predict future results.',
            ],
        },
        {
            heading: 'Data limits',
            paragraphs: [
                'Market, news, and alternative data may be incomplete, delayed, or wrong. Benchify does not guarantee accuracy, completeness, or fitness for any purpose.',
            ],
        },
        {
            heading: 'Your responsibility',
            paragraphs: [
                'You are responsible for your own financial decisions and for complying with the laws and rules that apply to you. If you need investment advice, consult a qualified professional.',
            ],
        },
    ],
};
