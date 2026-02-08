# Radiation Source Catalog (Authoritative Tier)

SHAMS ships with a lightweight **proxy** Lz(Te) table for scoping and UI continuity.
For *publication-grade* radiation claims, SHAMS supports an **authoritative tier** in which you supply
an immutable Lz(Te) database derived from **OpenADAS** (ADAS) via a documented pipeline (e.g. **RADAS**).

## What SHAMS expects

A single JSON file containing (minimum):

```json
{
  "meta": { "source": "...", "date": "...", "notes": "..." },
  "species": {
    "C":  { "Te_keV": [ ... ], "Lz_W_m3": [ ... ] },
    "NE": { "Te_keV": [ ... ], "Lz_W_m3": [ ... ] }
  }
}
```

* `Te_keV` must be strictly increasing.
* `Lz_W_m3` is the **zero-density** radiated power coefficient in **W·m^3**.

SHAMS will record **SHA256** of the file in every Point Designer artifact
(`radiation_db_sha256`) to make reviewer verification trivial.

## Recommended pipeline (RADAS → SHAMS)

1. Use RADAS to generate a NetCDF dataset from OpenADAS.
2. Convert NetCDF → SHAMS JSON using the helper script:
   `tools/radiation/convert_radas_netcdf_to_shams_lz_json.py`
3. Place the resulting JSON into:
   `src/data/radiation/lz_tables_radas_openadas_v1.json`

Then select **Lz(Te) database = radas_openadas_v1** in the Point Designer UI.

## Citations (for papers / reports)

When you publish, cite at minimum:
- OpenADAS / ADAS Project (data source)
- RADAS (pipeline/tooling), plus the exact SHAMS SHA256 recorded in artifacts.

