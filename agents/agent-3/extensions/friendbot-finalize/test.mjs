// Self-check probe for friendbot-finalize (no framework; node test.mjs).
// Cases mirror the 2026-08-03 trajectory failures (sessions 29c3e2cb / c47b2040).
import assert from "node:assert/strict";
import {
  countPathCitations,
  decide,
  hasBlockquotes,
  isNarration,
  isQuoteDelivery,
  turnHasSearch,
} from "./finalize-core.js";

let n = 0;
const ok = (name, fn) => {
  fn();
  n++;
  console.log(`ok ${n} - ${name}`);
};

const searchTurn = [
  { role: "user", content: [{ type: "text", text: "world is entertainment?" }] },
  { role: "assistant", content: [{ type: "toolCall", id: "c1", name: "exec", arguments: { command: "./search.py \"world is entertainment\" 10" } }] },
  { role: "tool", toolCallId: "c1", content: "UNIT ... path: `book.md`" },
];

const noSearchTurn = [
  { role: "user", content: [{ type: "text", text: "you and me are one" }] },
  { role: "assistant", content: [{ type: "text", text: "here is a quote" }] },
];

const good10 = [
  ...searchTurn,
  { role: "assistant", content: [{ type: "text", text: Array.from({ length: 12 }, (_, i) => `> quote ${i}\n> path: \`book-${i}.md\``).join("\n") }] },
];

ok("countPathCitations: backticked + bare", () => {
  assert.equal(countPathCitations("> x\n> path: `book.md`\n> path: other.md\npath: `third.md`"), 3);
  assert.equal(countPathCitations("no citations here"), 0);
});

ok("hasBlockquotes / isQuoteDelivery", () => {
  assert.equal(hasBlockquotes("hello\n> quoted"), true);
  assert.equal(isQuoteDelivery("> x\npath: `a.md`"), true);
  assert.equal(isQuoteDelivery("just chat"), false);
});

ok("turnHasSearch: content-block toolCall shape", () => assert.equal(turnHasSearch(searchTurn), true));
ok("turnHasSearch: OpenAI tool_calls shape", () => {
  const msgs = [
    { role: "user", content: "q" },
    { role: "assistant", tool_calls: [{ function: { name: "exec", arguments: '{"command":"./search.py \\"x\\" 10"}' } }] },
  ];
  assert.equal(turnHasSearch(msgs), true);
});
ok("turnHasSearch: no search in turn", () => assert.equal(turnHasSearch(noSearchTurn), false));

// S1: quotes with path: but NO search.py this turn (09:12:55 failure class)
ok("S1: quote delivery without search this turn -> revise", () => {
  const r = decide({ reply: 'Hawkins says it:\n> "That which I am is Allness."\n> path: `book.md`', messages: noSearchTurn });
  assert.equal(r?.action, "revise");
  assert.match(r.retryCandidates[0].instruction, /without running \.\/search\.py/);
});

// Fabrication: blockquotes with NO path: at all (worst class)
ok("citation integrity: blockquotes without path: -> revise", () => {
  const r = decide({ reply: '> "The world is actually entertainment."\n> "Worn lightly."', messages: searchTurn });
  assert.equal(r?.action, "revise");
  assert.match(r.retryCandidates[0].instruction, /no path: citations/);
});

// Q1: search ran but only 3 quotes (09:07/09:12 failure class)
ok("Q1: 3 quotes with search -> revise to >=10", () => {
  const r = decide({
    reply: '> q1\n> path: `a.md`\n> q2\n> path: `b.md`\n> q3\n> path: `c.md`',
    messages: searchTurn,
  });
  assert.equal(r?.action, "revise");
  assert.match(r.retryCandidates[0].instruction, /only 3 quoted sources/);
});

// Pass: 12 quotes with search
ok("pass: 12 quotes with search", () => {
  const r = decide({ reply: good10[good10.length - 1].content[0].text, messages: good10 });
  assert.equal(r, undefined);
});

// N1: narration opening (03:36:35 / 08:50 failure class)
ok("N1: 'Let me check my memory files...' -> revise", () => {
  const r = decide({ reply: "Let me check my memory files for any timezone info about Kaj.\nThere is none.", messages: [] });
  assert.equal(r?.action, "revise");
  assert.match(r.retryCandidates[0].instruction, /final answer only/);
  assert.equal(r.retryCandidates[0].maxAttempts, 1);
});
ok("N1: 'I need to check the current time...' -> revise", () => {
  assert.equal(isNarration("I need to check the current time in these locations. Let me get that."), true);
});
ok("N1: 'I found the exact quote' second line is not a trigger alone", () => {
  assert.equal(isNarration("I found the exact quote Lakshay is referencing."), false);
});

// Pass: chit-chat, NO_REPLY, short greetings
ok("pass: chit-chat", () => {
  assert.equal(decide({ reply: "Hahaha 😄 Geo over there giggling. What's funny?", messages: [] }), undefined);
});
ok("pass: NO_REPLY", () => {
  assert.equal(decide({ reply: "NO_REPLY", messages: [] }), undefined);
});
ok("pass: greeting", () => {
  assert.equal(decide({ reply: "Hello Lakshay! How can I help today?", messages: [] }), undefined);
});

console.log(`\n${n} probes passed`);
