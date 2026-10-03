"""Prepare the expressly authorized native fixture catalogue, without grants."""
import gzip
import json
from collections import Counter
from tools.stage2_vm_dataset import DEST,sha
from tools.stage2_vm_contract import sealed,atomic
from mta.presentation.permissions import materialize_permission_memberships


def main():
    manifest,manifest_sha=sealed(DEST)
    def rows(role,name):
        source=next(s for s in manifest['sources'] if s['source']=='Demo_'+role+'_1')
        table=next(t for t in source['tables'] if t['table_name'].casefold()==name.casefold())
        if sha(DEST/table['file'])!=table['sha256']:raise ValueError('Frozen permission input changed')
        with gzip.open(DEST/table['file'],'rt',encoding='utf-8') as stream:
            return [dict(zip([c['name'] for c in table['columns']],json.loads(line))) for line in stream]
    result=dict(version='legacy-ui-fixture-permissions-v1',dataset=manifest['identity'],manifest_sha256=manifest_sha)
    memberships={}
    for kind,table,prefix,attr,code,levels in [('products','PRODUCT_PERMISSION','product_hierarchy_','SkuAttributeData','SKUCode','SL'),('locations','LOCATION_PERMISSION','location_heirarchy_','LocationAttributeData','WHCode','LL')]:
        records=[dict(id=r['id'],**{'level_'+str(i):r[prefix+str(i)] for i in (1,2,3)}) for r in rows('Importer',table)]
        result[kind]=dict(records=records)
        attributes=[dict(code=r[code],**{'level_'+str(i):r[levels+str(i)] for i in (1,2,3)}) for r in rows('DBM',attr)]
        memberships[kind]=materialize_permission_memberships(records,attributes)
    pairs=Counter()
    for row in rows('DBM','Suggestions'):
        for p,ps in memberships['products'].items():
            if row['SKUCode'] not in ps:continue
            for l,ls in memberships['locations'].items():
                if row['WhCode'] in ls:pairs[p,l]+=ps[row['SKUCode']]*ls[row['WhCode']]
    if not pairs:raise ValueError('No represented positive native scope')
    selected=sorted(pairs,key=lambda pair:(-pairs[pair],pair))[0]
    atomic(DEST/'fixture-permissions.json',result)
    atomic(DEST/'fixture-scope-plan.json',dict(manifest_sha256=manifest_sha,catalogue_sha256=sha(DEST/'fixture-permissions.json'),
        broad={kind:[r['id'] for r in result[kind]['records']] for kind in ('products','locations')},
        restricted=dict(products=[selected[0]],locations=[selected[1]]),restricted_suggestion_join_rows=pairs[selected],
        native_memberships={kind:{str(k):len(v) for k,v in members.items()} for kind,members in memberships.items()},
        semantics='Native permission IDs and exact hierarchy values; no membership override; NULL never equals NULL'))
    print('Prepared native catalogue; represented restricted scope',selected,pairs[selected])


if __name__=='__main__':main()
