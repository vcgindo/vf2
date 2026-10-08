"""Issue real cookie JWT material for the two persisted Cohort3 proof actors."""
from django.conf import settings


ACTORS = frozenset((2, 3))


def issue_actor_tokens(actor_id):
    """Use the retained issuer; the caller keeps returned tokens private."""
    if not getattr(settings, 'VF_COHORT3_OWNED_INPROCESS', False) or actor_id not in ACTORS:
        raise ValueError('Cohort3 token issuance is limited to persisted actors2/3')
    from api.models import User
    actor = User.all_objects.using('identity').get(
        pk=actor_id, is_active=True, is_admin=False, is_deleted=False)
    from api.view.auth import get_tokens_for_user
    return get_tokens_for_user(actor)
