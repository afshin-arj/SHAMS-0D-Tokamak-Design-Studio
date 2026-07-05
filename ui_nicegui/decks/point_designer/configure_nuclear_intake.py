"""Nuclear dataset intake — external multi-group dataset builder."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.session import DesignSession


def _parse_vec_txt(txt: str) -> list[float]:
    return [float(x.strip()) for x in str(txt or "").split(",") if x.strip()]


def render_nuclear_dataset_intake(session: DesignSession) -> None:
    with ui.expansion("Nuclear dataset intake (external)", icon="upload_file").classes("w-full"):
        ui.label(
            "Import screening datasets into data/nuclear_datasets with SHA-256 provenance. "
            "Does not mutate frozen physics — registry intake only."
        ).classes("text-caption q-mb-sm")

        spectrum = ui.input(
            label="FW spectrum fractions (comma-separated, optional)",
            value="0.9,0.08,0.02",
        ).classes("w-full")
        tbrw = ui.input(
            label="TBR response weights (comma-separated, optional)",
            value="1.0,0.5,0.1",
        ).classes("w-full")

        json_payload = ui.textarea(label="Dataset JSON (single-file mode)").props(
            "outlined dense rows=4"
        ).classes("w-full")
        meta_payload = ui.textarea(label="Metadata JSON (CSV mode)").props(
            "outlined dense rows=3"
        ).classes("w-full")
        sigma_payload = ui.textarea(label="Sigma removal CSV text (CSV mode)").props(
            "outlined dense rows=3"
        ).classes("w-full")

        result_box = ui.textarea(value="").props("readonly outlined dense rows=6").classes("w-full")

        async def _build() -> None:
            try:
                from src.nuclear_data.intake import (
                    canonical_dataset_json,
                    dataset_from_json,
                    dataset_from_metadata_and_csv,
                )

                raw = (json_payload.value or "").strip()
                if raw:
                    ds = dataset_from_json(raw)
                else:
                    meta = (meta_payload.value or "").strip()
                    sigma = (sigma_payload.value or "").strip()
                    if not meta or not sigma:
                        raise ValueError("Provide dataset JSON, or metadata JSON + sigma CSV text")
                    ds = dataset_from_metadata_and_csv(
                        metadata_json_text=meta,
                        sigma_removal_csv_text=sigma,
                        spectrum_frac_fw=_parse_vec_txt(spectrum.value or ""),
                        tbr_response_weight=_parse_vec_txt(tbrw.value or ""),
                    )
                session.knobs["v408_built_dataset_id"] = str(getattr(ds, "dataset_id", ""))
                session.knobs["v408_built_dataset_sha256"] = str(getattr(ds, "sha256", ""))
                result_box.value = (
                    f"Validated OK\nSHA-256: {ds.sha256}\n\n"
                    + canonical_dataset_json(ds)[:4000]
                )
                ui.notify("Dataset validated.", type="positive")
            except Exception as exc:
                result_box.value = f"Intake failed: {exc}"
                ui.notify(str(exc), type="negative")

        async def _save() -> None:
            try:
                from src.nuclear_data.intake import dataset_from_json, canonical_dataset_json
                from src.nuclear_data.registry import build_dataset_evidence_card_md, save_external_dataset

                raw = (json_payload.value or "").strip()
                if not raw:
                    raise ValueError("Build/validate a JSON dataset first (single-file mode).")
                ds = dataset_from_json(raw)
                p = save_external_dataset(ds)
                (p.parent / f"{ds.dataset_id}.md").write_text(
                    build_dataset_evidence_card_md(ds), encoding="utf-8"
                )
                ui.notify(f"Saved to registry: {p.name}", type="positive")
            except Exception as exc:
                ui.notify(f"Save failed: {exc}", type="negative")

        with ui.row().classes("q-mt-sm gap-2"):
            ui.button("Build + validate", on_click=_build).props("outline")
            ui.button("Save to registry", on_click=_save).props("outline")
