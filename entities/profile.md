# Entity profile: naturally occurring messiness

Generated 2026-10-11 by `scripts/profile_entities.py` from `entities/recipient_records.csv`. Every count below is a real condition in the downloaded USAspending records. Nothing has been injected.

## Population

| measure | value |
|---|---:|
| record variants (rows) | 8,800 |
| unique recipient UEIs | 4,035 |
| UEIs with more than one record variant | 1,582 (39.2%) |
| max record variants for one UEI | 41 |

UEIs by NAICS group (a UEI can appear in more than one):

| NAICS group | UEIs |
|---|---:|
| 2382 | 2,743 |
| 5613 | 301 |
| 6211 | 685 |
| 6212 | 69 |
| 6213 | 432 |

## Same identifier, different master-record content (natural duplicates)

A *natural duplicate pair* is two record variants that share a UEI. There are **18,567** such pairs.

| condition | UEIs affected | share of UEIs |
|---|---:|---:|
| raw legal name spelled more than one way | 537 | 13.3% |
| ...and still different after suffix/punctuation normalization | 245 | 6.1% |
| more than one address (after abbreviation normalization) | 591 | 14.6% |
| address differs only in formatting | 26 | 0.6% |
| more than one DUNS | 0 | 0.0% |
| more than one CAGE code | 0 | 0.0% |
| more than one parent UEI over time | 129 | 3.2% |
| business-type flags disagree across records | 1,211 | 30.0% |

## Name forms within a record

| condition | records | share of records |
|---|---:|---:|
| raw name differs from USAspending-normalized name | 3,451 | 39.2% |
| DBA name present | 660 | 7.5% |
| DBA present and materially different from legal name | 551 | 6.3% |
| name contains lowercase letters (mixed case) | 0 | 0.0% |

## Different identifiers, similar entity (cross-UEI)

| condition | groups | UEI pairs |
|---|---:|---:|
| identical normalized name, different UEIs | 67 | 154 |
| near-duplicate names (token_sort_ratio >= 92), no shared UEI | n/a | 39 |
| same normalized street address + ZIP5, different UEIs | 99 | 135 |

These are not resolved here. Some are the same business re-registered, some are distinct franchisees or sibling entities, some are unrelated firms in a shared building.

## Corporate hierarchy

| condition | value |
|---|---:|
| UEIs reporting a parent UEI different from their own | 436 (10.8%) |
| child-parent pairs where the parent is also in this record set | 54 |
| ...where the child's reported parent name does not match the parent's own legal name | 16 |
| parents with two or more child UEIs in the set (sibling groups) | 40 |

## Missing and partial fields

| field | blank records | share |
|---|---:|---:|
| recipient_uei | 0 | 0.0% |
| recipient_duns | 2,203 | 25.0% |
| cage_code | 5,766 | 65.5% |
| recipient_doing_business_as_name | 8,140 | 92.5% |
| recipient_parent_uei | 13 | 0.1% |
| recipient_parent_name | 8 | 0.1% |
| recipient_address_line_1 | 1 | 0.0% |
| recipient_address_line_2 | 8,665 | 98.5% |
| recipient_city_name | 0 | 0.0% |
| recipient_county_name | 3,047 | 34.6% |
| recipient_zip_4_code | 0 | 0.0% |
| business_types | 343 | 3.9% |
| ZIP is 5-digit only (no +4) | 694 | 7.9% |

Primary identifier: 0 records have a blank `recipient_uei`. The 13 blank `recipient_parent_uei` values are natural data and are kept as published.

UEIs flagged as sole proprietorships: 547. Their recipient names may be personal names of practitioners, as published by USAspending.

## Examples (real, shown for orientation only)

- UEI `C36EHHSMQGH7`: MANPOWER INC. / MANPOWER INCORPORATED (2779)
- UEI `C53JNV2EWNS5`: UNITED NURSING INTERNATIONAL LIMITED LIABILITY COMPANY / UNITED NURSING INTERNATIONAL LLC
- UEI `CBZQS14ZCDL3`: GIGA ELECTRICAL & TECHNICAL SERVICES INC / GIGA ELECTRICAL AND TECHNICAL SERVICES INC.
- UEI `CD97KTAPPEY7`: RESA POWER SOLUTIONS - TRANSFORMER SERVICES, LLC / TRANSFORMER TESTING & REPAIR, INC.
- UEI `CJXLJMB8S231`: NUGENERATION TECHNOLOGIES LLC / NUGENERATION TECHNOLOGIES, LLC

- near-duplicate across UEIs (100): `COUNTY OF LOS ANGELES` vs `LOS ANGELES COUNTY OF`
- near-duplicate across UEIs (100): `COUNTY OF YOLO` vs `YOLO COUNTY OF`
- near-duplicate across UEIs (97): `REGENTS OF UNIVERSITY OF CALIFORNIA 6493` vs `REGENTS OF UNIVERSITY OF CALIFORNIA 6494`
- near-duplicate across UEIs (96): `HM CONSTRUCTION` vs `HMS CONSTRUCTION`
- near-duplicate across UEIs (95): `AIRCO COMMERCIAL SERVICES` vs `COMMERCIAL AIR SERVICES`

## Implication for the defect taxonomy

Rows in `spec/defect_taxonomy.md` cite these sections in the column "present naturally in real data?". A condition with a non-trivial count above is present naturally. Whether it must also be injected is left to the repo owner (`[FILL]`).
