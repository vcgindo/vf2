"""Read-only reconciliation of the deployed parser's local connection change.

Read configuration metadata only. No legacy business rows or SQL mutations.
The tested parsing/insertion functions must be byte-independent AST matches.
"""
import ast
import json
from pathlib import Path
import pyodbc
from parity.verify_current_day import file_hash

ROOT=Path(__file__).resolve().parents[1]


def reconcile():
    preserved=Path('F:/VFlow_Source_Backup/deployed-demo/MTA/V6/Engine/ReadDailyDataToInterface.py')
    deployed=Path('F:/VFlow_Local/local-runtime/mta-engine/Engine/ReadDailyDataToInterface.py')
    if file_hash(preserved)!='6b232a259f72fe55fa41aeb741f871442256593dab6bab3cd4cf1dc9026c50dd':
        raise ValueError('Preserved parser changed')
    if file_hash(deployed)!='dd94826491cc045259d02c20168de0f24c0540bc1f91b855015161bf5cf55e3f':
        raise ValueError('Deployed parser changed; require explicit reconciliation')
    def definitions(path):
        result={}
        for node in ast.parse(path.read_text()).body:
            if isinstance(node,ast.FunctionDef):result[node.name]=ast.dump(node,include_attributes=False)
            elif isinstance(node,ast.ClassDef):
                for method in node.body:
                    if isinstance(method,ast.FunctionDef):result[node.name+'.'+method.name]=ast.dump(method,include_attributes=False)
        return result
    a,b=definitions(preserved),definitions(deployed)
    differences=[name for name in sorted(set(a)|set(b)) if a.get(name)!=b.get(name)]
    if differences!=['DBConnect.get_file_column_mapping']:
        raise ValueError('Additional parser method drift: '+str(differences))
    # Fixed, read-only metadata query: no dynamic database/table or credentials.
    connection=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
        'DATABASE=Demo_Importer_1;Trusted_Connection=yes;TrustServerCertificate=yes',
        autocommit=True,timeout=10,readonly=True)
    try:
        cursor=connection.execute('SELECT FileName,TableName,Col,StartLine,DB,Delimiter FROM dbo.FileColumnMapping ORDER BY MappingId')
        columns=[r[0] for r in cursor.description]
        mapping=[dict(zip(columns,row)) for row in cursor]
    finally:connection.close()
    fixture=json.loads((ROOT/'mta/fixtures/r1_gulfoil_common_selected.json').read_text())
    if mapping!=fixture['mapping']:
        raise ValueError('Deployed MappingId order differs from retained adapter configuration')
    return dict(preserved_sha256=file_hash(preserved),deployed_sha256=file_hash(deployed),
        identical_function_names=[n for n in a if n not in differences],
        difference='Connection TrustServerCertificate; configuration lookup adds ORDER BY MappingId',
        configuration_rows=len(mapping),mapping_equals_retained_order=True,
        scope='Retained parser receipts execute the unchanged parsing/insert methods with this same ordered mapping')


if __name__=='__main__':
    import sys
    target=Path(sys.argv[1])
    if target.exists():raise ValueError('Preserve earlier reconciliation')
    result=reconcile();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
