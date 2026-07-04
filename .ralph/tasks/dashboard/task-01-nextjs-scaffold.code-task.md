---
status: pending
created: 2026-07-04
---
# Task: Next.js Scaffold + Design Tokens + Sidebar Shell

## Description
Stand up the dashboard app itself: a Next.js 14 (App Router) project at
`dashboard/` with Tailwind, shadcn/ui, the design system tokens from the spec,
and the persistent sidebar nav shell (empty pages for now — content comes in
later tasks).

## Background
This is the first task of the lien-prospecting dashboard feature: a local,
tool-packed web UI for the existing CLI/cron lien-prospecting pipeline. No
prior task exists; this establishes the app every later task builds on.

## Reference Documentation
**Required:**
- Design: `.ralph/specs/dashboard/design.md` (full document, especially
  "Architecture", "Design System", and "Pages & Layout")

**Note:** Read the design document before beginning implementation.

## Technical Requirements
1. Scaffold a Next.js 14 App Router + TypeScript project at `dashboard/`
   (sibling to `scripts/`, not nested inside it).
2. Install and configure Tailwind CSS and shadcn/ui.
3. Define the design system tokens from the spec as CSS variables /
   Tailwind theme extension: colors (`--color-primary: #1E40AF`, etc. — full
   list in the spec's "Design System" section), and load Fira Code (data/
   numbers) + Fira Sans (UI text) from Google Fonts.
4. Build the root layout (`app/layout.tsx`) with:
   - A persistent left sidebar with 4 nav items: Overview (`/`), Liens
     (`/liens`), Runs (`/runs`), Counties (`/counties`) — each a placeholder
     page for now (later tasks fill them in).
   - A slot/mount point for the chat panel (task 7 implements the panel
     itself; this task just reserves the layout space so later tasks don't
     have to restructure the shell).
   - Dark mode support wired at the token level (not necessarily a visible
     toggle yet — that's catalog #37, backlog).
5. Add `dashboard/node_modules/`, `dashboard/.next/`, and `dashboard/.data/`
   (the future `runs.jsonl` location, per the spec) to `.gitignore`.
6. `dashboard/README.md` (or a section in the root README) documenting how to
   run it: `cd dashboard && npm install && npm run dev`.

## Dependencies
None — this is the first task.

## Implementation Approach
1. `npx create-next-app@latest dashboard --typescript --tailwind --app` (or
   equivalent), then add shadcn/ui via its CLI init.
2. Wire the token values and fonts into `tailwind.config.ts` / `globals.css`.
3. Build the sidebar shell + 4 placeholder routes + chat panel mount point.
4. Update `.gitignore` and add run instructions.
5. Verify `npm run dev` starts cleanly and all 4 nav links render their
   placeholder pages without errors.

## Acceptance Criteria

1. **App boots cleanly**
   - Given `dashboard/` is scaffolded
   - When running `npm install && npm run dev` from `dashboard/`
   - Then the dev server starts without errors and `/` renders

2. **Sidebar nav present on every page**
   - Given the app is running
   - When visiting `/`, `/liens`, `/runs`, `/counties`
   - Then the same 4-item sidebar renders on all of them, with the current
     page visually indicated as active

3. **Design tokens applied, not hardcoded**
   - Given any rendered page
   - When inspecting styles
   - Then colors/fonts come from the spec's token values (via Tailwind theme
     / CSS variables), not raw hex/font-family strings scattered in
     components

4. **Runtime state gitignored**
   - Given a fresh `npm install` and `npm run dev`
   - When running `git status`
   - Then `dashboard/node_modules/`, `dashboard/.next/`, and `dashboard/.data/`
     do not appear as trackable/stageable changes

## Metadata
- **Complexity**: Medium
- **Labels**: scaffold, nextjs, design-system, dashboard
- **Required Skills**: Next.js, Tailwind, shadcn/ui
