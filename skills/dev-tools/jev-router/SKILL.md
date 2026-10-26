---
name: jev-router
description: Use when making routing decisions in the agent loop — choosing which skill to load, deciding whether to search the knowledge base, whether to do web research, whether to ask the user a clarifying question, or detecting stuck loops. Calls the JEV Decision API via the jev-route CLI for calibrated, confidence-gated decisions instead of guessing.
---

# JEV Decision Router

Replace "rule-table guessing" with one calibrated JEV call. The CLI takes the
agent's context as JSON and returns a decision with confidence tiers.

## When to call

Call `jev-route` at these decision points:

1. **Skill selection** — before loading a skill, when multiple could match or none obviously matches
2. **Knowledge-base trigger** — before searching a project knowledge base / vault / MCP memory, to avoid guaranteed-empty searches
3. **Web research** — before web_search/web_fetch, when the answer might be local
4. **Stuck detection** — after 2+ consecutive failed searches/commands, before retrying again

Do NOT call it for: trivial one-liner actions, tool choice between obviously
different tools (read_file vs bash), or anything with an explicit user instruction.

## How to call

```bash
echo '<ctx-json>' | jev-route
# or if not installed globally:
echo '<ctx-json>' | node "C:/Users/49059/.atomcode/skills/jev-router/src/cli.js"
```

`<ctx-json>` fields:

| field | type | required | meaning |
|-------|------|----------|---------|
| `request` | string | yes | the user's raw message (trimmed) |
| `signals` | object | no | e.g. `{"has_error_text": true, "error_fingerprint": "cargo E0433", "stack": "rust"}` |
| `recentFailures` | number | no | consecutive failed rounds — adds stuck detection |

Requires `TYPESAFE_API_KEY` in the environment. Requires Node >= 18.

## First-time setup (API key)

The CLI needs a TypeSafe API key. Without it every call fails with
`Missing API key` and falls back to the rule table — useful to know on first use.

1. Get a key from `console.typesafe.ai`
2. Set it as a persistent environment variable:
   - bash: add `export TYPESAFE_API_KEY="apikey_..."` to `~/.bashrc`
   - Windows: `setx TYPESAFE_API_KEY "apikey_..."` (takes effect in NEW terminals)
3. Verify: `echo '{"request":"ping"}' | node <cli path from above>` → a JSON
   decision object on stdout means the key works

Hygiene: never hardcode the key or print/log it; pass it via the environment only.

## Reading the output

Single-line JSON on stdout:

```json
{
  "skill":       {"choice": "systematic-debugging", "confidence": 1.0, "tier": "auto", "action": "load_skill"},
  "clarification": {"probability": 0.56, "tier": "proceed", "action": null},
  "kbSearch":    {"probability": 0.82, "tier": "proceed", "action": "search_knowledge_base"},
  "webResearch": {"probability_web_needed": 0.27, "local_score": 1.54, "tier": "auto", "action": "skip_web"},
  "stuck":       {"probability": 0.17, "tier": "ask", "action": null}
}
```

Tier semantics — follow the action, never override it:

- `tier: "auto"` → execute the action immediately
- `tier: "proceed"` → execute, but mention the probability in your reasoning/log
- `tier: "ask"` → **do not act**. For `skill`: present the top-2 candidates from
  `probabilities` and ask the user. For `kbSearch`/`webResearch`: skip it.
  For `stuck`: stop and report what you tried.

`action: null` means "do nothing for this dimension".

## Raw mode (custom questions)

Add a `questions` field to the stdin JSON to bypass the built-in 5-question
decide() and ask custom JEV primitives directly (e.g. turn your own rule
table's criteria text into a `choice` question):

```bash
echo '{"request":"...","questions":{"grade":{"type":"choice",
  "instructions":"...","criteria":{"A":"when...","B":"when..."}}}}' | node <cli path>
```

Returns `{model, answers, usage}` — answers are NOT tier-gated; apply your own
thresholds (e.g. 0.85/0.5). Omit `questions` for the default gated output.

## Failure handling

Non-zero exit + stderr message means JEV was unreachable or the key is invalid.
**Fall back to the existing rule-based routing table** (e.g. the error-fingerprint
→ skill arbitration table) and continue. Never block the user's task on JEV.

## Cost & hygiene

- One call ≈ $0.0001 (input $0.042/1M tokens, output free) — batch freely
- The `request` and `signals` you send go to the TypeSafe API: do not include
  secrets, tokens, or credentials in them
- Never print or log the API key
