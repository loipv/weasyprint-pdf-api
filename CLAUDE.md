# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

WeasyPrint needs system libraries (pango, fonts) that aren't pip-installable, so development normally runs in Docker:

```bash
make build         # build the Docker image
make server        # run the API on http://localhost:8000
make dev-console   # shell into the container with ./app mounted for live editing
```

Tests (requires `pip install httpx pytest` plus `requirements.txt`):

```bash
cd app && pytest                                  # CI runs it this way
cd app && pytest test_main.py::test_default_file_name   # single test
```

The server port is set by the `PORT` env var (default 8000). There is no linter configured.

## Architecture

A single-endpoint FastAPI service that renders HTML to PDF with WeasyPrint:

- `app/main.py` — the entire API. `POST /pdfs` takes a `PrintPdfRequest` (`html` required; optional `filename`, default `"weasyprint"`, whitespace-stripped with fallback to the default when blank). The endpoint is deliberately a sync `def` so FastAPI runs the CPU-bound `HTML(string=...).write_pdf()` in the threadpool — an `async def` here would block the event loop and stall ALL concurrent requests during heavy renders (regression-tested by `test_heavy_render_does_not_block_the_event_loop`). The `Content-Disposition` header embeds the filename twice (`name=` and `filename=`) with `.pdf` appended.
- `app/test_main.py` — TestClient tests asserting the exact `Content-Disposition`/`Content-Type` headers for default, blank, and padded filenames. Changing header construction breaks these.

## Deployment

- Multi-stage `Dockerfile` on `python:3.14-alpine`: a builder stage compiles the venv; the runtime stage installs pango, libffi/libjpeg/zlib, and DejaVu/Noto/CJK fonts (installed fonts affect PDF output) and runs as non-root `appuser`.
- `.github/workflows/docker-publish.yml`: PRs and non-tag pushes run pytest (Python 3.11); pushes to `main` publish `latest` and `v*` tags publish versioned images to ghcr.io.
- Dependencies are exact-pinned in `requirements.txt`; Dependabot opens PRs to bump them.
