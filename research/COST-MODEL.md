# Where the tokens go

Fitted from our own run logs on Sonnet and Opus sessions. These are shares of the bill by billing category, not by source (we did not measure a clean split into "files read vs skills vs tool output").

| Bucket | Share of the bill | What it is | Can it be compressed? |
|---|---|---|---|
| Cache writes | about 48 to 49% | Everything newly entering context: your prompt, files read, tool output, skill text, agent briefs | Partly: read fewer files, filter tool output, keep skills short. The test-output filter cut one 315-line log to 51 lines. |
| Output | about 27 to 29% | What the model writes | Barely. It is the work itself; only a cheaper model or fewer retries lowers it. |
| Cache reads | about 21 to 24% | Re-reading the whole conversation every turn | Mostly by shortening sessions: `/clear` with a handoff, or `/compact`. |
| Fixed startup | about 1.3k tokens for 13 skills (about 7.5k with all skills and MCP) | Skill and tool descriptions each session | Yes, but it is under a cent per session. |
| Model price | Opus about 1.7 to 2.2x Sonnet per token; Haiku runs cost about 7 to 13% of Sonnet | The rate applied to everything above | The biggest lever. Changing tier beats every trimming trick. |

## Caching

Caching is provider-side and cannot be edited mid-session. It is what makes re-reading cheap (about a tenth of the fresh input price). The saving from restarting a long session comes from a shorter context, not from changing the cache. We did not measure the restart saving on real sessions.

## What a spawned agent costs

About 19k cache-write tokens per spawn, roughly $0.15 on Opus, before it does any work. In our runs the planner, the triad (Sonnet session plus Opus planner plus Haiku worker) and `plan-haiku` cost 5 to 12x a single session and scored no higher on any task we could grade. Spawning is worth considering when the work is large and independent, or reading it would flood the main context. It was not worth it for the tasks we tested.
