# Mesa GitHub — Issues & Discussions Research

Date researched: 2026-03-22

---

## Key finding: `mesa.experimental.actions` already exists

**The most important thing I found:** Mesa is already building something that overlaps with pain point #9 (no multi-step plan mechanism). There is an `Actions` system in `mesa.experimental.actions` (PR #3461, discussion #3304) that provides:

- `Action` class — activities with duration, priority, callbacks
- Reward curves — map partial progress to completion (linear, all-or-nothing)
- Interruption handling — agents can pause actions with partial reward
- Optional `action_queue` for sequencing future actions

**Implication for proposal:** Don't propose building an IntentionQueue from scratch. Instead, propose *extending* the experimental Actions system toward BDI-compatible intentions — this is a much stronger framing (builds on existing work rather than duplicating it) and is more likely to land.

**What's still missing from the Actions system:**
- No belief store
- No desire/goal representation
- No deliberation logic (which desire to pursue given current beliefs)
- Behaviour selection is left entirely to users
- No partial observability integration

These gaps are exactly what the BDI layer should fill on top of the Actions foundation.

---

## Key discussion threads

### [#2927 — GSoC 2026 ideas](https://github.com/mesa/mesa/discussions/2927) ✅ Read
**Mentors say:**
- Build real models first, document pain points, then propose abstractions
- "Make existing complex behavior easier to implement" and "Allow new, previously impossible, behaviour"
- Evidence-driven proposals > theoretical design docs
- Rejected surface-level proposals; praised candidates who "built a small but non-trivial example model... and documented awkward patterns"
- Want to see: multi-step actions, competing priorities, continuous state changes

**Direct relevance:** This is exactly what we've been doing. The 5-model progression + 15-item pain points log is precisely the evidence base the mentors are asking for. This should be referenced prominently in the proposal.

### [#3304 — Actions: Event-driven agent behaviour](https://github.com/mesa/mesa/discussions/3304) ✅ Read
**Summary:** Mesa experimental has an `Action` class with duration and interruption semantics. Version 2 PR #3461 exists. Still unresolved: nested interrupts, idle detection, precondition re-checking.
**Pain point overlap:** #9 (IntentionQueue) — partially addressed by this work
**Proposal angle:** Extend actions toward BDI rather than replace them

### [#3559 — Behavioral Framework for Agent Models](https://github.com/mesa/mesa/discussions/3559)
**Posted by:** Khaled Saber (@1khaled-ctrl) — GSoC candidate
**Approach:** State machine (FSM) + BehaviorModule mixin
**Status:** No mentor replies yet
**Note:** See `reviews/review_1khaled-ctrl.md` for peer review

### [#3561 — GSoC 2026: Behavioral Framework (microgrid + RL)](https://github.com/mesa/mesa/discussions/3561)
Unanswered. Another candidate taking a domain-specific angle (microgrid energy management + RL). Worth reading for scope comparison.

### [#3595 — Exploring Trigger-Based Behavioral Patterns in Mesa](https://github.com/mesa/mesa/discussions/3595)
Posted 2026-03-22. Zero comments. May be another candidate.

---

## Pain points vs existing issues

| Our pain point | Existing Mesa issue/discussion |
|----------------|-------------------------------|
| #9 — no IntentionQueue | **Partially addressed**: `mesa.experimental.actions` (#3304, #3461) |
| #10 — no partial observability | **Not found** — no open issue |
| #11 — `agents_by_type` KeyError | **Not found** — worth filing a bug report |
| #2 — stepping order undocumented | **Not found** — worth a docs PR |
| #4 — DataCollector performance | **Not found** — good discussion candidate |

---

## Actions to take before proposal deadline

- [ ] Read `mesa.experimental.actions` source code — understand what's already built
- [ ] Comment on #2927 (GSoC ideas thread) — introduce yourself, link this repo
- [ ] Post on #3304 (Actions discussion) — note that pain point #9 maps to this, and describe how BDI deliberation layer would sit on top
- [ ] Open new issue for pain point #10 (partial observability) — not currently tracked
- [ ] Open new issue or comment for pain point #11 (`agents_by_type` KeyError) — small fix, good first contribution opportunity

---

## Notes on proposal framing

The mentor quote that matters most:
> "Make existing complex behavior easier to implement" and "Allow new, previously impossible, behaviour."

Our proposal should frame every deliverable against one of those two criteria. For example:
- IntentionQueue → makes multi-step plans easier (criterion 1)
- BeliefStore → enables new: belief-conditional replanning (criterion 2)
- Partial observability → enables new: emergent information asymmetry (criterion 2)
- RL mixin → enables new: adaptive policies (criterion 2)
