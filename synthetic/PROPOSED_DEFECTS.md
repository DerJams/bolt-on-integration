# Proposed defects (not applied)

Written by `scripts/generate_synthetic.py`. Nothing here is injected or labelled with a taxonomy outcome.

## Different UEIs sharing one normalized street address and ZIP

- Observed: 99 groups, 135 UEI pairs (`entities/profile.md`). The taxonomy lists it under "observed in real data but
  described by no evidence extract".
- Why it matters here: the profile says these are unresolved (re-registered businesses, franchisees, firms in a shared
  building). The repo owner gave the same reason for marking CV06 pairs "unknown". The answer key therefore marks these
  pairs `unknown` in `record_pairs.csv` (pair_basis `same_address`), gives them no decision label, and scoring excludes
  them from pairwise precision and recall.
- Needed before it becomes a row: an evidence extract describing shared-address entities in master-data consolidation,
  and a decision by the repo owner.
