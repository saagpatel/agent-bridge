# Sanitization report — agent-bridge public release

**Date:** 2026-06-07
**Method:** Clean-room reimplementation, not copy-and-scrub. No file from the
private system (`bridge-db`) was copied. Every line was written fresh against the
*architecture*, which is the strongest possible guarantee that no personal byte
rode along.

## Automated leak scan (repo contents)

Ran `grep` across all `.py`/`.md`/`.toml` in the public repo for:

| Pattern class | Searched for | Result |
|---|---|---|
| Filesystem paths | `/Users/`, `/Users/d`, home paths | **none** (only `/abs/path/to/...` placeholders in docs) |
| Operator identity | real name, mailbox address | **none** |
| Network internals | the local control-plane port, `127.0.0.1` | **none** |
| Security internals | `hard_deny` / `hard-deny`, `personal-ops`, `ssh`/`.aws`/`gnupg` | **none** |
| Source system names | `bridge-db`, `personal-ops`, `GithubRepoAuditor`, `notion` | **none** |
| Private project names | sample of real portfolio project names | **none** |

## What was deliberately changed for de-personalization

| Private original | Public version | Why |
|---|---|---|
| Hardcoded callers `cc/codex/claude_ai/notion_os/personal_ops` in SQL `CHECK` constraints | Config-driven allowlist (`AGENT_BRIDGE_AGENTS`), default `claude-code,codex,claude-ai,human`, validated in the app layer | Removes the personal fleet identities from the schema; also a genuine design improvement |
| DB at a specific personal data path; markdown exported into a personal `~/.claude/projects/...` tree | XDG default + `AGENT_BRIDGE_DB_PATH` / `AGENT_BRIDGE_MARKDOWN_PATH` overrides | No machine-specific paths anywhere |
| `shipped_sync_receipts` + Notion-specific shipped-event lifecycle | **Dropped** from the public artifact | Coupled to a private downstream (Notion project registry); not generalizable, and revealing it adds nothing |
| `project_resolver` reading the auditor's `project-registry.json` | **Dropped** | Couples to a private sibling system |
| `cost_records` with the personal fleet's systems | **Dropped** from the artifact | Kept the artifact tight; cost is discussed in the narrative instead |
| Real project names, real cost numbers in prose | Generic examples; cost given as a **range** with subscription caveat | See "borderline" below |

## What was intentionally NOT published (security posture)

Per the operator guardrail "never publish security-posture details that weaken
the machine," the narrative describes the permission layer **conceptually only**:

- No exact deny-list contents, hook filenames, regex, or carve-out conditions.
- No specifics that would help an attacker bypass the guardrails.
- The *shape* (deny-by-default, enforcement outside the model, mode-appropriate
  trust) is shared because it's standard security culture, not an exploit map.

## Borderline calls — operator should confirm

1. **Cost figures.** The narrative and the X thread state agent usage runs
   **~$1,000–$3,500/month of API-equivalent compute under a flat subscription.**
   This is grounded in real usage data (rounded to a range, no exact monthly
   figures, no subscription tier named). It is still *your* financial information
   going public. **Decide if you're comfortable; edit or remove the range freely.**
   It appears in: `docs/one-person-ai-operating-system.md` (§"What it costs") and
   `build-in-public-thread.md` (post 7).
2. **Byline / copyright holder.** `LICENSE` says `agent-bridge contributors` and
   `pyproject.toml` author is `agent-bridge contributors`. Replace with your name
   if you want attribution. The narrative is written in anonymous first person —
   add your byline when you publish it (that's the point of the authority asset),
   but that's your explicit action, not baked in.
3. **Test/example names.** Fixtures use generic words (`recall`, `orbital`,
   `widget`, `proj`). These are common nouns, not identifiable portfolio
   projects — low risk, noted for completeness.
4. **The narrative reveals the *existence and shape* of your private system**
   (a fleet, schedulers, a permission layer, persistent memory, a portfolio of
   dozens of projects). That exposure is the *intended* authority play, but it is
   exposure. Re-read `docs/one-person-ai-operating-system.md` end-to-end with
   "am I comfortable with this being public and attributed to me?" in mind.

## Bottom line

The code artifact is clean — no personal data, verified by scan and by
construction. The only personal exposure is in the narrative, and it's
intentional and conceptual. Nothing here weakens the machine's defenses.
