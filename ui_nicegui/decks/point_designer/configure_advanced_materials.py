"""Advanced materials / nuclear inputs — v403 stack, v407 dataset, v399 mix."""
from __future__ import annotations

from nicegui import ui

from ui_nicegui.session import DesignSession


def _knob_str(session: DesignSession, key: str, default: str = "") -> str:
    v = session.knobs.get(key, default)
    return str(v) if v is not None else default


def render_advanced_materials(session: DesignSession, *, embedded: bool = False) -> None:
    def _body() -> None:
        ui.label(
            "Text/JSON fields for library-backed authorities. Enable matching overlays in the master toggle list."
        ).classes("text-caption q-mb-sm")

        if bool(session.overlay.get("include_impurity_v399", False)):
            ui.textarea(
                label="Multi-species impurity mix JSON",
                value=_knob_str(session, "impurity_mix_json_v399", "{}"),
                on_change=lambda e: session.knobs.__setitem__("impurity_mix_json_v399", e.value),
            ).props("outlined dense rows=3").classes("w-full")

        if bool(session.overlay.get("include_neutronics_materials_library_v403", False)):
            ui.textarea(
                label="In-vessel materials stack JSON",
                value=_knob_str(session, "nm_stack_json_v403", ""),
                on_change=lambda e: session.knobs.__setitem__("nm_stack_json_v403", e.value),
            ).props("outlined dense rows=4").classes("w-full")

        if bool(session.overlay.get("include_nuclear_data_authority_v407", False)):
            ds_options = ["SCREENING_PROXY_V407", "CUSTOM_V407"]
            try:
                from src.nuclear_data.registry import list_registered_dataset_ids

                ids = list_registered_dataset_ids()
                if ids:
                    ds_options = list(ids)
            except Exception:
                pass
            cur = _knob_str(session, "nuclear_dataset_id_v407", ds_options[0])
            ui.select(
                ds_options,
                label="Nuclear dataset id",
                value=cur if cur in ds_options else ds_options[0],
                on_change=lambda e: session.knobs.__setitem__("nuclear_dataset_id_v407", str(e.value)),
            ).classes("w-full")
            ui.select(
                ["G6_V407", "G12_V407"],
                label="Group structure id",
                value=_knob_str(session, "nuclear_group_structure_id_v407", "G6_V407"),
                on_change=lambda e: session.knobs.__setitem__(
                    "nuclear_group_structure_id_v407", str(e.value)
                ),
            ).classes("w-full")

        if bool(session.overlay.get("include_neutronics_materials_authority_v401", False)):
            ui.select(
                ["OPTIMISTIC", "NOMINAL", "ROBUST"],
                label="Neutronics contract tier",
                value=str(session.knobs.get("nm_contract_tier_v401", "NOMINAL")),
                on_change=lambda e: session.knobs.__setitem__("nm_contract_tier_v401", str(e.value)),
            ).classes("w-full")
            ui.number(
                "Fragile margin fraction",
                value=float(session.knobs.get("nm_fragile_margin_frac_v401", 0.10)),
                min=0.0,
                max=0.5,
                step=0.01,
                on_change=lambda e: session.knobs.__setitem__("nm_fragile_margin_frac_v401", e.value),
            )

    if embedded:
        _body()
    else:
        with ui.expansion("Advanced materials & nuclear data inputs", icon="science").classes("w-full"):
            _body()
