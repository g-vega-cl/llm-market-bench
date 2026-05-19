## [2026-05-19] design-system | Card primitive consolidation & "Today" feature migration

### Changes
- **Card Primitive**: Updated `packages/ui-design-system/src/primitives/Card.tsx` to default to `rounded-3xl` (32px radius), aligning with the "Bloomberg Terminal meets Wired" aesthetic defined in the wiki.
- **Enhanced Card Logic**: Added a first-class `isHoverable` prop that toggles the `.card-lift` utility (vertical translation and deeper shadow). Added `radius` and `padding` props for controlled flexibility. Enabled the `group` class on the container by default to allow children to react to card hover states (e.g., icons translating or gradients appearing).
- **Global Migration**: Replaced ~120 lines of redundant manual Tailwind CSS with the updated `Card` primitive across five major "Today" components:
    - `NewsletterFeed.tsx`: Manual `<article>` cards → `Card`.
    - `AgentInsights.tsx`: Manual memory cards with specialized gradients and accent borders → `Card`.
    - `MarketUpdates.tsx`: Manual ticker cards → `Card`.
    - `FutureCatalysts.tsx`: Manual event cards on the timeline → `Card`.
    - `MarketStatusHero.tsx`: Removed redundant `rounded-3xl` overrides.
- **Documentation**: Updated [[entities/design-system]] to reflect the new `Card` capabilities and the removal of stale sub-components.

### Files changed
- `packages/ui-design-system/src/primitives/Card.tsx`: +radius prop, +isHoverable prop, +group class, updated default radius to 3xl.
- `apps/web/src/features/today/components/NewsletterFeed.tsx`: Migrated to `Card`.
- `apps/web/src/features/today/components/AgentInsights.tsx`: Migrated to `Card`.
- `apps/web/src/features/today/components/MarketUpdates.tsx`: Migrated to `Card`.
- `apps/web/src/features/today/components/FutureCatalysts.tsx`: Migrated to `Card`.
- `apps/web/src/features/today/components/MarketStatusHero.tsx`: Removed redundant classes.
- `wiki/entities/design-system.md`: Updated `Card` documentation.

### Test results
Verified with `tsc --noEmit` and `pnpm biome check`. All 22 web tests remain green.

### Key decisions
- **Default to 3xl**: Chose `rounded-3xl` as the default for `Card` to match the brand identity, reducing boilerplate in feature components.
- **isHoverable Prop**: Abstracted the common `card-lift` + `hover:shadow-*` pattern into a single prop for better consistency.
- **Composition over Sub-components**: Focused on a highly flexible base `Card` rather than re-introducing `CardHeader`/`Body`/`Footer`, which were previously removed for being too restrictive.
