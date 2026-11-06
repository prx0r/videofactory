"""Ship success criteria (versioned — new thresholds mean a new version).

tantrasara-ship-v1: a unit ships (finals + R2 + seal candidacy) iff EVERY
criterion is TRUE on measured artifacts. UNKNOWN (missing evidence) never
ships — it schedules evidence collection, never a waiver-by-default.
"""
SHIP_CRITERIA_VERSION = 'tantrasara-ship-v1'

# strict: no single white hold past 60s, measured from part render_meta
# hold entries (MMS-timed, not estimates). Estimates gate pre-render
# (hold-scan); this gates the ship on what actually rendered.
MAX_WHITE_SPAN_S = 60.0

# entries integrity tolerance: sum(entry durs) vs meta duration (ffprobe).
ENTRIES_DURATION_TOL_S = 2.0

CRITERIA = (
    # id, kind, description
    ('ship/verified-v1', 'gate', 'sha-bound verification PASS for these exact bytes'),
    ('ship/max-white-span-v1', 'measured', 'max single white span <= 60s across part entries (boundary-merged)'),
    ('ship/geometry-proven-v1', 'measured', 'every part meta validates and matches current inputs (gate ran on these bytes)'),
    ('ship/review-current-v1', 'gate', 'review pack current for this data'),
    ('ship/ears-v1', 'gate', 'owner ears decision bound to these exact bytes'),
    ('ship/issues-clear-v1', 'gate', 'no open block/needs-owner issues (waivers explicit)'),
)
