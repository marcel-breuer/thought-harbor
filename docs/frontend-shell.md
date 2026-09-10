# Frontend shell and navigation

ThoughtHarbor routes render inside the shared `AppShell` component at
`apps/web/src/routes/+layout.svelte`. The shell owns navigation chrome and
keeps route components focused on their feature content.

## Navigation

Desktop layouts use a fixed sidebar with Dashboard, Inbox, Knowledge,
Meetings, Documents, Chat / Search, Tasks, and Settings. Meetings and Documents
have dedicated overview routes that link to their source-grounded detail views.
On narrow screens the sidebar becomes an accessible slide-out menu opened by
the menu button. Route links remain normal SvelteKit links so keyboard and
browser navigation work as expected.

The shell exposes a persistent search trigger. `Ctrl+K` and `⌘K` open the same
command palette from any route; Escape closes it. Navigation commands are
filtered as the user types, and a query that does not match a view offers the
Chat / Search route as the fallback.

Authenticated users are shown in the lower-left desktop sidebar and in the
mobile navigation drawer. Both account areas provide the session logout action.

## Styling and accessibility

The shell uses the existing `ink`, `harbor`, slate, and sky design tokens from
Tailwind. Interactive controls have explicit text sizing, visible focus rings,
semantic labels, and touch-friendly padding. Feature routes should not add a
second global sidebar or command palette; compose their content inside the
layout instead.

The navigation and command-palette flows are covered by
`apps/web/tests/e2e/navigation.spec.ts`. The E2E suite requires the configured
Playwright Chromium installation.
