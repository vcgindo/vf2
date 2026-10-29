"""Metadata-only selection of an already accepted daily closing state."""


def latest_predecessor(candidates):
    """Return the unique latest eligible run, or None when none exists.

    Intake supplies successful same-source daily runs strictly before the
    requested date. Calendar gaps do not create transactions to replay.
    """
    latest = None
    latest_count = 0
    for candidate in candidates:
        if latest is None or candidate.business_date > latest.business_date:
            latest = candidate
            latest_count = 1
        elif candidate.business_date == latest.business_date:
            latest_count += 1
    if latest_count > 1:
        raise ValueError('A unique successful own native day on the latest prior date is required')
    return latest
