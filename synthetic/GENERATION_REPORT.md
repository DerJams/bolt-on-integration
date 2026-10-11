# Generation report

Generated 2026-10-11 by `scripts/generate_synthetic.py`, seed 3391519676 (`synthetic/SEED.txt`). Every number below is computed by the script. Holdout figures are counts only.

## Tracks

| track | name | identifier columns in the inputs | CV07 |
|---|---|---|---|
| `track_b` | no-shared-identifier (headline) | none: `recipient_uei`, `recipient_duns`, `cage_code`, `recipient_parent_uei`, `recipient_parent_duns` removed | not applicable |
| `track_a` | shared-identifier | all, `recipient_uei` blanked on CV07 records | 5% per domain per entity |

Both tracks share the seed, partition, dev/holdout split, entity clusters, sampled negatives and chart-of-accounts key. Record ids and row order differ between tracks, so ids cannot be joined across them.

## Partition (Task 1)

- Attempts until the constraint held: 1
- Natural duplicate pairs (same UEI) split across entities: 13,332; kept within one entity: 5,235 (minimum 15 each)
- Parent-child record pairs split: 527; kept: 211
- UEIs per domain: customer 2,037, vendor 1,998

## Records per entity and domain (both tracks)

| entity | domain | records | dev | holdout | dev share | CV07 injected (track A) | CV07 rate |
|---|---|---:|---:|---:|---:|---:|---:|
| PlatformCo | customer | 1,810 | 1,090 | 720 | 60.2% | 90 | 4.97% |
| PlatformCo | vendor | 1,764 | 1,068 | 696 | 60.5% | 88 | 4.99% |
| AddOnA | customer | 866 | 520 | 346 | 60.1% | 43 | 4.97% |
| AddOnA | vendor | 886 | 532 | 354 | 60.1% | 44 | 4.97% |
| AddOnB | customer | 907 | 553 | 354 | 61.0% | 45 | 4.96% |
| AddOnB | vendor | 867 | 526 | 341 | 60.7% | 43 | 4.96% |
| AddOnC | customer | 855 | 517 | 338 | 60.5% | 43 | 5.03% |
| AddOnC | vendor | 845 | 516 | 329 | 61.1% | 42 | 4.97% |

CV07 overall (track A): 438 of 8,800 records (4.98%); blank primary UEIs before injection: 0.

## Chart of accounts (both tracks)

COA05 (AddOn A, cash basis): 16 of 274 ledger accounts removed (5.84%); list in `synthetic/injection_log.json`. The system never sees those accounts, so the answer key scores them as 7 items, one per platform target account the cash-basis chart can no longer feed (`AddOnA::cash_basis::<target>`).

| folder | AddOn A | AddOn B | AddOn C | DIRECT | MANY_TO_ONE | SPLIT | REQUIRES_POLICY |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev | 159 | 108 | 32 | 30 | 149 | 14 | 106 |
| holdout | 106 | 72 | 22 | 16 | 115 | 4 | 65 |

Dev share of mapping rows per add-on: AddOnA 60.0%, AddOnB 60.0%, AddOnC 59.3%. The mapping key awaits independent review (`synthetic/review/`).

## Answer-key items: track_b (no-shared-identifier)

| folder | domain | records | clusters | match pairs | non-match pairs | unknown pairs | decision items | escalations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dev | customer | 2,680 | 1,212 | 5,398 | 5,681 | 620 | 11,784 | 1,623 |
| dev | vendor | 2,642 | 1,254 | 5,527 | 5,909 | 496 | 12,132 | 1,687 |
| dev | coa | | | | | | 299 | 106 |
| holdout | customer | 1,758 | 825 | 2,859 | 2,919 | 456 | 6,249 | 832 |
| holdout | vendor | 1,720 | 744 | 4,783 | 4,563 | 1,192 | 10,632 | 2,326 |
| holdout | coa | | | | | | 200 | 65 |

| folder | domain | AUTO_RESOLVE_MATCH | AUTO_RESOLVE_NON_MATCH | DO_NOT_MERGE_CONFLICTING_IDENTIFIER | ESCALATE_AMBIGUOUS | ESCALATE_POLICY_DECISION | MAP_REQUIRES_ACCOUNTING_POLICY |
|---|---|---:|---:|---:|---:|---:|---:|
| dev | customer | 4,512 | 5,649 | 225 | 1,006 | 392 | 0 |
| dev | vendor | 4,670 | 5,775 | 235 | 954 | 498 | 0 |
| holdout | customer | 2,604 | 2,813 | 143 | 327 | 362 | 0 |
| holdout | vendor | 3,834 | 4,472 | 1,001 | 1,003 | 322 | 0 |

## Answer-key items: track_a (shared-identifier)

| folder | domain | records | clusters | match pairs | non-match pairs | unknown pairs | decision items | escalations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| dev | customer | 2,680 | 1,212 | 5,398 | 5,681 | 620 | 11,926 | 2,019 |
| dev | vendor | 2,642 | 1,254 | 5,527 | 5,909 | 496 | 12,268 | 1,862 |
| dev | coa | | | | | | 299 | 106 |
| holdout | customer | 1,758 | 825 | 2,859 | 2,919 | 456 | 6,331 | 1,117 |
| holdout | vendor | 1,720 | 744 | 4,783 | 4,563 | 1,192 | 10,728 | 2,475 |
| holdout | coa | | | | | | 200 | 65 |

| folder | domain | AUTO_RESOLVE_MATCH | AUTO_RESOLVE_NON_MATCH | DO_NOT_MERGE_CONFLICTING_IDENTIFIER | ESCALATE_AMBIGUOUS | ESCALATE_POLICY_DECISION | MAP_REQUIRES_ACCOUNTING_POLICY |
|---|---|---:|---:|---:|---:|---:|---:|
| dev | customer | 4,874 | 5,033 | 201 | 1,424 | 394 | 0 |
| dev | vendor | 5,074 | 5,332 | 224 | 1,135 | 503 | 0 |
| holdout | customer | 2,634 | 2,580 | 135 | 618 | 364 | 0 |
| holdout | vendor | 4,336 | 3,917 | 863 | 1,283 | 329 | 0 |

Unknown pairs (same in both tracks): 2,764 record pairs. They come from 120 same-name and 46 near-name UEI pairs (CV06) and 100 same-address UEI pairs (not a taxonomy row; see `PROPOSED_DEFECTS.md`). Scoring leaves them out of pairwise precision and recall.

## Natural versus injected defect counts

Pair counts are record pairs. One pair can carry several CV tags.

| defect | origin | track A dev | track A holdout | track B dev | track B holdout |
|---|---|---:|---:|---:|---:|
| COA01 (mappings) | natural | 30 | 16 | 30 | 16 |
| COA02 (mappings) | natural | 149 | 115 | 149 | 115 |
| COA03 (mappings) | natural | 14 | 4 | 14 | 4 |
| COA05 (mappings) | injected | 5 | 2 | 5 | 2 |
| COA07 (mappings) | natural | 5 | 9 | 5 | 9 |
| COA08 (mappings) | natural | 39 | 26 | 39 | 26 |
| COA09 (mappings) | natural | 57 | 28 | 57 | 28 |
| CV01 (pairs) | natural | 1,077 | 706 | 1,077 | 706 |
| CV02 (pairs) | natural | 7,828 | 5,504 | 7,828 | 5,504 |
| CV03 (pairs) | natural | 2,441 | 1,767 | 2,441 | 1,767 |
| CV04 (pairs) | natural | 1,743 | 1,204 | 1,743 | 1,204 |
| CV05 (pairs) | natural | 4,566 | 2,850 | 4,566 | 2,850 |
| CV06 (pairs) | natural | 460 | 1,144 | 460 | 1,144 |
| CV07 (pairs) | injected | 2,085 | 1,607 | 0 | 0 |
| CV07 (records) | injected | 263 | 175 | 0 | 0 |
| CV08 (records) | natural | 217 | 126 | 217 | 126 |
| CV09 (pairs) | natural | 688 | 2,208 | 688 | 2,208 |
| CV10 (clusters) | natural | 745 | 497 | 724 | 487 |

## UEI links used for ground truth

Distinct UEI pairs: same normalized name 149, near-duplicate name 47, parent-child 54, siblings 307, same address 129. Precedence when one pair has several links: reported parent-child (non-match, CV09), then name similarity (unknown, CV06), then siblings (non-match, CV09), then shared address (unknown).

All 54 parent-child pairs are CV09 non-match: 24 with different names keep AUTO_RESOLVE_NON_MATCH, and 30 that also share a name are ESCALATE_POLICY_DECISION (repo owner, 2026-10-11). Those 30 were `unknown` (CV06) in the previous run.

These counts differ from `entities/profile.md` on purpose. The profile adds up UEI pairs per name or address group, so one pair can count twice, and it counts near-duplicates as name pairs. Here every UEI pair counts once.

## Track differences in labels

- CV07 exists only in track A. Its records and pairs are ESCALATE_AMBIGUOUS there.
- CV04 match pairs (trading name differs from legal name): AUTO_RESOLVE_MATCH in track A when both UEIs are visible; ESCALATE_AMBIGUOUS in track B, where no identifier is visible (repo owner, 2026-10-11).
- CV10 in track B uses only visible attributes (business types); parent-UEI conflicts count only in track A.

## Taxonomy rows not applied

- COA04 (legacy chart bloat): not applicable. The charts carry no usage data (`docs/injection_decisions.md`). On the v2 list.
- COA06 (revenue recognition basis): not applicable. It cannot be seen in a chart of accounts. On the v2 list.
- CV07: injected in track A only; not applicable to track B.
- All other rows except CV07 and COA05 are natural only, with no injection. COA01, COA02, COA03, COA07, COA08 and COA09 are tagged on mapping rows; CV01 to CV06 and CV09 on record pairs; CV08 on records; CV10 on clusters.
