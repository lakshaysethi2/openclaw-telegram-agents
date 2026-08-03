// Friend Bot finalize enforcement (pure logic; no OpenClaw imports).
// Rules checked on every natural final reply via the before_agent_finalize hook:
//   S1 search-first: a reply that quotes Hawkins must have run ./search.py this turn
//   Q1 min-quotes:   a quote delivery must carry >= 10 path: citations
//   N1 no-narration: the final answer must not open by narrating the process
// Ceiling (documented, not enforced): content answers WITHOUT quotes and WITHOUT
// narration are indistinguishable from chit-chat at finalize time.
export const MIN_QUOTES = 10;

export const NARRATION_RE = new RegExp(
  [
    "^let me\\b", "^let's\\b", "^i'?ll\\b", "^i will\\b",
    "^the searches?\\b", "^searching\\b", "^pulling\\b", "^checking\\b",
    "^i need to\\b", "^i should\\b", "^i'm (?:going|gonna|checking|searching|looking|pulling)\\b",
    "^on it\\b", "^hang on\\b", "^give me a sec\\b", "^one moment\\b", "^i checked\\b",
  ].join("|"),
  "i",
);

export function countPathCitations(text) {
  if (typeof text !== "string") return 0;
  const re = /path:\s*(?:`[^`]*`|[^\s`]+)/g;
  return (text.match(re) || []).length;
}

export function hasBlockquotes(text) {
  return typeof text === "string" && /(^|\n)\s*>/.test(text);
}

export function isQuoteDelivery(text) {
  return hasBlockquotes(text) || countPathCitations(text) > 0;
}

// First two non-empty lines are the "opening"; narration there is what users see.
export function openingLines(text) {
  return (typeof text === "string" ? text : "")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .slice(0, 2)
    .join("\n");
}

export function isNarration(text) {
  return NARRATION_RE.test(openingLines(text));
}

// Collect exec/search tool calls from a transcript message, tolerating both the
// OpenAI wire shape ({tool_calls:[{function:{name,arguments}}]}) and the
// session-file shape (content blocks [{type:"toolCall",name,arguments}]).
export function collectToolCalls(message) {
  const out = [];
  if (!message || typeof message !== "object") return out;
  for (const tc of Array.isArray(message.tool_calls) ? message.tool_calls : []) {
    const fn = tc?.function;
    const name = typeof fn?.name === "string" ? fn.name : "";
    const args = typeof fn?.arguments === "string" ? fn.arguments : "";
    out.push({ name, args, raw: tc });
  }
  if (Array.isArray(message.content)) {
    for (const block of message.content) {
      if (block && block.type === "toolCall") {
        const args =
          typeof block.arguments === "string"
            ? block.arguments
            : JSON.stringify(block.arguments ?? "");
        out.push({ name: block.name ?? "", args, raw: block });
      }
    }
  }
  return out;
}

export function isSearchCall(tool) {
  const name = String(tool?.name ?? "");
  const args = String(tool?.args ?? "");
  return (
    /^search$/.test(name) ||
    /search\.py|docdocgo/.test(name) ||
    (name === "exec" && /search\.py|docdocgo/.test(args))
  );
}

// True when at least one search.py/docdocgo call appears after the last user
// message (i.e. in this turn). No user message -> fall back to whole transcript.
export function turnHasSearch(messages) {
  const list = Array.isArray(messages) ? messages : [];
  let lastUserIdx = -1;
  for (let i = 0; i < list.length; i++) {
    if (list[i]?.role === "user") lastUserIdx = i;
  }
  for (let i = lastUserIdx + 1; i < list.length; i++) {
    for (const tc of collectToolCalls(list[i])) {
      if (isSearchCall(tc)) return true;
    }
  }
  return false;
}

export function revise(instruction, maxAttempts = 2) {
  return { action: "revise", retryCandidates: [{ instruction, maxAttempts }] };
}

// Decide whether the final reply needs one more model pass. Returns a
// before_agent_finalize result, or undefined to accept the reply.
export function decide({ reply, messages }) {
  if (typeof reply !== "string" || reply.trim() === "") return undefined;
  if (reply.trim() === "NO_REPLY") return undefined;

  if (isQuoteDelivery(reply)) {
    const paths = countPathCitations(reply);
    if (paths === 0) {
      return revise(
        "Your reply quotes Hawkins text but carries no path: citations. Rerun ./search.py for the topic and quote only verbatim units, each with its own path: `...` citation. Deliver at least 10 quotes, then stop.",
      );
    }
    if (!turnHasSearch(messages)) {
      return revise(
        `You delivered ${paths} quoted source(s) without running ./search.py in this turn. Rerun ./search.py for the topic and deliver at least ${MIN_QUOTES} verbatim quotes, each with its own path: \`...\` citation, then stop.`,
      );
    }
    if (paths < MIN_QUOTES) {
      return revise(
        `Your reply delivered only ${paths} quoted sources; the minimum is ${MIN_QUOTES}. Rerun ./search.py and deliver at least ${MIN_QUOTES} verbatim quotes, each with its own path: \`...\` citation, then stop.`,
      );
    }
    return undefined;
  }

  if (isNarration(reply)) {
    return revise(
      "Reply with the final answer only. Remove the process narration opening (\"Let me…\", \"I'll…\", \"I need to…\", \"The searches…\") and state the answer directly.",
      1,
    );
  }
  return undefined;
}
