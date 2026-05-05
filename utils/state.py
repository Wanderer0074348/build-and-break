STAGES = [
    "INIT",
    "SOURCES_LOADED",
    "CHANGELOGS_FETCHED",
    "ENTRIES_PARSED",
    "RECENT_ENTRIES_FILTERED",
    "CHANGES_CLASSIFIED",
    "HIGH_RISK_STRIPE_CHANGES_SELECTED",
    "CODEBASE_IMPACT_ANALYSED",
    "MIGRATION_GUIDES_GENERATED",
    "MIGRATION_CODE_VALIDATED",
    "IMPACT_REPORT_WRITTEN",
    "OPTIONAL_OUTPUTS_GENERATED",
    "VALIDATION_COMPLETE",
    "RESULTS_FINALISED",
]


class PipelineState:
    def __init__(self):
        self.current = None
        self._index = -1

    def advance(self, stage_name: str) -> None:
        if stage_name not in STAGES:
            raise RuntimeError(f"Unknown stage: {stage_name}")
        expected_index = self._index + 1
        if expected_index >= len(STAGES):
            raise RuntimeError(
                f"Cannot advance past final stage. Current: {self.current}, requested: {stage_name}"
            )
        expected = STAGES[expected_index]
        if stage_name != expected:
            raise RuntimeError(
                f"Stage out of order. Expected {expected!r}, got {stage_name!r}. Current: {self.current!r}"
            )
        self.current = stage_name
        self._index = expected_index
