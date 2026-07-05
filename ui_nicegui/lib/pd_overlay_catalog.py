"""Authority / engineering overlay toggles for Point Designer Configure."""

from __future__ import annotations



from typing import List, Tuple



from ui_nicegui.lib.pd_panel_labels import (

    OVERLAY_GROUP_SPECS,

    overlay_display_label,

    overlay_group_title,

)



# (group title, [(session.overlay key, display label, default)])

OVERLAY_GROUPS: List[Tuple[str, List[Tuple[str, str, bool]]]] = [

    (

        overlay_group_title(group_id),

        [(key, overlay_display_label(key), default) for key, default in items],

    )

    for group_id, items in OVERLAY_GROUP_SPECS

]



ALL_OVERLAY_KEYS = [k for _, items in OVERLAY_GROUP_SPECS for k, _ in items]





def seed_overlay_defaults(overlay: dict) -> None:

    for _, items in OVERLAY_GROUP_SPECS:

        for key, default in items:

            overlay.setdefault(key, default)

