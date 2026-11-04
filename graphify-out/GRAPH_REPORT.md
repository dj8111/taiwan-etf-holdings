# Graph Report - reverse-api-engineer  (2026-11-04)

## Corpus Check
- 11 files · ~3,695 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: .csv 4, (none) 1, .db 1)

## Summary
- 104 nodes · 207 edges · 7 communities (5 shown, 2 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9b7f101c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- steps
- target_mode
- ETFRepository
- ETFFund
- main.py
- repository.py

## God Nodes (most connected - your core abstractions)
1. `ETFRepository` - 25 edges
2. `init_db()` - 13 edges
3. `main()` - 13 edges
4. `ETFFund` - 12 edges
5. `ETFNav` - 11 edges
6. `fetch_and_save_navs()` - 10 edges
7. `ETFHolding` - 9 edges
8. `TWSENavCollector` - 8 edges
9. `fetch_and_save()` - 8 edges
10. `NavItem` - 7 edges

## Surprising Connections (you probably didn't know these)
- `ETFRepository` --uses--> `NavItem`  [INFERRED]
  db/repository.py → collectors/twse_nav.py
- `list_funds()` --uses--> `ETFFund`  [INFERRED]
  main.py → db/models.py
- `show_holdings()` --uses--> `ETFFund`  [INFERRED]
  main.py → db/models.py
- `show_nav_history()` --uses--> `ETFFund`  [INFERRED]
  main.py → db/models.py
- `export_csv()` --calls--> `init_db()`  [EXTRACTED]
  main.py → db/models.py

## Import Cycles
- None detected.

## Communities (7 total, 2 thin omitted)

### Community 0 - "steps"
Cohesion: 0.20
Nodes (10): jobs, update-holdings-and-nav, name, run, uses, with, runs-on, steps (+2 more)

### Community 1 - "target_mode"
Cohesion: 0.13
Nodes (14): target_mode, name, permissions, contents, cron, default, description, options (+6 more)

### Community 2 - "ETFRepository"
Cohesion: 0.15
Nodes (10): init_db(), ETFRepository, list_dates(), list_funds(), main(), search_stock(), show_diff(), show_holdings() (+2 more)

### Community 3 - "ETFFund"
Cohesion: 0.19
Nodes (3): ETFFund, ETFHolding, ETFNav

### Community 4 - "main.py"
Cohesion: 0.13
Nodes (7): TWSENavCollector, export_csv(), fetch_all_batch(), fetch_all_twse_etf_codes(), fetch_and_save(), fetch_and_save_navs(), get_collectors()

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ETFRepository` connect `ETFRepository` to `ETFFund`, `main.py`, `repository.py`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ETFRepository` (e.g. with `NavItem` and `ETFFund`) actually correct?**
  _`ETFRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `target_mode` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Why does `ETFNav` connect `ETFFund` to `ETFRepository`, `main.py`, `repository.py`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ETFFund` (e.g. with `ETFRepository` and `list_funds()`) actually correct?**
  _`ETFFund` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13438735177865613 - nodes in this community are weakly interconnected._
- **Why does `fetch_and_save_navs()` connect `main.py` to `ETFRepository`, `ETFFund`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._