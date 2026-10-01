"""Selected GenericFunction permission-ID expansion, before normalized joins."""
from collections import Counter

PERMISSION_FIXTURE_SOURCE='BLOCK1_SYNTHETIC_PERMISSION'


class PermissionCodes(set):
    """Membership-compatible carrier retaining canonical auth join weights."""
    def __init__(self,counts):
        self.multiplicities=Counter(counts)
        super().__init__(key for key,value in self.multiplicities.items() if value>0)


def permission_multiplicity(codes,code):
    if codes is None: return 1
    if isinstance(codes,PermissionCodes): return codes.multiplicities.get(code,0)
    return int(code in codes)


def _sql_equal(left,right):
    # Selected case-insensitive SQL profile ignores trailing ASCII spaces for
    # VARCHAR equality. Expansion does not trim leading spaces.
    return left is not None and right is not None and str(left).rstrip(' ').casefold()==str(right).rstrip(' ').casefold()


def expand_permission_ids(records,assigned_ids):
    """Return DISTINCT T2 IDs, without inventing members or a NULL==NULL join.

    records: id plus level_1/2/3 from exactly one kind/profile. The caller owns
    completeness validation and the subsequent code membership join.
    """
    assigned=set(assigned_ids)
    parents=[row for row in records if row['id'] in assigned]
    return {candidate['id'] for candidate in records for parent in parents
            if _sql_equal(candidate['level_1'],parent['level_1'])
            and all(parent[key] is None or _sql_equal(candidate[key],parent[key])
                    for key in ('level_2','level_3'))}


def materialize_permission_memberships(records,attributes):
    """Canonical lower(trim(...)) triple join, retaining every attribute row.

    attributes carry code/level_1/2/3. No calculated report result is an input.
    NULL in either side never matches; a root's NULLs expand IDs, not codes.
    """
    def triple(row):
        values=[row[f'level_{i}'] for i in (1,2,3)]
        return None if any(v is None for v in values) else tuple(str(v).strip(' ').lower() for v in values)
    members={row['id']:Counter() for row in records}
    for permission in records:
        key=triple(permission)
        if key is None: continue
        for attribute in attributes:
            if triple(attribute)==key:
                members[permission['id']][attribute['code']]+=1
    return members
