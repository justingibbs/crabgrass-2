# Slice 11: WYSIWYG Canvas & AST Foundation

**Status:** Complete ✅
**Started:** 2026-01-03
**Completed:** 2026-01-03

## Decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| WYSIWYG Editor | ~~Milkdown~~ → **Quill** | Milkdown had CDN bundling issues; Quill works reliably |
| Library Loading | CDN (jsdelivr) | Global scripts, no import maps needed |
| Edit/Preview Toggle | Replaced with WYSIWYG | Single editing mode |
| AST Layer Scope | Minimal (parse + serialize) | Using marked.js lexer |
| Markdown Conversion | Turndown + marked | HTML↔Markdown conversion |

---

## Summary

Successfully implemented true WYSIWYG editing using Quill editor with Markdown conversion:

### What Works ✅
- **True WYSIWYG editing** - Rich text with live formatting
- **Toolbar formatting** - Bold, Italic, H1-H3, lists, blockquote, code
- **Keyboard shortcuts** - Cmd+B (bold), Cmd+I (italic), Cmd+S (save)
- **Markdown persistence** - Saves as Markdown via Turndown conversion
- **Content loading** - Markdown→HTML via marked.js
- **Dirty state tracking** - Orange indicator for unsaved changes
- **Save & Close** - Saves content and navigates back
- **AST utilities** - parseMarkdown, serializeAst using marked lexer
- **Fallback editor** - Textarea if Quill fails to load

### Architecture
```
Markdown (stored) ←→ HTML (edited in Quill)
     ↑                      ↓
  turndown              marked.js
     ↑                      ↓
   Save                   Load
```

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `frontend/index.html` | Modified | Added Quill, Turndown, marked CDN links |
| `frontend/js/lib/editor.js` | Created | Quill wrapper with MD↔HTML conversion |
| `frontend/js/lib/markdown-ast.js` | Created | AST utilities using marked lexer |
| `frontend/js/components/canvas-toolbar.js` | Created | Formatting toolbar for Quill |
| `frontend/js/concepts/canvas.js` | Modified | WYSIWYG integration with fallback |
| `frontend/styles/canvas.css` | Created | Quill + editor styling |

---

## CDN Dependencies

```html
<!-- Quill Editor -->
<link href="https://cdn.jsdelivr.net/npm/quill@2.0.2/dist/quill.snow.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/quill@2.0.2/dist/quill.js"></script>

<!-- Markdown conversion -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/turndown@7.1.2/dist/turndown.js"></script>
<script src="https://cdn.jsdelivr.net/npm/turndown-plugin-gfm@1.0.2/dist/turndown-plugin-gfm.js"></script>
```

---

## Toolbar Buttons

| Button | Format | Shortcut |
|--------|--------|----------|
| B | Bold | Cmd+B |
| I | Italic | Cmd+I |
| H1 | Header 1 | - |
| H2 | Header 2 | - |
| H3 | Header 3 | - |
| • | Bullet list | - |
| 1. | Numbered list | - |
| " | Blockquote | - |
| </> | Code block | - |

---

## Why Quill Instead of Milkdown

Milkdown (our first choice) failed due to esm.sh CDN version mismatch:
- `@milkdown/core@7.8.0` loaded internal deps at `7.17.3`
- Error: `Context "nodes" not found`
- The `?bundle` flag didn't resolve internal dependency versions
- Skypack.dev caused the page to hang completely

Quill advantages:
- Mature, battle-tested (10+ years)
- Reliable CDN distribution
- Simple API
- HTML-based (we convert to/from Markdown)

---

## Notes for Future

- Slice 12 can extend AST utilities for agent-canvas integration
- Consider adding link insertion button to toolbar
- Consider adding image upload support
- Build step (Vite) could enable Milkdown if preferred later

---

*Completed: 2026-01-03*
