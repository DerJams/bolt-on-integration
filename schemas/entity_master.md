# Schema: customer and vendor master record

Applies to `entities/recipient_records.csv` and to any customer or vendor master later derived from it. Customer and vendor masters share one record shape, because both are drawn from the same real recipient pool.

## Fields present in the real data

| field | type | source column (USAspending contract award summary) | evidence that the field matters in integration |
|---|---|---|---|
| record_id | string `R#####` | assigned by `scripts/build_entities.py` (stable sort order) | n/a (benchmark key) |
| recipient_uei | string(12) | recipient_uei | tax/legal identifier standardisation: `evidence/pmistack_erp_consolidation.md` |
| recipient_duns | string(9) | recipient_duns (legacy identifier, blank after 2022) | same as above |
| cage_code | string(5) | cage_code | same as above |
| recipient_name | string | recipient_name (USAspending-normalized) | name standardisation: `evidence/pmistack_erp_consolidation.md` |
| recipient_name_raw | string | recipient_name_raw (as submitted) | same |
| recipient_doing_business_as_name | string | recipient_doing_business_as_name | same |
| recipient_parent_uei / _duns / _name / _name_raw | string | recipient_parent_* | legal-entity hierarchy: `evidence/houseblend_netsuite_100day.md` |
| recipient_address_line_1, _line_2, city, county, state, zip_4, country | string | recipient_* address columns | address standardisation: `evidence/pmistack_erp_consolidation.md` |
| business_types | `;`-joined flag names | business-type flag columns set to `t` | incomplete or conflicting supplier records: `evidence/estes_erp_pe_acquisitions.md` |
| organizational_type | string | organizational_type | same |
| naics_codes | `;`-joined | naics_code over all awards in the group | scope only |
| n_awards, first_seen, last_seen | int, date, date | count and min/max of award base and latest action dates | activity recency (no evidence row; descriptive only) |

## Fields named by evidence but absent from the real data

These cannot be populated from public records. A later pass must not invent values for them (README rule: transform real records only).

| field | named in |
|---|---|
| payment terms | `evidence/pmistack_erp_consolidation.md`, `evidence/houseblend_netsuite_100day.md`, `evidence/estes_erp_pe_acquisitions.md` |
| credit limit | `evidence/pmistack_erp_consolidation.md` |
| open AR/AP balances, aging | `evidence/consero_rollup_checklist.md`, `evidence/houseblend_netsuite_100day.md` |
| pricing rules, rebates | `evidence/estes_erp_pe_acquisitions.md` |
| critical-vendor flag | `evidence/consero_rollup_checklist.md` |

## Excluded on purpose

Phone and fax numbers and highly compensated officer names are in the source file and deliberately not copied into `entities/`.
