# Open-Loop vs Closed-Loop Control Toggle

**Project:** ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch

**Overall Progress:** `100%` *(4 of 4 steps complete)*

## TLDR

Add a **Controls toggle** that switches the dispatch controller between **closed-loop** (default: verify-then-actuate with physical feedback) and **open-loop** (score-only dispatch, no verification gate). Same UI still shows failed checks in open-loop mode so viva demos can contrast unsafe cyber-only control vs CPS-safe closed-loop control.

---

## Critical Decisions

- **Default: closed-loop ON** — Normal demo behavior unchanged; toggle off only for contrast demos.
- **Open-loop winner rule** — Highest-scoring **available** resource wins; verification results are computed and displayed but not used to block actuation.
- **Trace metadata** — Store `controlMode: "closed" | "open"` on each trace for Latest allocation copy and session restore.
- **No backend changes** — Client-side only in `index.html`.

---

## Tasks

- [x] 🟩 **Step 1: State + Controls UI**
  - [x] 🟩 `state.closedLoopControl = true`; checkbox in Controls panel
  - [x] 🟩 Persist in `serializeLiveState` / `restoreLiveSession`; reset on `resetDemo`

- [x] 🟩 **Step 2: Allocation logic**
  - [x] 🟩 `isClosedLoop()`, `findActuationWinner(bids)` helpers
  - [x] 🟩 Closed-loop: `bids.find(bid => bid.score.canCommit)` + repair note
  - [x] 🟩 Open-loop: first available top-scorer; no repair path

- [x] 🟩 **Step 3: Trace + Latest allocation UI**
  - [x] 🟩 `controlMode` on trace; open-loop outcome text
  - [x] 🟩 Chips, explainer, verification banner when open-loop bypassed checks
  - [x] 🟩 Control mode badge on physical plant header

- [x] 🟩 **Step 4: Validation**
  - [x] 🟩 Closed-loop (default): unchanged verify-then-actuate
  - [x] 🟩 Open-loop: pending incidents assign despite failed ETA/fuel checks; UI shows warning

---

## Viva demo script

1. **Closed-loop (checked):** Start scenario → show actuation blocked or repair when ETA fails.
2. **Uncheck closed-loop:** Reset → Start → same incident assigns top scorer with failed checks visible + **Open loop** chip.
3. **One line:** *Open-loop ignores feedback; closed-loop uses verification as a control interlock before actuation.*
