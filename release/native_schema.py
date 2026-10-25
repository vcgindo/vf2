"""Read-only schema fingerprint inside the existing immutable capability.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
from mta.serialization import digest
from mta.presentation.schema_reuse import schema_read


@schema_read
def schema_digest(cursor):
    """Detect schema drift beyond object/ACL checks; never mint an authority row."""
    queries = {
        'columns': """SELECT n.nspname,c.relname,a.attnum,a.attname,
            format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,a.attgenerated,
            pg_get_expr(d.adbin,d.adrelid)
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
            WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control')
              AND a.attnum>0 AND NOT a.attisdropped ORDER BY 1,2,3""",
        'constraints': """SELECT n.nspname,c.relname,t.conname,t.contype,
            t.convalidated,pg_get_constraintdef(t.oid)
            FROM pg_constraint t JOIN pg_class c ON c.oid=t.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1,2,3""",
        'indexes': """SELECT schemaname,tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1,2,3""",
        'triggers': """SELECT n.nspname,c.relname,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid)
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE NOT t.tgisinternal AND n.nspname IN ('mta','mta_state','mta_opening','fresh_control')
            ORDER BY 1,2,3""",
        'functions': """SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),
            pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname IN ('mta','mta_state','mta_opening','fresh_control') ORDER BY 1,2,3""",
        'views': """SELECT n.nspname,c.relname,pg_get_viewdef(c.oid)
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE c.relkind IN ('v','m') AND n.nspname IN ('mta','mta_state','mta_opening','fresh_control')
            ORDER BY 1,2""",
        'migrations': 'SELECT app,name FROM mta.django_migrations ORDER BY app,name',
    }
    result = {}
    for name, sql in queries.items():
        cursor.execute(sql)
        result[name] = cursor.fetchall()
    return digest(result)
