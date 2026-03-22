# Mesa GSoC 2026 — Learning Space

**Candidate:** Darragh Moran · University of Galway · Financial Mathematics & Economics
**Project:** [Mesa Behavioral Framework](https://github.com/projectmesa/mesa) · GSoC 2026
**Mentors:** Ewout ter Hoeven ([@EwoutH](https://github.com/EwoutH)) · Jan Kwakkel ([@quaquel](https://github.com/quaquel))

This repository documents my process of learning Mesa from the ground up — building progressively complex agent-based models, identifying pain points in the current API, and developing the intuition needed to contribute meaningfully to the Behavioral Framework project.

---

## Progress

| Area | Status |
|------|--------|
| 5 models built (Schelling → RL Agent) | ✅ Complete |
| 15 pain points identified and documented | ✅ Complete |
| Mesa GitHub issues & discussions researched | ✅ Complete |
| GitHub discussions opened on key pain points | ✅ Complete |
| Peer candidate review written | ✅ Complete |
| GSoC proposal | 🔄 In progress |

---

## Models

| # | Model | Mesa concepts | Status |
|---|-------|---------------|--------|
| 1 | [Schelling Segregation](models/schelling/README.md) | `SingleGrid`, `DataCollector`, `shuffle_do` | ✅ |
| 2 | [Wolf-Sheep Predator-Prey](models/wolf_sheep/README.md) | `MultiGrid`, `agents_by_type`, multi-class stepping, agent removal | ✅ |
| 3 | [Wealth Distribution (extended)](models/wealth/README.md) | `NetworkGrid`, agent-level `DataCollector`, Gini coefficient, Lorenz curve, network topology comparison | ✅ |
| 4 | [BDI Agent prototype](models/bdi_agents/README.md) | Custom `BDIAgent` base class, beliefs / desires / intentions, partial observability, replanning | ✅ |
| 5 | [RL Agent — Q-Learning](models/rl_agent/README.md) | Tabular Q-learning, ε-greedy exploration, value heatmap, learner vs. reactive baseline | ✅ |

---

## Pain Points Identified

15 issues found while building — documented with model context and severity. Full details in [`motivation.md`](motivation.md) and each model's README.

| # | Issue | Model | Severity |
|---|-------|-------|----------|
| 1 | Two-step agent removal (`grid.remove_agent` + `agent.remove()`) easy to get half-wrong, leaving ghost agents | Wolf-Sheep | High |
| 2 | Stepping order between agent types is a silent modelling assumption with measurable outcome effects — no built-in way to document it | Wolf-Sheep | Medium |
| 3 | `get_neighborhood` vs `get_neighbors` return types (positions vs agents) are easy to confuse | Wolf-Sheep | Medium |
| 4 | `DataCollector` lambdas re-iterate `AgentSet` every step — no caching for expensive reporters | Wolf-Sheep | Low → High at scale |
| 5 | `agents_by_type` behaviour on zero-population types not clearly documented | Wolf-Sheep | Low |
| 6 | `NetworkGrid.coord_iter()` not implemented — must fall back to raw NetworkX graph | Wealth | Medium |
| 7 | `get_agent_vars_dataframe()` returns multi-indexed `(Step, AgentID)` frame with no clear docs example | Wealth | Medium |
| 8 | `NetworkGrid.get_neighbors()` silently returns `[]` for isolated nodes — no warning | Wealth | Low |
| 9 | No built-in multi-step plan / deferred action mechanism — intention queues must be user-managed | BDI | High |
| 10 | No partial observability primitive — `grid.get_cell_list_contents()` works for any cell regardless of agent position | BDI | High |
| 11 | `agents_by_type[T]` raises `KeyError` when all agents of type T have been removed | BDI | Medium |
| 12 | No standard interface for inspecting agent belief/intention state — all debugging is manual | BDI | Medium |
| 13 | No built-in state abstraction for RL — state is just `agent.pos`; adding features requires manual tuple-packing | RL Agent | Medium |
| 14 | Q-table not serialisable via `DataCollector` — can't track full policy evolution without custom serialisation | RL Agent | Medium |
| 15 | `SingleGrid` prevents multiple agents per cell — distorts learned policy in dense RL environments | RL Agent | Low |

---

## Community Engagement

| Activity | Detail |
|----------|--------|
| GitHub discussion opened | [Partial observability primitive](https://github.com/projectmesa/mesa/discussions) — pain point #10, not currently tracked in Mesa |
| GitHub discussion opened | [IntentionQueue / multi-step plan support](https://github.com/projectmesa/mesa/discussions) — pain point #9, links to `bdi_base.py` as prototype |
| Peer review written | [`reviews/review_1khaled-ctrl.md`](reviews/review_1khaled-ctrl.md) — FSM/BehaviorModule approach vs BDI |
| Mesa issues researched | [`notes/mesa_issues.md`](notes/mesa_issues.md) — pain point overlap with existing issues, `mesa.experimental.actions` discovery |

---

## Repository Structure

```
Mesa_GSoC/
├── motivation.md              # Background, goals, full pain points log
├── requirements.txt           # pip install -r requirements.txt
├── models/
│   ├── schelling/             # Model 1 — SingleGrid, emergent segregation
│   ├── wolf_sheep/            # Model 2 — MultiGrid, predator-prey dynamics
│   ├── wealth/                # Model 3 — NetworkGrid, Gini, Lorenz curve
│   ├── bdi_agents/            # Model 4 — BDI architecture prototype
│   └── rl_agent/              # Model 5 — Q-learning, value heatmap
├── reviews/                   # Peer reviews of other candidates' work
└── notes/
    ├── bdi_design.md          # BDI architecture design + Mesa gap analysis
    ├── mesa_issues.md         # Mesa GitHub issue/discussion research
    └── proposal_ideas.md      # Gap → deliverable table, timeline, proposal outline
```

---

## Running the Models

```bash
pip install -r requirements.txt

cd models/schelling   && python run.py   # Schelling Segregation
cd models/wolf_sheep  && python run.py   # Wolf-Sheep Predator-Prey
cd models/wealth      && python run.py   # Wealth Distribution
cd models/bdi_agents  && python run.py   # BDI Agent prototype
cd models/rl_agent    && python run.py   # RL Agent (Q-Learning)
```

---

## Notes

- All models target **Mesa 3.x** — no `unique_id`, `AgentSet.shuffle_do()` instead of scheduler
- Pain points are numbered to match cross-references in model READMEs and `motivation.md`
- `bdi_base.py` is a standalone reusable base class — zero Mesa internals, composable with any Mesa agent
