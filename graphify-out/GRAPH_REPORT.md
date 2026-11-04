# Graph Report - reverse-api-engineer  (2026-11-04)

## Corpus Check
- 10 files · ~2,339 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 1, .csv 1, .db 1)

## Summary
- 25 nodes · 24 edges · 5 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `93e8c8ef`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- steps
- target_mode
- True
- update_etf.yml
- update-holdings

## God Nodes (most connected - your core abstractions)
1. `target_mode` - 6 edges
2. `steps` - 5 edges
3. `update-holdings` - 3 edges
4. `with` - 3 edges
5. `schedule` - 2 edges
6. `workflow_dispatch` - 2 edges
7. `inputs` - 2 edges
8. `permissions` - 2 edges
9. `jobs` - 2 edges
10. `name` - 1 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (5 total, 0 thin omitted)

### Community 0 - "steps"
Cohesion: 0.29
Nodes (7): name, run, uses, with, steps, cache, python-version

### Community 1 - "target_mode"
Cohesion: 0.33
Nodes (6): target_mode, default, description, options, required, type

### Community 2 - "True"
Cohesion: 0.40
Nodes (5): cron, True, schedule, workflow_dispatch, inputs

### Community 3 - "update_etf.yml"
Cohesion: 0.50
Nodes (3): name, permissions, contents

### Community 4 - "update-holdings"
Cohesion: 0.67
Nodes (3): jobs, update-holdings, runs-on

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `True` connect `True` to `update_etf.yml`?**
  _High betweenness centrality (0.565) - this node is a cross-community bridge._
- **Why does `jobs` connect `update-holdings` to `update_etf.yml`?**
  _High betweenness centrality (0.489) - this node is a cross-community bridge._
- **Why does `update-holdings` connect `update-holdings` to `steps`?**
  _High betweenness centrality (0.489) - this node is a cross-community bridge._