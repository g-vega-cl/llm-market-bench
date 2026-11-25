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
                'Usage data: page views, clicks, feature interactions, and errors captured by PostHog. Session replay is enabled with text inputs masked. Browser console logs and unhandled errors are also captured for debugging.',
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
            ],
        },
        {
            heading: 'Cookies and local storage',
            paragraphs: [
                'Benchify uses browser storage for three purposes: keeping you signed in (Supabase auth cookies/storage), remembering product state such as in-progress drafts, and maintaining PostHog analytics sessions. We do not use advertising cookies or sell data to advertisers.',
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
                'You can request access to, correction of, or deletion of your account and product data by emailing privacy@benchify.dev. We will verify the request and respond within a reasonable period. You can also delete browser-only drafts by clearing site data, and you can limit analytics by blocking third-party scripts in your browser. Deleting your account does not erase aggregate usage data that can no longer be linked to you.',
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
            paragraphs: ['Questions about privacy or data deletion: privacy@benchify.dev.'],
        },
    ],
};

export const termsOfService: LegalDocument = {
    title: 'Terms of Service',
    updated: '2026-11-25',
    intro: 'These terms govern your use of benchify.dev. By creating an account or using the site, you agree to them. Benchify is a beta product, so expect rough edges and changing behavior.',
    sections: [
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
            heading: 'Changes and termination',
            paragraphs: [
                'We may suspend or terminate accounts that violate these terms or abuse the service. We may update these terms as the product evolves; the “Updated” date shows the current version. Continued use after a change means you accept the revised terms.',
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
    intro: 'Benchify is an educational research and benchmarking tool. Nothing on this site is financial, investment, legal, or tax advice.',
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
