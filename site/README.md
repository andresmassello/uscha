# uscha.dev — site

Static site for the Uscha methodology. No build step, no framework.

## Structure

| Path | What it is |
|---|---|
| `index.html` | Landing page (English — site root) |
| `es/index.html` | Landing page (Spanish twin) |
| `why/index.html` | Essay: open loop vs. measured graph (English) |
| `es/why/index.html` | Essay (Spanish twin) |
| `assets/uscha.css` | Shared stylesheet (dark control-room theme) |
| `llms.txt` | LLM-facing site summary (llmstxt.org format) — update version/claims on release |
| `docs/` | **Generated** — copies of the canonical decks in `../docs/`. Never edit by hand. |

## Rules

1. **`site/docs/` is build output.** The canonical sources are in `../docs/`.
   To update, edit the source docs and run `bash site/sync-docs.sh`.
2. **The twins rule applies**: every English page has its Spanish twin
   (`/x` ↔ `/es/x`). An edit in one requires the equivalent edit in the other.
3. **Truth-pass applies**: the landing claims nothing the engine does not do.
   Version numbers come from `uscha-kit/VERSION` — not from older decks.

## Local preview

All paths are relative, so double-clicking any `index.html` works directly
(`file://`). A local server also works:

```bash
python -m http.server 8788 --directory site
```

## Deploy (Cloudflare Pages)

- Build command: `bash site/sync-docs.sh` (or none if `site/docs/` is committed fresh)
- Output directory: `site`
