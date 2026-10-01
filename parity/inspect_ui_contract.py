"""Bounded read-only schema/config inspection in owned canonical oracle."""
import json
import os
from pathlib import Path
from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import file_sha


def main():
    import sys
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    result = {}
    with exclusive_replay():
        with connection('VFTEST_BPR') as db:
            for name in ('Userwise_UiReportConfiguration', 'ui_ReportConfigurations', 'LocationAttributeData'):
                columns = db.execute('''SELECT c.name,t.name,c.max_length,c.is_nullable
                    FROM sys.columns c JOIN sys.types t ON c.user_type_id=t.user_type_id
                    WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id''', name).fetchall()
                result[name] = {'columns': [list(r) for r in columns],
                    'definition': db.execute('SELECT OBJECT_DEFINITION(OBJECT_ID(?))',name).fetchval(),
                    'synonym': [list(r) for r in db.execute('SELECT name,base_object_name FROM sys.synonyms WHERE name=?',name).fetchall()]}
            cursor = db.execute("SELECT * FROM ui_ReportConfigurations WHERE ReportName='NormSuggestion'")
            result['dbm_config'] = [dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]
        with connection('VFTEST_Importer') as db:
            cursor = db.execute("SELECT * FROM ui_ReportColumnTypes WHERE ReportName='NormSuggestion'")
            result['dbm_types'] = [dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]
    path = target/'inspection.json'
    path.write_text(json.dumps(result,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(path),'sha256':file_sha(path),'configuration_rows':len(result['dbm_config']),
        'types':len(result['dbm_types']), 'schema':{k:v for k,v in result.items() if k not in ('dbm_config','dbm_types')}}))


if __name__ == '__main__':
    main()
