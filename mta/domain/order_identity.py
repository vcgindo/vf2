"""Approved production identity ordering; no claim of canonical insertion parity."""

CONTRACT = 'preserved-feed-row-ordinary-before-spike-v1'
ELEPHANT_CONTRACT = 'persisted-elephant-ordinal-before-feed-ordinary-spike-v1'
QUALIFICATION = 'APPROVED_PRODUCTION_CONTRACT_CHANGE'
MAX_KEY = 2147483647


def counter(value):
    if type(value) is not int or not 1 <= value <= MAX_KEY:
        raise ValueError('Explicit positive signed32 order identity counter required')
    return value


def next_keys(last_value, count):
    """Check complete capacity before assigning any row; deleted keys are not reused."""
    counter(last_value)
    if type(count) is not int or count < 0:
        raise ValueError('Nonnegative generated order count required')
    if count > MAX_KEY-last_value:
        raise ValueError('SQL order identity exhausted')
    return range(last_value+1, last_value+count+1)
