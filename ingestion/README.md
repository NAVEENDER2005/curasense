# Ingestion

Mock HL7/FHIR-style data loaders. No real EHR credentials are used or required.

- `sample_data/fhir_bundle.json` - a synthetic FHIR `Bundle` (Patient, Encounter,
  DocumentReference, Claim resources) standing in for an Epic/Cerner export.
- `sample_data/payers.json` - payer master data.
- `sample_data/payer_policies.json` - synthetic payer policy documents, embedded
  by the AI layer for retrieval-augmented policy validation.
- `seed.py` - parses the files above and loads them into Postgres.

## Swapping in a real EHR feed

Replace the bundle read in `seed.py::run()` with a call to the hospital's FHIR
R4 endpoint (`GET /Patient`, `/Encounter`, `/DocumentReference`, `/Claim`,
typically via SMART-on-FHIR OAuth2). The resource shapes in `fhir_bundle.json`
intentionally mirror real FHIR fields (`identifier`, `name`, `birthDate`,
`period.start/end`, `diagnosisCodes`) so the parsing logic in `seed.py`
carries over with minimal changes - the main addition needed is OAuth2 token
handling and pagination over `Bundle.link[rel=next]`.

## Running

```bash
python db/migrate.py   # apply schema first
python ingestion/seed.py
```
