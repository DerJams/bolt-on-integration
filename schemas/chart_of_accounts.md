# Schema: chart of accounts

Applies to every CSV in `coa/`.

| column | type | meaning | evidence that the field matters |
|---|---|---|---|
| gl_code | string | account code as published by the source chart; blank when the source publishes no codes | GL code decisions in CoA mapping: `evidence/pmistack_erp_consolidation.md` |
| account_name | string | account name as published | name and definition differences across ERPs: `evidence/houseblend_netsuite_100day.md` |
| account_type | string | the source chart's own type or class label (not harmonised) | same |
| normal_balance | `debit` / `credit` / blank | as published, or derived from account_type by the standard rule (see `coa/README.md` for which) | n/a |
| description | string | source description, if any | n/a |
| parent_code | string | parent account or group code where the source has a hierarchy | legal-entity and account hierarchy: `evidence/houseblend_netsuite_100day.md` |

No mapping columns exist in `coa/`. Mappings are produced only by the later synthetic pass, under `synthetic/`.
