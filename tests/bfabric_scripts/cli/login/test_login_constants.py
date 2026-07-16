from __future__ import annotations

from bfabric_scripts.cli.login._constants import SCOPE_PRESETS


class TestScopePresets:
    def test_presets_are_minimal_use_case_sets(self):
        # Login presets deliberately omit the OIDC/groups scopes (those live in
        # DEFAULT_REGISTRATION_SCOPE for registration), and api:write implies api:read
        # server-side so read-write lists only api:write.
        assert [(p.name, p.scope) for p in SCOPE_PRESETS] == [
            ("read-only", "api:read"),
            ("read-write", "api:write"),
            ("upload", "api:write tus"),
        ]

    def test_every_preset_has_a_description(self):
        assert all(preset.description for preset in SCOPE_PRESETS)
