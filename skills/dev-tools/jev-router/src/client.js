// jev-router/src/client.js — zero-dependency JEV (TypeSafe systemone) client.
// Node >= 18 (global fetch). No npm deps. Key comes from TYPESAFE_API_KEY env var
// or is passed explicitly to the constructor.

const DEFAULT_ENDPOINT = 'https://api.typesafe.ai/v1/systemone';
const DEFAULT_MODEL = 'jev-1.13.0'; // pin version for stable routing thresholds

export class JevError extends Error {
  constructor(message, { status = 0, retryable = false, body = null } = {}) {
    super(message);
    this.name = 'JevError';
    this.status = status;
    this.retryable = retryable;
    this.body = body;
  }
}

export class JevClient {
  constructor({ apiKey, endpoint = DEFAULT_ENDPOINT, model = DEFAULT_MODEL, timeoutMs = 15000, maxRetries = 3 } = {}) {
    this.apiKey = apiKey ?? process.env.TYPESAFE_API_KEY;
    if (!this.apiKey) throw new JevError('Missing API key: pass apiKey or set TYPESAFE_API_KEY');
    this.endpoint = endpoint;
    this.model = model;
    this.timeoutMs = timeoutMs;
    this.maxRetries = maxRetries;
  }

  // questions: { [id]: { type: 'noul'|'choice'|'score', instructions, criteria? } }
  // Returns { model, answers, usage } — answers keyed by the same question ids.
  async evaluate(state, questions, { model, signal } = {}) {
    const payload = { state, model: model ?? this.model, questions };
    let lastErr;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      if (attempt > 0) await sleep(backoffMs(attempt));
      try {
        return await this.#once(payload, signal);
      } catch (err) {
        lastErr = err;
        if (!(err instanceof JevError) || !err.retryable || attempt === this.maxRetries) throw err;
      }
    }
    throw lastErr;
  }

  async #once(payload, signal) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(new JevError('Request timed out')), this.timeoutMs);
    if (signal) signal.addEventListener('abort', () => ctrl.abort(signal.reason), { once: true });
    try {
      const res = await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: ctrl.signal,
      });

      if (res.status === 429 || res.status === 529) {
        throw new JevError(`JEV rate-limited/overloaded (HTTP ${res.status})`, { status: res.status, retryable: true });
      }
      if (res.status === 401) {
        throw new JevError('Authentication failed — check TYPESAFE_API_KEY', { status: 401 });
      }
      if (!res.ok) {
        const body = await safeJson(res);
        throw new JevError(`JEV request failed (HTTP ${res.status})`, { status: res.status, body });
      }
      const body = await res.json();
      return { model: body.model, answers: body.answers ?? {}, usage: body.usage ?? {} };
    } catch (err) {
      if (err instanceof JevError) throw err;
      // fetch network failure / abort — retryable
      throw new JevError(`Network error: ${err.message}`, { retryable: true });
    } finally {
      clearTimeout(timer);
    }
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const backoffMs = (attempt) => Math.min(400 * 2 ** (attempt - 1), 4000);

async function safeJson(res) {
  try { return await res.json(); } catch { return null; }
}
