def validate_text(field, value):
    if not isinstance(value, str):
        raise ValueError(f'{field} must be text')

    value = value.strip()
    if not 1 <= len(value) <= 64:
        raise ValueError(f'{field} must have 1 to 64 characters')

    # Dozwolone znaki poza literami i cyframi.
    punctuation = " .,'’\"-():!?/"
    if any(not (char.isalnum() or char in punctuation) for char in value):
        raise ValueError(f'{field} contains unsupported characters')

    return value
