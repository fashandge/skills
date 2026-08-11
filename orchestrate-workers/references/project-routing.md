# Project routing for spawned workers

How the orchestrator decides which project — and therefore which herdr
workspace — each task's worker runs in. Used by the routing step of
orchestrate-workers.

## Routing rule

1. **Current project first.** Identify the project the orchestrator itself
   runs in (its cwd). Tasks that clearly belong to it spawn as new tabs in
   the current workspace — no placement flags.
2. **Otherwise match the task to one project below** — the project whose
   repo the task edits, or whose data/tooling it runs. Spawn the worker with
   that project's directory as cwd and `--workspace-label <label>`; the
   workspace is created on first use.
3. **No project.** A task that belongs nowhere ("summarize the top posts in
   my X home feed") spawns in the orchestrator's own workspace and cwd.

Workspace labels are the project folder name, with one exception: **notes**
is split by subproject — usually the label `search`, `organize` only for
organizer work (see its entry).

Match on what the task *touches*, not what it mentions: "add a quick screen
for NVDA" runs stock_picker tooling (stock_picker), while "fix the quick
screen fetcher's retry logic" edits it (also stock_picker) — but "make the
dashboard show quick-screen scores" edits market-pulse. Tasks about note
*content* (writing a wiki, absorbing clippings, researching the vault) are
not notes-project tasks — the notes project is the search/organizer
software; route content tasks by their topic (see the notes entry).

## Inventory

Projects live under `~/projects/<name>` unless a path is given. Related
projects are grouped so the confusable ones sit next to each other.

### Investing & markets

- **stock_picker** — stock research toolkit: themed watchlist (ticker.csv),
  research methodology, quick-screen/fundamentals/earnings skills,
  stockanalysis.com fetchers. Also the home for general discussion and
  research on investing and stock analysis — a task about a company, a
  sector, or a thesis routes here even when it touches no stock_picker
  code. Keywords: watchlist, quick screen, fundamentals, earnings call,
  ticker.csv, market pulse data, investment research/discussion.
- **investment** — fetches stock price data (daily/weekly bars) and computes
  the derived features and technical indicators on top of them, in a DuckDB
  pipeline; plus ML classifiers predicting price moves. Keywords:
  stocks.duckdb, daily bars, indicators, features, classifier, examples
  table.
- **market-pulse** — React + FastAPI web dashboard monitoring market and
  portfolio tickers; reads stock_picker's ticker.csv/portfolio.csv.
  Keywords: dashboard, Market Overview, frontend, Vite, Tailwind, FastAPI.
- **news** — unattended news aggregation and summarization (X/Twitter via
  xreach, TradingView, wenxuecity, Zhihu) running on LaunchAgents. Route
  here only for code changes to this project. *Running* the fetch-x-posts /
  fetch-reddit-posts skills is not a news task — that routes by the topic
  being researched, and most of the time belongs to no project at all
  ("fetch the top 30 posts in my X home feed" stays with the orchestrator).
  Keywords: xreach, X home feed fetcher, news summaries, feed snapshot.

### Notes & research writing

- **notes** — the software behind the Obsidian vault, with two subprojects:
  `search/` full-text search engine (FTS5/QMD, indexing, watcher,
  agent-index notes) and `organize/` clipping organizer for `raw/inbox/`.
  Route here only for code changes; most of the time that means the
  `search` workspace, and only organizer work (routing clippings out of
  `raw/inbox/`, the organize pipeline) goes to the `organize` workspace.
  Creating or researching note *content* (a wiki, an absorb, vault
  research) routes by the topic under discussion — most often investment or
  stock analysis, which belongs to stock_picker. Keywords: notes-search,
  index, vault search engine, organize inbox.
- **clipping** — web-clipping CLI: URL → markdown with YAML frontmatter.
  Keywords: clip.py, normalize.
- **startups** — research and ideation writing workspace on startups and
  business models; analysis and notes, not software.

### Agent & dev tooling

- **agents** — Python library for driving coding-agent CLIs and
  orchestration: handoff protocol, spawn_worker, herdr/cmux/tmux adapters,
  OpenClaw messaging, OpenRouter/DeepSeek clients, `env.build_env()`.
  Keywords: spawn_worker, handoff, openclaw, coding_agents, launchd env.
- **browser** — logged-in Chrome automation over the Chrome DevTools
  Protocol; the fetch layer other projects use for bot-hardened sites.
  Keywords: CDP, logged_in_chrome, real-browser scraping.
- **skills** (`~/skills`) — global agent skills, one `<name>/SKILL.md` per
  folder, symlinked as `~/.claude/skills` and `~/.codex/skills`. Global
  skills only: a project-level skill (a `skills/<name>/` folder inside a
  project repo) belongs to that project — and when that is the
  orchestrator's own project, the current workspace. Keywords: SKILL.md,
  slash command, skill description/frontmatter, skill eval.
- **dotfiles** (`~/dotfiles`) — shell configuration, personal command
  wrappers (`mycmd/`), machine install scripts. Keywords: .zshrc, .zshenv,
  PATH, mycmd, install.sh.

Rarely-used projects (rtk, weather, insurance, email, polymarkets,
claude-pty-wrapper, and the rest of `~/projects`) are deliberately omitted.
A task that clearly targets one of them still routes the same way — cwd =
its folder, `--workspace-label` = its folder name.
