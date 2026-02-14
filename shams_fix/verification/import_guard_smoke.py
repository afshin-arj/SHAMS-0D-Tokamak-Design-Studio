"""Smoke test: importing UI modules must not execute Streamlit calls at import-time."""
def test_import_concept_opt_cockpit():
    import ui.concept_opt_cockpit  # noqa: F401

def test_import_physics_panel():
    import ui.physics_panel  # noqa: F401
