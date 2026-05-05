CHANGE_TYPES = {"deprecation", "breaking", "enhancement", "bugfix", "security"}

BREAKING_RISK_LEVELS = {"critical", "high", "medium", "low", "none"}


def validate_classification(entry: dict) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"Classification entry must be a dict, got {type(entry).__name__}")

    change_type = entry.get("change_type")
    if change_type not in CHANGE_TYPES:
        raise ValueError(
            f"Invalid change_type {change_type!r} for entry {entry.get('entry_id')!r}. "
            f"Allowed: {sorted(CHANGE_TYPES)}"
        )

    breaking_risk = entry.get("breaking_risk")
    if breaking_risk not in BREAKING_RISK_LEVELS:
        raise ValueError(
            f"Invalid breaking_risk {breaking_risk!r} for entry {entry.get('entry_id')!r}. "
            f"Allowed: {sorted(BREAKING_RISK_LEVELS)}"
        )

    for flag in ("affects_auth", "affects_billing", "affects_data_model"):
        if not isinstance(entry.get(flag), bool):
            raise ValueError(
                f"Field {flag!r} must be a boolean for entry {entry.get('entry_id')!r}, "
                f"got {type(entry.get(flag)).__name__}"
            )
