"""Persisted historical action-policy identities, without action selection.

These finite names validate existing opening provenance. Automatic trial
Apply/Sleep selection is development-only; ordinary business commands do not
use this module.
"""
POLICY = 'own-recommendations-daily-apply-retained-sleep-v1'
ELIGIBLE_SLEEP_POLICY = 'own-recommendations-apply-eligible-retained-sleep-v1'
POLICIES = (POLICY, ELIGIBLE_SLEEP_POLICY)


def require_policy_identity(profile):
    value = profile.get('synthetic_action_policy', POLICY)
    if value not in POLICIES:
        raise ValueError('Unrecognized explicit action policy')
    return value
