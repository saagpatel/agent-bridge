# Release checklist — agent-bridge

Everything is staged locally. Nothing has been pushed, posted, or shared. These
are the steps **you** take to publish, in order.

## 0. Final review (do this first)

- [ ] Read `SANITIZATION-REPORT.md` and resolve the 4 borderline calls.
- [ ] Re-read `docs/one-person-ai-operating-system.md` for comfort with public,
      attributed exposure. Edit/remove the cost range if you want.
- [ ] Decide the byline/copyright name; update `LICENSE` + `pyproject.toml`
      `authors` if you want attribution instead of "agent-bridge contributors".

## 1. Repo prep (local)

- [ ] `cd /Users/d/Projects/agent-bridge`
- [ ] Branch is `feat/initial-release` with one commit. Review the diff:
      `git show --stat HEAD`
- [ ] Re-run the gate: `uv sync --extra dev && uv run pytest -q && uv run ruff check`
- [ ] Merge to `main` locally (your call — the agent does not push to main):
      `git checkout -b main 2>/dev/null || git checkout main; git merge --ff-only feat/initial-release`

## 2. Create the GitHub repo (your action)

- [ ] `gh repo create agent-bridge --public --source=. --remote=origin --description "A SQLite-backed MCP server that gives your AI coding agents a shared memory bus."`
- [ ] `git push -u origin main`
- [ ] Add repo topics: `mcp`, `ai-agents`, `claude`, `sqlite`, `fts5`,
      `coordination`, `model-context-protocol`.
- [ ] Replace `<you>` placeholders in `README.md` and `docs/` with the real
      GitHub URL, commit, push.

## 3. Publish the narrative (the authority asset)

- [ ] The narrative lives in the repo (`docs/one-person-ai-operating-system.md`) —
      already public once the repo is. Optionally also post it as a blog/Substack
      with your byline for reach + SEO/GEO. Add the canonical link back to the repo.

## 4. Distribution (staged drafts in this folder)

- [ ] **Show HN** — use `show-hn.md`. Post during a US-morning weekday window.
      Paste the "first comment" immediately after submitting.
- [ ] **Build-in-public** — use `build-in-public-thread.md` (X thread or LinkedIn
      post). Put the repo link in a reply/comment, not the first post, on X.
- [ ] **Awesome lists** — use `awesome-list-entry.md`. Open PRs to the MCP-server
      lists first; follow each list's CONTRIBUTING format.

## 5. Post-launch hygiene

- [ ] Watch the HN thread for the first 2 hours and answer questions (prep is in
      `show-hn.md`).
- [ ] Tag a release: `gh release create v0.1.0 --generate-notes`.
- [ ] If it gets traction, add a CONTRIBUTING.md and a couple of GitHub issues
      labeled `good first issue` (e.g. an HTTP transport, a `cost_records` table).

## Guardrail reminder

The agent created everything locally and pushed nothing. Steps 2–4 are
outward-facing and are yours to execute. The code artifact is sanitized and
verified; the only judgment calls left are the borderline items in the
sanitization report.
