#!/usr/bin/env node
// jev-route CLI — lets any coding agent get a JEV decision from a shell call.
// Usage:
//   echo '{"request":"...","signals":{...},"recentFailures":2}' | jev-route
//   jev-route --request "cargo E0433" --signal stack=rust --failures 2
// Output: single-line JSON decision (stdout). Errors go to stderr, exit 1.
// On failure the agent should fall back to its rule-based routing table.

import { JevRouter, JevClient } from './index.js';

const raw = await readStdin();
let ctx = {};
if (raw.trim()) {
  try { ctx = JSON.parse(raw); } catch { fatal('stdin is not valid JSON'); }
}
// CLI flags override / fill stdin fields
const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--request') ctx.request = args[++i];
  else if (args[i] === '--failures') ctx.recentFailures = Number(args[++i]);
  else if (args[i] === '--signal') {
    const [k, ...v] = args[++i].split('=');
    ctx.signals = { ...ctx.signals, [k]: v.join('=') };
  }
}
if (!ctx.request) fatal('missing request (stdin JSON or --request)');

try {
  const router = new JevRouter();
  // ctx.questions (optional): raw mode - ask custom JEV primitives directly,
  // bypassing the built-in 5-question decide(). Returns { model, answers, usage }.
  const d = ctx.questions
    ? await new JevClient().evaluate(
        { request: ctx.request, ...(ctx.signals ? { signals: ctx.signals } : {}) },
        ctx.questions,
      )
    : await router.decide(ctx);
  process.stdout.write(JSON.stringify(d) + '\n');
} catch (err) {
  fatal(`jev decision failed: ${err.message} — fall back to rule table`);
}

async function readStdin() {
  if (process.stdin.isTTY) return '';
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

function fatal(msg) {
  process.stderr.write(`jev-route: ${msg}\n`);
  process.exit(1);
}
