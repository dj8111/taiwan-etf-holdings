# Graph Report - reverse-api-engineer  (2026-11-04)

## Corpus Check
- 10 files · ~2,923 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: .csv 3, (none) 1, .db 1)

## Summary
- 75 nodes · 111 edges · 8 communities (5 shown, 3 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 6 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1726d59`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- steps
- target_mode
- main
- ETFRepository
- main.py
- export_csv
- fetch_all_twse_etf_codes

## God Nodes (most connected - your core abstractions)
1. `ETFRepository` - 15 edges
2. `main()` - 11 edges
3. `fetch_and_save()` - 6 edges
4. `target_mode` - 6 edges
5. `fetch_all_batch()` - 5 edges
6. `export_csv()` - 5 edges
7. `show_stock_history()` - 5 edges
8. `steps` - 5 edges
9. `fetch_all_twse_etf_codes()` - 4 edges
10. `show_holdings()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `fetch_and_save()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py
- `list_dates()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py
- `show_diff()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py
- `show_holdings()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py
- `search_stock()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py

## Import Cycles
- None detected.

## Communities (8 total, 3 thin omitted)

### Community 0 - "steps"
Cohesion: 0.20
Nodes (10): jobs, update-holdings, name, run, uses, with, runs-on, steps (+2 more)

### Community 1 - "target_mode"
Cohesion: 0.13
Nodes (14): target_mode, name, permissions, contents, cron, default, description, options (+6 more)

### Community 2 - "main"
Cohesion: 0.18
Nodes (5): list_dates(), list_funds(), main(), show_diff(), show_holdings()

### Community 3 - "ETFRepository"
Cohesion: 0.19
Nodes (3): ETFRepository, search_stock(), show_stock_history()

### Community 4 - "main.py"
Cohesion: 0.31
Nodes (3): fetch_all_batch(), fetch_and_save(), get_collectors()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ETFRepository` connect `ETFRepository` to `main`, `main.py`, `repository.py`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Should `target_mode` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Why does `jobs` connect `steps` to `target_mode`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._