# Rules for the fill run (synthetic layer)

Set by the repo owner on 2026-10-11. These apply on top of the fill prompt when it is run as a seeded Python script in a later session.

1. Partition is constrained random: seeded draw, re-draw until at least 15 natural duplicate pairs are split across entities and at least 15 kept together. Record attempts.
2. Split dev/holdout by entity cluster, not by record, so no pair crosses folders.
3. Injection rates are 2 to 8 percent of records per domain per entity, counted after partition.
4. Citations may be "prompt-specified" for the seed, rates, and split ratio.
5. Use the system date for the manifest, computed in code.
6. SHA-256 computed by the script, not by the model.
7. Do not fill the "must be injected" column in `spec/defect_taxonomy.md`. The repo owner fills it.
