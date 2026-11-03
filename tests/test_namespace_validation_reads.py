"""The real ACL reader queries fit the unchanged locked SELECT-only boundary."""
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch
from mta.mdm import owned_namespace
from mta.presentation import request_scope


class Connection:
    in_atomic_block=True
    def __init__(self):self.wrappers=[];self.queries=[]
    @contextmanager
    def execute_wrapper(self,wrapper):
        self.wrappers.append(wrapper)
        try:yield
        finally:self.wrappers.pop()
    def execute(self,sql,params=None):
        def base(sql,params,many,context):self.queries.append((sql,params))
        execute=base
        for wrapper in self.wrappers:
            previous=execute
            execute=lambda *args,wrapper=wrapper,previous=previous:wrapper(previous,*args)
        return execute(sql,params,False,{})
    def fetchone(self):return (7,True,False)
    def fetchall(self):return []


class NamespaceValidationTests(TestCase):
    def test_catalogue_acl_queries_remain_read_only_and_preserve_result_contract(self):
        db=Connection()
        registration=dict(issuer_oid=1,consumer_oid=2,owner_oid=3,acceptor_oid=4)
        with patch('django.db.connection',db),request_scope.remark_validation(),request_scope.validation_reads():
            self.assertEqual(owned_namespace._acl_violations(db,dict(oid=5),registration),
                             dict(count=7,issuer_connect=True,consumer_connect=False))
            self.assertEqual(owned_namespace._application_catalogue(db),dict(objects=[],grants=[],functions=[]))
            for sql in ('UPDATE x SET y=1','SET ROLE owner','WITH x AS (DELETE FROM y RETURNING *) SELECT * FROM x'):
                with self.assertRaisesRegex(ValueError,'SQL write or control'):
                    db.execute(sql)
        self.assertEqual(len(db.queries),4)
        self.assertTrue(all(sql.lstrip().startswith('SELECT') for sql,_params in db.queries))
        self.assertEqual(db.queries[0][1],[5,1,2,1,2,3,2,4,2,3,4,3,2,4,2,3,4,1,5,2,5])
