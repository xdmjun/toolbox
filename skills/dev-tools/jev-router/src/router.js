// jev-router/src/router.js — decision layer for coding agents.
// Turns agent context into ONE batched JEV call, then applies a 3-tier
// confidence gate: auto (>0.85) / proceed-with-note (0.5–0.85) / ask-user (<0.5).

import { JevClient, JevError } from './client.js';

export const TIERS = { AUTO: 'auto', PROCEED: 'proceed', ASK: 'ask' };

const DEFAULT_SKILLS = {
  none: 'Ordinary task, no special skill needed',
  'systematic-debugging': 'Bug report, debugging or error fix, especially with a concrete error message or stack trace',
  'brainstorming': 'Creative work: new feature or component whose requirements are not yet defined',
  'writing-plans': 'Multi-file implementation with an agreed approach or spec',
  'architect-thinking': 'Architecture design, technology selection, refactoring strategy',
};

export class JevRouter {
  constructor({ client, autoThreshold = 0.85, askThreshold = 0.5, skills = DEFAULT_SKILLS } = {}) {
    this.client = client ?? new JevClient();
    this.autoThreshold = autoThreshold;
    this.askThreshold = askThreshold;
    this.skills = skills;
  }

  // ctx: {
  //   request: string            — the user's raw message
  //   signals?: object           — e.g. { has_error_text, error_fingerprint, stack }
  //   recentFailures?: number    — consecutive failed searches/commands (stuck detection)
  //   skills?: object            — override the skill criteria map for this call
  // }
  // Returns one decision object with per-question answers + gated actions.
  async decide(ctx, { signal } = {}) {
    const questions = {
      skill: {
        type: 'choice',
        instructions: {
          user_request: ctx.request,
          ...(ctx.signals ? { signals: ctx.signals } : {}),
          question: 'Which skill best fits handling `user_request` given `signals`?',
        },
        criteria: { ...this.skills, ...(ctx.skills ?? {}) },
      },
      needs_clarification: {
        type: 'noul',
        instructions: 'Is the user request in `user_request` too ambiguous to proceed without asking a clarifying question?',
      },
      should_search_kb: {
        type: 'noul',
        instructions: {
          signals: ctx.signals ?? {},
          question: ctx.signals?.error_fingerprint
            ? 'A concrete error fingerprint exists in `signals`. Would a knowledge-base search very likely hit a relevant precedent?'
            : 'Given the tech stack and task type in `signals`, is a knowledge-base search likely to return a relevant precedent (not a cold start)?',
        },
      },
      needs_web: {
        type: 'noul',
        instructions: 'Does answering `user_request` require information beyond the local codebase and model knowledge (unfamiliar library API, versioned docs, recent releases)?',
      },
      local_confidence: {
        type: 'score',
        instructions: 'How confident could a purely local answer (no web) be for `user_request`?',
        criteria: ['Cannot answer locally', 'Partial — needs verification against docs', 'Fully answerable locally'],
      },
    };
    if (typeof ctx.recentFailures === 'number') {
      questions.stuck = {
        type: 'noul',
        instructions: `The agent has had ${ctx.recentFailures} consecutive failed search/command rounds. Is it stuck and should it stop and report to the user instead of retrying?`,
      };
    }

    const { model, answers, usage } = await this.client.evaluate(
      { request: ctx.request, ...(ctx.signals ? { signals: ctx.signals } : {}) },
      questions,
      { signal },
    );

    return {
      model,
      usage,
      skill: gateSkill(answers.skill, this.autoThreshold, this.askThreshold),
      clarification: gateBool(answers.needs_clarification, 'ask_clarifying_question', this.autoThreshold),
      kbSearch: gateBool(answers.should_search_kb, 'search_knowledge_base', this.autoThreshold),
      webResearch: gateWeb(answers.needs_web, answers.local_confidence, this.autoThreshold),
      ...(answers.stuck ? { stuck: gateBool(answers.stuck, 'stop_and_report', this.autoThreshold) } : {}),
    };
  }
}

function gateSkill(answer, autoT, askT) {
  const base = { confidence: answer.confidence ?? null, probabilities: answer.probabilities ?? null, tier: tierOf(answer.confidence, autoT, askT) };
  if (base.tier === TIERS.ASK) return { ...base, action: null, choice: answer.choice ?? null, note: 'low confidence — present top candidates to the user' };
  return { ...base, action: 'load_skill', choice: answer.choice, note: null };
}

function gateBool(answer, action, autoT) {
  const p = answer.noul ?? null;
  const tier = p == null ? TIERS.PROCEED : p >= autoT ? TIERS.AUTO : p >= 0.5 ? TIERS.PROCEED : TIERS.ASK;
  return { probability: p, tier, action: tier === TIERS.ASK ? null : action };
}

function gateWeb(needsWeb, localScore, autoT) {
  const pWeb = needsWeb?.noul ?? null;
  const score = localScore?.score ?? null;
  // skip web when local answer is confidently sufficient
  const skip = pWeb != null && pWeb < 0.3 && score != null && score >= 1.5;
  const tier = skip ? TIERS.AUTO : tierOf(pWeb, autoT, 0.5);
  return { probability_web_needed: pWeb, local_score: score, tier, action: skip ? 'skip_web' : tier === TIERS.ASK ? null : 'do_web_research' };
}

function tierOf(confidence, autoT, askT) {
  if (confidence == null) return TIERS.PROCEED;
  if (confidence >= autoT) return TIERS.AUTO;
  if (confidence >= askT) return TIERS.PROCEED;
  return TIERS.ASK;
}

export { JevError };
