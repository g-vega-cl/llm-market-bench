# REMOVED — May 2026

The government incentive tracking feature (`is_government_incentive` field on MacroEvent,
`_validate_and_enrich_government_events()` in analysis.py, GOV-DETECT keyword matching,
UNFLAGGED POLICY EVENT warnings) was removed because the model-level flag was unreliable
and produced noise. The consensus `_is_vague_government_event()` helper remains for
synthesis quality control.
