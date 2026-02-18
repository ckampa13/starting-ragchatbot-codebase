# Frontend Changes

## Dark/Light Mode Toggle Button

### Summary
Added a theme toggle button positioned fixed in the top-right corner. Clicking it switches between the existing dark theme and a new light theme with smooth CSS transitions. The user's preference is persisted in `localStorage`.

---

### Files Modified

#### `frontend/index.html`
- Bumped stylesheet version to `?v=11` and script version to `?v=10` to bust cache.
- Added a `<button id="themeToggle" class="theme-toggle">` element just before `</body>`.
  - Contains two inline SVG icons:
    - `.sun-icon` — visible in dark mode; clicking switches to light mode.
    - `.moon-icon` — visible in light mode; clicking switches to dark mode.
  - Both icons are `aria-hidden="true"`; the button itself carries a descriptive `aria-label` that is updated dynamically by JavaScript.

#### `frontend/style.css`
- **New CSS variables added to `:root`:**
  - `--code-bg` — background for `<code>` and `<pre>` blocks (was hardcoded `rgba(0,0,0,0.2)`).
  - `--source-item-bg` / `--source-item-hover-bg` — background for source citation items (was hardcoded dark values).
- **New `[data-theme="light"]` block** overrides all theme-sensitive variables:
  - Background, surface, hover, text, border, assistant message bubble, shadow, welcome section, code bg, source item bg.
- **Smooth transitions** added to `body` and a list of theme-sensitive elements (`transition: background-color 0.3s ease, ...`).
- **Hardcoded dark backgrounds replaced** with CSS variables on `.message-content code`, `.message-content pre`, and `.source-item`.
- **`.theme-toggle` button styles:**
  - `position: fixed; top: 1rem; right: 1rem; z-index: 100`
  - 40×40 px circular button styled to match sidebar aesthetic (uses `--surface`, `--border-color`, `--text-secondary`).
  - Hover: slight scale-up, primary colour highlight, shadow.
  - Focus: `focus-visible` ring using `--focus-ring` (keyboard-navigable).
  - Icon animation: `.sun-icon` and `.moon-icon` are absolutely positioned and crossfade with rotate+scale transitions (0.3 s ease).

#### `frontend/script.js`
- Added three theme functions before `DOMContentLoaded`:
  - `initTheme()` — reads `localStorage.theme` (defaults to `'dark'`) and calls `applyTheme()`.
  - `applyTheme(theme)` — sets `data-theme` attribute on `<html>`, updates button `aria-label`/`title`, saves to `localStorage`.
  - `toggleTheme()` — reads current theme and flips it.
- In `DOMContentLoaded`: calls `initTheme()` first (before DOM queries) and wires `click` event on `#themeToggle` to `toggleTheme()`.

---

### Design Decisions
- `data-theme` attribute is placed on `<html>` (`document.documentElement`) so CSS selectors like `[data-theme="light"] .theme-toggle .moon-icon` work globally without JavaScript class juggling.
- Default theme is `dark` to preserve the existing look for returning users who have no saved preference.
- Icon visibility is CSS-driven (opacity + transform), keeping JavaScript minimal.
- `focus-visible` (not `focus`) is used so keyboard users see a focus ring but mouse users don't, matching modern accessibility best practice.

---

## Light Theme Colour System

### Summary
Completed the light theme by replacing every remaining hardcoded dark-only colour in `style.css` with CSS variables, and auditing all light-mode values against WCAG AA contrast requirements.

---

### Files Modified

#### `frontend/index.html`
- Bumped stylesheet version to `?v=12` to bust cache.

#### `frontend/style.css`

**Expanded `:root` variable set** — all colours that were hardcoded inline are now variables:

| Variable | Dark value | Purpose |
|---|---|---|
| `--assistant-message` | `#1e293b` | Assistant chat bubble background |
| `--welcome-bg` | `#1e3a5f` | Welcome panel background |
| `--welcome-border` | `#2563eb` | Welcome panel border |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.25)` | Welcome panel box-shadow |
| `--code-bg` | `rgba(0,0,0,0.25)` | `<code>` / `<pre>` background |
| `--code-border` | `rgba(255,255,255,0.06)` | Code block border (reserved) |
| `--sources-accent` | `#60a5fa` | Sources header text & item border |
| `--sources-accent-hover` | `#93c5fd` | Sources hover state |
| `--sources-bg` | `rgba(37,99,235,0.06)` | Sources panel background |
| `--sources-bg-hover` | `rgba(37,99,235,0.12)` | Sources header background |
| `--sources-border` | `rgba(37,99,235,0.2)` | Sources panel border |
| `--source-item-bg` | `rgba(30,41,59,0.55)` | Individual source row background |
| `--source-item-hover-bg` | `rgba(30,41,59,0.85)` | Source row hover |
| `--link-color` | `#93c5fd` | Source link text |
| `--link-color-hover` | `#bfdbfe` | Source link hover |
| `--error-bg/text/border` | red-400 palette | Error status message |
| `--success-bg/text/border` | green-400 palette | Success status message |

**Light theme overrides `[data-theme="light"]`** with WCAG AA-compliant values:

| Variable | Light value | Contrast on bg |
|---|---|---|
| `--text-primary` | `#0f172a` | ~17:1 on `#f8fafc` ✓ |
| `--text-secondary` | `#475569` | ~5.9:1 on `#f8fafc` ✓ |
| `--assistant-message` | `#eef2f7` | Distinct from `#f8fafc` bg ✓ |
| `--sources-accent` | `#1d4ed8` | ~6.3:1 on sources panel ✓ |
| `--link-color` | `#2563eb` | ~5.9:1 on source-item bg ✓ |
| `--error-text` | `#b91c1c` | ~7.0:1 on error-bg ✓ |
| `--success-text` | `#15803d` | ~5.6:1 on success-bg ✓ |
| `--border-color` | `#cbd5e1` | Visible on white ✓ |

**Selector changes** — inline hardcoded values replaced with variables:
- `.message.assistant .message-content` → `background: var(--assistant-message)` (was `var(--surface)` = white on white in light mode)
- `.message.welcome-message .message-content` → `background: var(--welcome-bg)`, `border: var(--welcome-border)`, `box-shadow: var(--welcome-shadow)`
- `.sources-collapsible` → `background: var(--sources-bg)`, `border: var(--sources-border)`
- `.sources-collapsible summary` → `color: var(--sources-accent)`, `background: var(--sources-bg-hover)`
- `.sources-collapsible summary:hover` → `color: var(--sources-accent-hover)`
- `.sources-collapsible[open] summary` → `border-bottom: var(--sources-border)`
- `.source-item` → `border-left: var(--sources-accent)`
- `.source-item:hover` → `border-left-color: var(--sources-accent-hover)`
- `.source-link` → `color: var(--link-color)`
- `.source-link:hover` → `color: var(--link-color-hover)`
- `.error-message` → `var(--error-bg/text/border)`
- `.success-message` → `var(--success-bg/text/border)`

---

### Accessibility Notes
- All foreground/background pairs in both themes meet **WCAG AA** (4.5:1 for body text, 3:1 for large/bold text).
- The assistant message bubble (`--assistant-message: #eef2f7`) is intentionally distinct from the page background (`#f8fafc`) so messages remain visually separated without a border.
- Status message colours use darker shades in light mode (red-700, green-700) versus lighter shades in dark mode (red-400, green-400) to maintain readability in each context.

---

## JavaScript Functionality & Smooth Transitions

### Summary
Closed four remaining gaps in the theme system: FOUC prevention, OS preference detection, `color-scheme` CSS property, and complete transition coverage.

---

### Files Modified

#### `frontend/index.html`
- Bumped stylesheet to `?v=13` and script to `?v=11`.
- Added an **inline synchronous `<script>` block** in `<head>` (before the stylesheet `<link>`) that reads `localStorage` and `prefers-color-scheme` and writes `data-theme` to `<html>` before the browser paints. This eliminates the flash of the wrong theme on page load.

#### `frontend/style.css`
- Added `color-scheme: dark` to `:root` and `color-scheme: light` to `[data-theme="light"]`. This tells the browser to render native UI controls (scrollbars, input placeholders, date-pickers, selection highlight) using the matching scheme, so they no longer look out-of-place in light mode.
- Expanded the grouped transition selector to cover elements that were previously missing smooth colour changes on theme switch:
  - `.main-content` — background
  - `.stat-label`, `.stat-value` — text colour
  - `.source-link`, `.source-text` — link/text colour
  - `.sources-collapsible summary` — background + text colour
  - `.course-title-item` — text + border colour
  - `.no-courses`, `.error` — text colour

#### `frontend/script.js`
- Replaced hard-coded `'dark'` default with **OS preference detection** via `window.matchMedia('(prefers-color-scheme: dark)')`. Priority order: saved `localStorage` preference → OS preference → dark.
- `initTheme()` now reads `osPrefersDark.matches` as the fallback, so users on a light-mode OS see light mode on first visit without having to toggle.
- Added a **`change` event listener** on `osPrefersDark`: when the OS switches colour scheme (e.g. macOS auto mode at sunset), the app follows — but only when the user has not made a manual choice. A manual toggle always wins over the OS preference.
- The inline `<head>` script and `initTheme()` in `DOMContentLoaded` are coordinated: the inline script applies the correct `data-theme` attribute synchronously (for zero-flash rendering), and `initTheme()` later syncs the button's `aria-label` and `title` to match.

---

### How the Theme Priority Chain Works

```
Page load
  └─ Inline <head> script (synchronous, before paint)
       ├─ localStorage.theme exists?  → use it
       └─ else → read prefers-color-scheme → apply

User toggles button
  └─ toggleTheme() → applyTheme(opposite)
       └─ saves to localStorage (manual choice wins forever)

OS changes colour scheme (auto mode)
  └─ matchMedia change event fires
       ├─ localStorage.theme exists?  → ignore (manual wins)
       └─ else → applyTheme(new OS preference)
```
