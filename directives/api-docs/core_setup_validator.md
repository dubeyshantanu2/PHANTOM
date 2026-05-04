# Module core.setup_validator

## Function `validate_setup`
Performs a comprehensive validation of a potential trading setup.

Runs a series of ordered checks to ensure the setup adheres to all
trading rules and session constraints.

Args:
    setup (Dict[str, Any]): The setup data to validate.
    instrument (InstrumentConfig): Configuration for the traded instrument.

Returns:
    str: Validation status ("VALID", "INVALID", or "PENDING").
        - VALID: All criteria met.
        - INVALID: High-level failure (e.g., bias neutral, session ended).
        - PENDING: Intermediate state (e.g., sweep detected but FVG not yet formed).

