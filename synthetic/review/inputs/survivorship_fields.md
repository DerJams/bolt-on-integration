# Record fields available for choosing a golden record

Each customer or vendor master row carries the fields below (`schemas/entity_master.md`). Identity clusters span
the four entities' masters. In track B (no-shared-identifier) the five identifier fields are withheld from the
system under test; they are listed here because the answer key's golden record carries them.

| field | content | in track B inputs |
|---|---|---|
| `record_id` | benchmark record id; the prefix names the entity master (PLT, AOA, AOB, AOC) | yes |
| `recipient_uei` | Unique Entity Identifier (12 characters) | no |
| `recipient_duns` | legacy DUNS number; blank on records after 2022 | no |
| `cage_code` | CAGE code | no |
| `recipient_name` | legal name, USAspending-normalized | yes |
| `recipient_name_raw` | legal name as submitted | yes |
| `recipient_doing_business_as_name` | trading (DBA) name | yes |
| `recipient_parent_uei` | parent entity UEI | no |
| `recipient_parent_duns` | parent entity DUNS | no |
| `recipient_parent_name` | parent entity name, normalized | yes |
| `recipient_parent_name_raw` | parent entity name as submitted | yes |
| `recipient_address_line_1` | street address | yes |
| `recipient_address_line_2` | address line 2 | yes |
| `recipient_city_name` | city | yes |
| `recipient_county_name` | county | yes |
| `recipient_state_code` | state | yes |
| `recipient_zip_4_code` | ZIP or ZIP+4 | yes |
| `recipient_country_code` | country | yes |
| `business_types` | `;`-joined business-type flags | yes |
| `organizational_type` | organizational type | yes |
| `naics_codes` | `;`-joined NAICS codes over the entity's awards | yes |
| `n_awards` | number of awards behind the record | yes |
| `first_seen` | earliest award date behind the record | yes |
| `last_seen` | latest award date behind the record | yes |
