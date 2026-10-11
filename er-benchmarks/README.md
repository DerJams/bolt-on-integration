# Entity-resolution benchmarks

Three real-world match problems from the Leipzig database group's benchmark collection, used here to test record-matching logic against published gold mappings. No synthetic data.

Landing page: https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution (checked 2026-10-11)

## Datasets

| Dataset | Folder | Source zip (downloaded 2026-10-11) | Left file (records) | Right file (records) | Gold file | Gold match pairs |
|---|---|---|---|---|---|---:|
| Abt-Buy | `abt-buy/` | https://dbs.uni-leipzig.de/files/datasets/Abt-Buy.zip | `Abt.csv` (1,081) | `Buy.csv` (1,092) | `abt_buy_perfectMapping.csv` | 1,097 |
| Amazon-Google | `amazon-google/` | https://dbs.uni-leipzig.de/files/datasets/Amazon-GoogleProducts.zip | `Amazon.csv` (1,363) | `GoogleProducts.csv` (3,226) | `Amzon_GoogleProducts_perfectMapping.csv` (filename misspelling is original) | 1,300 |
| DBLP-ACM | `dblp-acm/` | https://dbs.uni-leipzig.de/files/datasets/DBLP-ACM.zip | `DBLP2.csv` (2,616) | `ACM.csv` (2,294) | `DBLP-ACM_perfectMapping.csv` | 2,224 |

Record counts are rows parsed by pandas (multi-line quoted fields counted once). Every gold pair references ids present in both tables.

Fields:

- Abt-Buy: Abt `id, name, description, price`; Buy `id, name, description, manufacturer, price`.
- Amazon-Google: Amazon `id, title, description, manufacturer, price`; Google `id, name, description, manufacturer, price`.
- DBLP-ACM: both `id, title, authors, venue, year`.

## Provenance

The original zips are stored untouched in `../sources/er/`. Archive member dates are 2010-09-30.

| Zip | Bytes | SHA-256 |
|---|---:|---|
| Abt-Buy.zip | 134,745 | `b9ff2937d97371b7a00b0a97033213bfbdee24e8f1a0718a41ea8364472a8ff8` |
| Amazon-GoogleProducts.zip | 904,417 | `fcd72e223d51ce5b0d6b1d68034a438ba95cf2940431e209a57910b067cc4811` |
| DBLP-ACM.zip | 270,239 | `e37e7ed8e06722499e6d9e94583fdec279207b13ce6270a37595b6a5d594bc40` |

## Encoding notes

`Abt.csv`, `Amazon.csv`, `GoogleProducts.csv` and `DBLP2.csv` are not valid UTF-8 (ISO-8859-1 / Windows-1252). None of them contains bytes in 0x80 to 0x9F, so latin-1 and cp1252 decode them identically. `Buy.csv`, `ACM.csv` and the gold files are plain ASCII. The gold files use CRLF line endings. `scripts/er_baseline.py` tries UTF-8 first and falls back per file.

## Baseline

`../scripts/er_baseline.py` runs a rapidfuzz token-set-ratio baseline. Results, including the full threshold sweep, are in `baseline_results.md`.

## Citation

Hanna Köpcke, Andreas Thor, Erhard Rahm. Evaluation of entity resolution approaches on real-world match problems. Proceedings of the VLDB Endowment (PVLDB) 3(1-2): 484-493, 2010. doi:10.14778/1920841.1920904

```bibtex
@article{kopcke2010evaluation,
  author  = {K{\"o}pcke, Hanna and Thor, Andreas and Rahm, Erhard},
  title   = {Evaluation of entity resolution approaches on real-world match problems},
  journal = {Proceedings of the VLDB Endowment},
  volume  = {3},
  number  = {1-2},
  pages   = {484--493},
  year    = {2010},
  doi     = {10.14778/1920841.1920904}
}
```
