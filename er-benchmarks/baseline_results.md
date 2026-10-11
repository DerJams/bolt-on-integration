# Entity-resolution fuzzy baseline results

Run date: 2026-10-11

Command (from repo root `C:\Users\James\bolt-on-integration`): `uv run --with rapidfuzz --with pandas python -I scripts/er_baseline.py`

Method: rapidfuzz `fuzz.token_set_ratio` on one name/title field with `utils.default_process` (lowercase, strip non-alphanumerics), full left x right score matrix via `process.cdist`, top-1 right record per left record as the block, predicted match when the top-1 score >= threshold. Precision, recall and F1 are computed against the gold perfect mapping. The top-1 recall ceiling is the recall at threshold 0, i.e. the share of gold pairs that top-1 blocking can find at all.

## Best threshold per dataset

| Dataset | Fields (left vs right) | Left | Right | Gold pairs | Best threshold | Precision | Recall | F1 | Top-1 recall ceiling |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Abt-Buy | name vs name | 1081 | 1092 | 1097 | 55 | 0.685 | 0.673 | 0.679 | 0.673 |
| Amazon-Google | title vs name | 1363 | 3226 | 1300 | 65 | 0.584 | 0.594 | 0.589 | 0.598 |
| DBLP-ACM | title vs title | 2616 | 2294 | 2224 | 90 | 0.939 | 0.957 | 0.948 | 0.960 |

## Abt-Buy sweep

Files: `abt-buy/Abt.csv` (1081 records) vs `abt-buy/Buy.csv` (1092 records). Decoded as: Abt.csv=cp1252, Buy.csv=utf-8, abt_buy_perfectMapping.csv=utf-8. Gold pairs: 1097 (rows in file: 1097, pairs referencing ids absent from the tables: 0).

| Threshold | Predicted | TP | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|
| 50 | 1081 | 738 | 0.683 | 0.673 | 0.678 |
| 55 | 1077 | 738 | 0.685 | 0.673 | 0.679 |
| 60 | 1066 | 732 | 0.687 | 0.667 | 0.677 |
| 65 | 1019 | 712 | 0.699 | 0.649 | 0.673 |
| 70 | 975 | 685 | 0.703 | 0.624 | 0.661 |
| 75 | 874 | 623 | 0.713 | 0.568 | 0.632 |
| 80 | 752 | 549 | 0.730 | 0.500 | 0.594 |
| 85 | 594 | 445 | 0.749 | 0.406 | 0.526 |
| 90 | 395 | 323 | 0.818 | 0.294 | 0.433 |
| 95 | 205 | 186 | 0.907 | 0.170 | 0.286 |

## Amazon-Google sweep

Files: `amazon-google/Amazon.csv` (1363 records) vs `amazon-google/GoogleProducts.csv` (3226 records). Decoded as: Amazon.csv=cp1252, GoogleProducts.csv=cp1252, Amzon_GoogleProducts_perfectMapping.csv=utf-8. Gold pairs: 1300 (rows in file: 1300, pairs referencing ids absent from the tables: 0).

| Threshold | Predicted | TP | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|
| 50 | 1362 | 777 | 0.570 | 0.598 | 0.584 |
| 55 | 1355 | 777 | 0.573 | 0.598 | 0.585 |
| 60 | 1342 | 774 | 0.577 | 0.595 | 0.586 |
| 65 | 1323 | 772 | 0.584 | 0.594 | 0.589 |
| 70 | 1292 | 760 | 0.588 | 0.585 | 0.586 |
| 75 | 1223 | 728 | 0.595 | 0.560 | 0.577 |
| 80 | 1155 | 696 | 0.603 | 0.535 | 0.567 |
| 85 | 1061 | 647 | 0.610 | 0.498 | 0.548 |
| 90 | 944 | 594 | 0.629 | 0.457 | 0.529 |
| 95 | 828 | 525 | 0.634 | 0.404 | 0.493 |

## DBLP-ACM sweep

Files: `dblp-acm/DBLP2.csv` (2616 records) vs `dblp-acm/ACM.csv` (2294 records). Decoded as: DBLP2.csv=cp1252, ACM.csv=utf-8, DBLP-ACM_perfectMapping.csv=utf-8. Gold pairs: 2224 (rows in file: 2224, pairs referencing ids absent from the tables: 0).

| Threshold | Predicted | TP | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|---:|
| 50 | 2616 | 2136 | 0.817 | 0.960 | 0.883 |
| 55 | 2611 | 2136 | 0.818 | 0.960 | 0.884 |
| 60 | 2567 | 2135 | 0.832 | 0.960 | 0.891 |
| 65 | 2518 | 2135 | 0.848 | 0.960 | 0.900 |
| 70 | 2449 | 2135 | 0.872 | 0.960 | 0.914 |
| 75 | 2372 | 2135 | 0.900 | 0.960 | 0.929 |
| 80 | 2315 | 2135 | 0.922 | 0.960 | 0.941 |
| 85 | 2287 | 2134 | 0.933 | 0.960 | 0.946 |
| 90 | 2266 | 2128 | 0.939 | 0.957 | 0.948 |
| 95 | 2245 | 2112 | 0.941 | 0.950 | 0.945 |
