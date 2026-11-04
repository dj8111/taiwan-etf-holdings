# Graph Report - reverse-api-engineer  (2026-11-05)

## Corpus Check
- 11 files · ~3,737 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: .csv 4, (none) 1, .db 1)

## Summary
- 103 nodes · 203 edges · 7 communities (5 shown, 2 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 15 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1cc90a5a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- steps
- target_mode
- ETFRepository
- ETFFund
- main.py
- NavItem

## God Nodes (most connected - your core abstractions)
1. `ETFRepository` - 25 edges
2. `main()` - 13 edges
3. `init_db()` - 13 edges
4. `ETFNav` - 11 edges
5. `fetch_and_save_navs()` - 10 edges
6. `ETFFund` - 9 edges
7. `ETFHolding` - 9 edges
8. `fetch_and_save()` - 8 edges
9. `TWSENavCollector` - 8 edges
10. `fetch_all_batch()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `ETFRepository` --uses--> `NavItem`  [INFERRED]
  db/repository.py → collectors/twse_nav.py
- `fetch_and_save_navs()` --calls--> `init_db()`  [EXTRACTED]
  main.py → db/models.py
- `fetch_and_save_navs()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py
- `fetch_and_save()` --calls--> `init_db()`  [EXTRACTED]
  main.py → db/models.py
- `fetch_and_save()` --calls--> `ETFRepository`  [EXTRACTED]
  main.py → db/repository.py

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
Cohesion: 0.16
Nodes (10): init_db(), ETFRepository, list_dates(), list_funds(), main(), search_stock(), show_diff(), show_holdings() (+2 more)

### Community 3 - "ETFFund"
Cohesion: 0.16
Nodes (3): ETFFund, ETFHolding, ETFNav

### Community 4 - "main.py"
Cohesion: 0.14
Nodes (7): TWSENavCollector, export_csv(), fetch_all_batch(), fetch_all_taiwan_etf_codes(), fetch_and_save(), fetch_and_save_navs(), get_collectors()

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ETFRepository` connect `ETFRepository` to `ETFFund`, `main.py`, `NavItem`?**
  _High betweenness centrality (0.180) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ETFRepository` (e.g. with `NavItem` and `ETFFund`) actually correct?**
  _`ETFRepository` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Should `target_mode` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Why does `ETFNav` connect `ETFFund` to `ETFRepository`, `main.py`, `NavItem`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `fetch_and_save_navs()` (e.g. with `.fetch_all_navs()` and `.save_navs_batch()`) actually correct?**
  _`fetch_and_save_navs()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Why does `fetch_and_save_navs()` connect `main.py` to `ETFRepository`, `NavItem`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._