# FTS5 Search Syntax for `notes-search`

Use this reference only when a research prompt asks for explicit search-query constraints that are easier to express with FTS5 syntax. In most research tasks, keep using multiple ordinary `notes-search search "..."` queries, then union, dedupe, and rerank. Implementation details live in `~/projects/notes/search`.

## When to Use Advanced FTS5

Use FTS5 syntax for constraints such as:
- Excluding titles with generic phrases: `quick screen`, `screen_summary`, `watchlist`
- Targeting a specific indexed field, such as title or tags
- Expressing a phrase or Boolean constraint that would otherwise require many noisy post-filters

Do not use advanced syntax just to improve recall. Recall still comes from multiple query variants.

## Indexed Fields

The FTS5 table has these searchable fields:
- `filepath`
- `title`
- `search_text`
- `metadata_search_text`
- `tags_text`

Prefer the normal `--folder` option for folder restriction. Use `(filepath:...)` only when the folder constraint must be part of the FTS expression.

Always wrap field filters in parentheses so FTS5 parses them robustly:
- Good: `(title:memory cycle)`
- Good: `(title:"memory cycle")`
- Avoid: `title:memory cycle`

## Common Patterns

Exclude notes whose title contains a phrase:

```bash
notes-search search 'CPU investment NOT (title:"quick screen")' --limit 30 --json
```

Exclude multiple generic title patterns:

```bash
notes-search search 'CPU investment NOT (title:"quick screen") NOT (title:"screen summary")' --limit 30 --json
```

Target title matches:

```bash
notes-search search '(title:CPU investment)' --limit 30 --json
notes-search search '(title:"memory cycle")' --limit 30 --json
```

Target tags:

```bash
notes-search search 'agent (tags_text:research)' --limit 30 --json
```

Use phrase constraints sparingly; phrase searches are precise but may reduce recall:

```bash
notes-search search '"moving average" trading' --limit 30 --json
```

## Operational Notes

- FTS5 syntax applies to the default FTS5 engine. Do not use it with QMD semantic modes.
- FTS5 syntax works inside `search-multi` query strings too — each query is normalized independently before fusion.
- Keep per-query limits generous, then apply top-N after fusion and the shortlist filter.
- If an advanced FTS query returns suspiciously few results, rerun a plain version of the query and compare before trusting the constraint.
- For CJK topics, still run both compound and split query variants unless the user explicitly asks for a single constrained query.
