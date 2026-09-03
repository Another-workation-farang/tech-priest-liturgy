# ADEPTUS MECHANICUS COGITATOR STYLE GUIDE: COLOR & LAYOUT

**Protocol Reference:** AM-COG-UI-844.M41
**Clearance Level:** Omnis-Red-04 (Restricted)

This is the design protocol both HTML doc pages in this directory follow:
`liber-liturgiae.html` (the full language reference) and
`liturgy-data-slate.html` (the short data-slate overview). Text content is
never authored in these pages; `LIBER-LITURGIAE.md` stays the canonical
source, and the pages render its text. Capitalization of descriptive prose
is applied with CSS `text-transform: uppercase`, not by editing the text,
so the rendered pages and the canonical Markdown remain the same text.

---

## 1. Design specifications & palette

The visual layout of a Tech-Priest cogitator mimics archaic text-based
terminals, severe grid systems, and low-fidelity cathode-ray tube (CRT)
monitors.

### Core palette

| Element | Hex Code | Description | RGB |
| :--- | :--- | :--- | :--- |
| **Background** | `#050A07` | Deep Abyssal Green (Unlit Screen Phosphor) | `(5, 10, 7)` |
| **Primary Text** | `#39FF14` | High-Intensity Neon/Phosphor Green | `(57, 255, 20)` |
| **Secondary Text** | `#00AA33` | Diminished Olive Green (Comments, De-emphasized Data) | `(0, 170, 51)` |
| **Alert/Warning** | `#FF1E27` | Binary Red (Scrap-code Alerts, Machine Anger) | `(255, 30, 39)` |
| **System Highlight** | `#FFB300` | Cyber-Amber (Strings, Literals, Sacred Constants) | `(255, 179, 0)` |
| **Structural Borders** | `#1B4D22` | Dark Forest Green (Grid Lines, Layout Boxes) | `(27, 77, 34)` |

### Typography rules

- **Font-family:** `Courier New`, `Consolas`, `SF Mono`, or `OCR-A`.
- **Casing:** Code architecture follows Pythonic syntax
  (CamelCase/snake_case), but **all descriptive text, warnings, and error
  streams must be capitalized** to emphasize mechanical permanence.
- **Layout alignment:** Strict left-justified layout. No centered text
  block is permitted by the Machine Spirit.

### Local conventions (adopted by the two pages)

- Section rules are ASCII: `====` for the document frame, `----` between
  numbered `[I]`, `[II]`, ... sections, in the border green.
- Scriptural epigraphs render in secondary olive italic; error streams and
  curse output in binary red; inline code and string literals in
  cyber-amber.
- Table headers use secondary green so the grid reads as structure and the
  data reads as signal.
- Primary text carries a faint phosphor `text-shadow` glow; the blinking
  EOF cursor is disabled under `prefers-reduced-motion`.
- Single-theme by design: a CRT commits to its own world, so every color
  is painted explicitly and no light/dark media queries exist.

---

## 2. CSS implementation

Use these exact values to enforce the cogitator UI aesthetic.

```css
:root {
    --bg-color: #050A07;
    --text-primary: #39FF14;
    --text-secondary: #00AA33;
    --alert-color: #FF1E27;
    --highlight-color: #FFB300;
    --border-color: #1B4D22;
}

body {
    background-color: var(--bg-color);
    color: var(--text-primary);
    font-family: 'Courier New', Consolas, monospace;
    padding: 20px;
    line-height: 1.5;
}

/* Simulated scanline effect */
body::before {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 10;
    background-size: 100% 4px, 6px 100%;
    pointer-events: none;
}

.code-block {
    border: 1px solid var(--border-color);
    background-color: rgba(0, 0, 0, 0.5);
    color: var(--text-primary);
    padding: 15px;
    margin: 10px 0;
}

.comment { color: var(--text-secondary); }
.string  { color: var(--highlight-color); }
.warning { color: var(--alert-color); border: 2px solid var(--alert-color); }
```
