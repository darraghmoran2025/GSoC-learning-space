# Mesa GSoC Learning Space

**Candidate:** Darragh Moran — University of Galway, Financial Mathematics & Economics
**Project:** [Mesa](https://github.com/projectmesa/mesa) — Behavioral Framework (GSoC 2026)

This repository documents my process of learning Mesa from the ground up — building progressively complex agent-based models, identifying pain points in the current API, and developing the intuition needed to contribute meaningfully to the Behavioral Framework project.

---

## Structure

```
Mesa_GSoC/
├── motivation.md              # Background, goals, pain points log
├── models/
│   ├── schelling/             # Model 1: Schelling Segregation
│   ├── wolf_sheep/            # Model 2: Wolf-Sheep Predator-Prey
│   ├── wealth/                # Model 3: Wealth Distribution (extended)
│   └── bdi_agents/            # Model 4: BDI Agent prototype
├── reviews/                   # Reviews of other candidates' work
└── notes/                     # Design notes, reading notes, proposal ideas
```

---

## Models

| # | Model | Mesa concepts | Status |
|---|-------|---------------|--------|
| 1 | [Schelling Segregation](models/schelling/README.md) | `SingleGrid`, `DataCollector`, `shuffle_do` | ✅ Complete |
| 2 | [Wolf-Sheep Predator-Prey](models/wolf_sheep/README.md) | `MultiGrid`, `agents_by_type`, multi-class stepping, agent removal | ✅ Complete |
| 3 | [Wealth Distribution (extended)](models/wealth/README.md) | `NetworkGrid`, agent-level `DataCollector`, Gini coefficient, Lorenz curve, network topology comparison | ✅ Complete |
| 4 | [BDI Agent prototype](models/bdi_agents/README.md) | Custom `BDIAgent` base class, beliefs/desires/intentions, partial observability, replanning | ✅ Complete |

---

## Pain Points Identified

Issues found while building — worth raising with the Mesa community and directly relevant to the Behavioral Framework proposal.

| # | Issue | Model | Severity |
|---|-------|-------|----------|
| 1 | Two-step agent removal (`grid.remove_agent` + `agent.remove()`) is easy to get half-wrong, leaving ghost agents | Wolf-Sheep | High |
| 2 | Stepping order between agent types is a silent modelling assumption with measurable outcome effects — no built-in way to document it | Wolf-Sheep | Medium |
| 3 | `get_neighborhood` vs `get_neighbors` return types (positions vs agents) are easy to confuse | Wolf-Sheep | Medium |
| 4 | `DataCollector` lambdas re-iterate AgentSets every step — no caching mechanism for expensive reporters | Wolf-Sheep | Low (at scale: High) |
| 5 | `agents_by_type` behaviour on zero-population types not clearly documented | Wolf-Sheep | Low |
| 6 | `NetworkGrid.coord_iter()` not implemented — must fall back to raw NetworkX graph | Wealth | Medium |
| 7 | `get_agent_vars_dataframe()` returns multi-indexed `(Step, AgentID)` frame with no clear docs example | Wealth | Medium |
| 8 | `NetworkGrid.get_neighbors()` silently returns `[]` for isolated nodes — no warning | Wealth | Low |
| 9 | No built-in multi-step plan / deferred action mechanism — intention queues must be user-managed | BDI | High |
| 10 | No partial observability primitive — `grid.get_cell_list_contents()` works for any cell regardless of agent position | BDI | High |
| 11 | `agents_by_type[T]` raises `KeyError` when all agents of type T have been removed | BDI | Medium |
| 12 | No standard interface for inspecting agent belief/intention state — all debugging is manual | BDI | Medium |

Full context for each in [`motivation.md`](motivation.md) and the relevant model README.

---

## Running the models

```bash
pip install mesa matplotlib numpy networkx

# Schelling Segregation
cd models/schelling && python run.py

# Wolf-Sheep Predator-Prey
cd models/wolf_sheep && python run.py
