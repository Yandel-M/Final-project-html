<!-- Copilot / AI agent instructions for the Final-project-html repo -->
# Copilot instructions for this repository

This file gives concise, repository-specific guidance so AI coding agents can be productive quickly.

Project summary
- **Type:** Small Flask-based blog web app using file-based persistence (`data.json`).
- **Entry point:** `app.py` — a plain Flask app with `app.run(debug=True)`; run with `python app.py`.
- **Templates:** Jinja templates live in `templates/` (e.g. `Homepage.html`, `Posts.html`, `Create-Posts.html`). Note: file name casing in templates may differ (Windows is case-insensitive); ensure exact names on case-sensitive hosts.
- **Static assets:** `static/styles.css` and `static/script.js`.

Key architectural notes (why things are structured this way)
- The app stores posts in a JSON file (`data.json`) and exposes simple CRUD-like behavior via routes in `app.py`. This is deliberate to avoid a database for this small project.
- `app.py` contains the full controller logic: loading/saving data (`load_data`, `save_data`), session-based likes (`session['liked_posts']`), and form handlers for creating posts and comments.

Developer workflows / run & debug
- Install dependencies: `pip install flask` (virtualenv recommended).
- Run locally from the repo root: `python app.py`. App runs with `debug=True` so changes reload automatically.
- To reproduce a typical test scenario: ensure `data.json` exists (sample content is already present). If `data.json` is missing or empty, the app creates/initializes `blog_posts` in memory.

Project-specific conventions and gotchas
- Template filenames: The code calls `render_template('homepage.html')`, `render_template('posts.html')`, `render_template('create-posts.html')`, etc., while the repository contains `Homepage.html`, `Posts.html`, `Create-Posts.html`. On Windows this works; on Linux/macOS (case-sensitive), rename templates to the exact lowercase names or update `app.py` to match.
- Data file path: `DATA_FILE = 'data.json'` is relative to where `app.py` is started. Always run commands from the repo root to avoid path problems.
- Session and secrets: `app.secret_key` is hard-coded (`super_secret_blog_key_123`). Replace this for production and when writing tests that require session control.
- Authentication: Minimal, hard-coded admin creds (`admin` / `password`) used only for demo login flow in `login()`.
- Concurrency: `save_data()` overwrites `data.json` and there's no locking — concurrent writes may cause data loss. Avoid parallel processes writing to `data.json` in tests.

Important files to inspect for changes or behavior to preserve
- `app.py` — routes, business logic, persistence helpers, session usage.
- `data.json` — canonical example data and format for posts/comments. Each post has `id`, `title`, `author`, `content`, `timestamp`, `likes`, `comments`.
- `templates/Posts.html` — shows how likes and comments are wired (forms POST to `/like-post/<id>` and `/add-comment/<id>`). Use this as a pattern when adding UI features.
- `templates/Homepage.html` — shows `latest_posts` usage and `truncate` filter example.

Examples (quick recipes)
- Create a post (manual curl example):
  - The form in `create-posts.html` POSTs to `/create-posts`. To simulate a POST, use an HTTP client or run the UI.
- Like a post (example curl):
  - `curl -X POST http://127.0.0.1:5000/like-post/1` (the app relies on the session cookie; automated tests should set an appropriate cookie or mock session).

Editing guidance for agents
- Prefer modifying `app.py` functions in-place and keep behavior backwards-compatible with `data.json` format.
- When adding routes or API endpoints, follow existing naming patterns (`/create-posts`, `/posts`, `/like-post/<id>`, `/add-comment/<id>`).
- If changing template names or locations, update every `render_template()` call accordingly.

Testing and validation pointers
- There are no automated tests in this repo. For quick checks:
  - Run `python app.py` and visit `http://127.0.0.1:5000/` to manually verify behavior.
  - Inspect `data.json` after creating posts/likes/comments to ensure `save_data()` persisted changes.

Limitations and non-goals
- This repo is intentionally simple: no DB, no blueprints, no API authentication. Avoid adding heavy infra unless explicitly requested.

If something is unclear
- Ask for clarifications about desired persistence (file vs DB), template renaming preferences (linux compatibility), or whether to add tests. Also confirm if secret key rotation or credential changes are allowed.

— End of instructions —
