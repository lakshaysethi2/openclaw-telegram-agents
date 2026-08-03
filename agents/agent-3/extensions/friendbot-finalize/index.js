import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { decide, isQuoteDelivery } from "./finalize-core.js";

// Friend Bot finalize enforcement: before the bot's final reply is accepted,
// require evidence-based quote deliveries (search-first + >=10 path: citations)
// and final-answer-only replies (no process narration). Prompt rules alone were
// shown insufficient with deepseek-v4-flash; this hook is the run-level gate.
// Bounded: core allows at most 3 revisions per run; each rule carries its own
// maxAttempts, so a bad reply always ships eventually rather than looping.

export default definePluginEntry({
  id: "friendbot-finalize",
  name: "Friend Bot finalize enforcement",
  description:
    "Run-level gate: quote deliveries must run search.py this turn and carry >=10 path: citations; final replies must not narrate the process",
  register(api) {
    api.on(
      "before_agent_finalize",
      (event) => {
        const reply = event?.lastAssistantMessage;
        if (!reply) return;
        const outcome = decide({ reply, messages: event?.messages });
        if (!outcome) return;
        const why = isQuoteDelivery(reply)
          ? "quote rules"
          : "narration";
        console.log(
          `[friendbot-finalize] requesting one more pass (${why}): runId=${event.runId ?? "?"}`,
        );
        return outcome;
      },
      { priority: 100 },
    );
  },
});
