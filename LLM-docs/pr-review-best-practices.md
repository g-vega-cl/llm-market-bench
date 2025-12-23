---
globs: *.ts,*.tsx,*.js,*.jsx
description: PR review hygiene items for JS/TS files
---
# PR Review Best Practices

Confirm each point during review:

- **Strip `console.log` calls**: Debug logging must not ship; replace with structured logging or remove before merge.
- **Allow but flag `any`**: `any` keeps momentum but call it out so the author can justify or plan a follow-up.
- **Prefer optional chaining (`?.`)**: Use `?.` instead of direct property access when data may be incomplete to avoid runtime crashes.
- **Avoid non-null assertion (`!`)**: Never use the `!` operator as it disables TypeScript's type safety and can cause runtime crashes. Instead use explicit conditional checks: `if (user.profile) { const profileName = user.profile.name; }` or optional chaining `?.` combined with nullish coalescing `??` for defaults: `const displayName = user.profile?.name ?? 'Guest'`.
- **Centralize styles in `.style.ts` files (for `./usm-native-app`)**: Move reusable styles out of components and into the designated style modules to stay consistent with the native app convention.
- **Remove assigned-but-unused variables**: Prevent dead code and confusion by deleting variables that never get read.
- **Delete unused imports**: Keep files lean and avoid bundling unreferenced modules by removing imports that are not used.
- **Remove dead code**: Eliminate unreachable functions, unused variables, and commented-out blocks—especially after feature removals or refactors. If you suspect code isn't used, add temporary logging or search references to confirm before deletion.
- **Check for unused branches**: Identify and remove code paths guarded by always-false conditions or deprecated feature flags.
- **Apply .filter before .map**: Filter arrays first to reduce processing overhead before applying expensive transformations, 
    - e.g., `items.filter(item => item.isValid).map(item => transform(item))` instead of `items.map(item => transform(item)).filter(item => item.isValid)`.
- **Default to const**: Use `const` for variable declarations by default; use `let` only when reassignment is necessary. Reassignment is not a good practice, so avoid reassigning.
- **Replace magic numbers**: Use named constants like `VOTING_AGE = 18` instead of literal values to improve code clarity and maintainability.
- **Remove redundant comments**: Delete comments that merely restate what the code already clearly expresses to reduce visual noise.
- **Prefer logical NOT (!)**: Use `!value` instead of `value === false` for cleaner, more idiomatic boolean checks that handle edge cases like null or undefined more predictably.
- **Follow React Hooks rules**: Call hooks only at the top level of function components; never inside callbacks, event handlers, loops, or conditionals.
- **Memoize callback props**: Use `useCallback` for functions passed as props to preserve `React.memo` benefits and prevent unnecessary re-renders.
- **Complete hook dependency arrays**: Include all referenced variables in hook dependency arrays to avoid stale closures and ensure correct updates.

# Advanced Refactoring (Tidy First)
- **Use guard clauses**: Place precondition checks at function start and return early when conditions fail to flatten control flow and highlight the happy path.
- **Extract helper functions**: Move self-contained code blocks into separate functions named after their purpose to reduce complexity and improve reusability.
- **Move declarations together**: Place variable declarations and their initialization together to improve readability and reduce mental overhead.
- **Use explaining variables**: Extract complex expressions into named variables that clarify the intent behind the computation.
- **Apply cohesion order**: Group related functions and code elements together to reduce the mental effort of understanding relationships.
- **Chunk statements**: Separate distinct logical phases within functions using blank lines to improve visual organization.
- **Avoid tight coupling**: Don't pass entire objects when you only need specific properties; prefer `login({ email }: { email: string })` with `userRepo.findByEmail(email)` over `login({ user }: { user: User })` that accesses `user.email` and database details directly.
- **Ensure high cohesion**: Each function should have one clear responsibility; split `processUserData()` that creates accounts, sends emails, and generates reports into focused `createAccount()`, `sendWelcomeEmail()`, and `generateReport()` functions.
- **Don't over-engineer**: If you only have one way to send emails, just write `sendEmail()` directly instead of creating `interface EmailSender` with one implementation—add abstractions only when you actually need multiple implementations.
- **Keep business logic out of UI components**: UI components should only handle presentation and user interaction; move calculations like `calculateTotal(cart)` and operations like `processPayment()` into separate functions or hooks that the component calls.
- **Make dependencies explicit**: Don't hide function dependencies in global variables or environment access; prefer `processPayment({ amount, currency, feeStrategy }: PaymentParams)` over reading from `process.env.DEFAULT_CURRENCY` or `this.config` inside the function.
- **One concept per variable**: Don't reuse variables for different concepts; avoid `let result: string | number` that stores `getUserId()` or `"guest"` depending on conditions—use separate `userId` and `guestLabel` variables instead.
- **Separate processing phases**: Split functions that mix parsing, processing, and formatting into distinct phases like `parseInput()`, `applyRules()`, and `formatOutput()` for better clarity and testability.
- **Wrap awkward interfaces**: When calling legacy code with unclear parameters, create a new function with a clean interface that passes through to the old implementation; prefer `processPayment({amount: number, currency: string})` over `legacyProcess({ a: amount, c: currency })`.
- **Organize files for readability**: Structure files with types/interfaces first, then main exports, then private implementation details last so readers understand the public API before diving into implementation.
- **Combine related operations**: Keep code that changes together close together; if two loops iterate the same list, consider combining them.
- **Reduce function length**: Aim for functions under 20 lines. If a function is longer, it likely does too much.
- **Inline single-use helper functions**: If a function is used only once and doesn't add significant clarity, inline it to reduce mental jumps.

# React Native
- **Check dark mode for UI changes**: Make sure Dark mode looks visually correct before comitting.
- **Design SVGs for theming**: Ensure SVG files are designed to support dynamic theming rather than using hardcoded colors to enable theme flexibility.