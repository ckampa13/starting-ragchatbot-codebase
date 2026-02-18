# Frontend Changes — Prettier Code Quality Setup

## Summary

Added Prettier as the standard code formatter for all frontend files (`*.js`, `*.css`, `*.html`), applied consistent formatting throughout the existing files, and created a development script for running quality checks.

---

## New Files

### `package.json`
Root-level Node package manifest. Declares Prettier as a dev dependency and defines two npm scripts:
- `npm run format` — auto-formats all frontend files in place
- `npm run format:check` — checks formatting without modifying files (suitable for CI)

### `.prettierrc`
Prettier configuration. Key decisions:
| Option | Value | Reason |
|---|---|---|
| `tabWidth` | `2` | Standard Prettier default; consistent across JS/CSS/HTML |
| `singleQuote` | `true` | Matches existing JS style |
| `trailingComma` | `"es5"` | Modern JS best practice |
| `printWidth` | `80` | Standard line length |
| `endOfLine` | `"lf"` | Unix line endings for cross-platform consistency |

### `.prettierignore`
Scopes Prettier to the frontend only — ignores `backend/`, `docs/`, Python files, lock files, and Markdown.

### `scripts/check-frontend.sh`
Executable shell script for running frontend quality checks from the project root:
```bash
./scripts/check-frontend.sh          # check formatting (non-zero exit if issues found)
./scripts/check-frontend.sh --fix    # auto-format all frontend files
```

---

## Modified Files

### `frontend/script.js`
- Converted from 4-space to 2-space indentation throughout
- Removed double blank lines (extra blank line between `addEventListener` keypress block and suggested questions; between `setupEventListeners` and `sendMessage`)
- Standardized all string literals to single quotes
- Added trailing comma in object/array literals per `trailingComma: "es5"` config
- Formatted multi-line `fetch` body and chained `.map().join()` calls for readability

### `frontend/index.html`
- Converted from 4-space to 2-space indentation throughout
- Lowercased `<!DOCTYPE html>` → `<!doctype html>` (Prettier HTML standard)
- Added self-closing slash on void elements (`<meta />`, `<link />`, `<input />`)
- Broke long `<button data-question="...">` attributes across multiple lines for readability

### `frontend/style.css`
- Converted from 4-space to 2-space indentation throughout
- Expanded selector groups to one-per-line where Prettier requires (e.g. `*,\n*::before,\n*::after`)
- Separated single-line rule blocks (`h1 { font-size: 1.5rem; }`) into multi-line form
- Expanded `@keyframes bounce` `0%, 80%, 100%` selector to multi-line form
- Expanded `.no-courses, .loading, .error` selector group to multi-line form
- Removed trailing whitespace throughout

---

## Usage

### Install Prettier (first time only)
```bash
npm install
```

### Check formatting
```bash
npm run format:check
# or
./scripts/check-frontend.sh
```

### Auto-format
```bash
npm run format
# or
./scripts/check-frontend.sh --fix
```
