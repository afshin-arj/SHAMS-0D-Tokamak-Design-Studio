from __future__ import annotations

import json

from src.nuclear_data.intake import (
    canonical_dataset_json,
    dataset_from_json,
    dataset_from_metadata_and_csv,
    parse_metadata_json,
    parse_sigma_removal_csv,
)


def test_v408_parse_metadata_json() -> None:
    md = parse_metadata_json(
        json.dumps(
            {
                "dataset_id": "TEST_V408",
                "source_label": "unit",
                "source_version": "0.1",
                "processing_notes": "pytest",
                "group_structure_id": "G6_V407",
            }
        )
    )
    assert md.dataset_id == "TEST_V408"
    assert md.group_structure_id == "G6_V407"


def test_v408_parse_sigma_removal_csv() -> None:
    csv_text = "material,g1,g2,g3,g4,g5,g6\nSS316,1,2,3,4,5,6\n"
    sigma = parse_sigma_removal_csv(csv_text, n_groups=6)
    assert "SS316" in sigma
    assert len(sigma["SS316"]) == 6


def test_v408_dataset_from_metadata_and_csv() -> None:
    md_json = json.dumps(
        {
            "dataset_id": "INTAKE_V408",
            "source_label": "pytest",
            "source_version": "1",
            "processing_notes": "csv path",
            "group_structure_id": "G6_V407",
        }
    )
    csv_text = "material,g1,g2,g3,g4,g5,g6\nW,0.1,0.2,0.3,0.4,0.5,0.6\n"
    spectrum = [0.1, 0.1, 0.2, 0.2, 0.2, 0.2]
    tbrw = [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    ds = dataset_from_metadata_and_csv(md_json, csv_text, spectrum, tbrw)
    assert ds.dataset_id == "INTAKE_V408"
    assert "W" in ds.sigma_removal_1_m
    text = canonical_dataset_json(ds)
    roundtrip = dataset_from_json(text)
    assert roundtrip.dataset_id == ds.dataset_id
