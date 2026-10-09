"""Bounded restore provisioning for a registered, isolated source namespace."""
import json
import os
from pathlib import Path
import re

import psycopg
from psycopg import sql

POLICY='fresh-owned-restore-v1'
FIELDS={'policy','registration_digest','database_oid','owner_oid','provisioner_oid',
        'provisioner_role','credential_file'}


class OwnedRestore:
    def __init__(self, binding, namespace, database):
        if (not isinstance(binding,dict) or set(binding)!=FIELDS
                or binding['policy']!=POLICY
                or any(binding[name]!=namespace[name] for name in
                       ('registration_digest','database_oid','owner_oid'))
                or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}',binding['provisioner_role'])
                or type(binding['provisioner_oid']) is not int
                or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}',namespace['owner_role'])):
            raise ValueError('Exact registered restore binding required')
        path=Path(binding['credential_file'])
        if not path.is_absolute() or not path.is_file():
            raise ValueError('Explicit private restore credential file required')
        secret=json.loads(path.read_bytes())
        if (not isinstance(secret,dict) or set(secret)!={'user','password'}
                or secret['user']!=binding['provisioner_role']
                or not isinstance(secret['password'],str) or not secret['password']):
            raise ValueError('Restore credential role binding differs')
        self.binding=binding;self.namespace=namespace;self.database=database
        self.params=dict(host=database['HOST'],port=database['PORT'] or '5432',options='',**secret)
        self.target_oid=None

    def admin(self):
        return psycopg.connect(dbname='postgres',autocommit=True,**self.params)

    def connect(self,name):
        return psycopg.connect(dbname=name,**self.params)

    def environment(self):
        return {**os.environ,'PGHOST':str(self.params['host']),
                'PGPORT':str(self.params['port']),'PGUSER':self.params['user'],
                'PGPASSWORD':self.params['password'],'PGOPTIONS':''}

    def authorize(self,admin,target,source):
        row=admin.execute('''SELECT r.oid::bigint,r.rolname,r.rolcanlogin,r.rolsuper,
            r.rolcreatedb,r.rolcreaterole,r.rolreplication,r.rolbypassrls,r.rolinherit,
            current_user=session_user FROM pg_roles r WHERE rolname=current_user''').fetchone()
        expected=(self.binding['provisioner_oid'],self.binding['provisioner_role'],
                  True,False,True,False,False,False,False,True)
        if tuple(row or ())!=expected:
            raise ValueError('Dedicated minimum-authority restore provisioner required')
        memberships=admin.execute('''SELECT 1 FROM pg_roles r WHERE r.oid<>%s
            AND (pg_has_role(%s,r.oid,'MEMBER')
              OR (NOT r.rolsuper AND pg_has_role(r.oid,%s,'MEMBER'))) LIMIT 1''',
            (row[0],row[0],row[0])).fetchone()
        actual=admin.execute('''SELECT oid::bigint,datdba::bigint,
            has_database_privilege(%s,oid,'CONNECT') FROM pg_database WHERE datname=%s''',
            (row[0],source)).fetchone()
        if (memberships or source!=self.namespace['database_name']
                or tuple(actual or ())!=(self.binding['database_oid'],self.binding['owner_oid'],False)
                or target==source):
            raise ValueError('Restore source ownership or provisioner isolation differs')

    def created(self,admin,target):
        row=admin.execute('SELECT oid::bigint,datdba::bigint FROM pg_database WHERE datname=%s',
                          (target,)).fetchone()
        if not row or row[1]!=self.binding['provisioner_oid']:
            raise ValueError('New restore target owner differs')
        self.target_oid=row[0]
        admin.execute(sql.SQL('REVOKE ALL ON DATABASE {} FROM PUBLIC').format(sql.Identifier(target)))
        extra=admin.execute('''SELECT 1 FROM pg_database d CROSS JOIN LATERAL
            aclexplode(COALESCE(d.datacl,acldefault('d',d.datdba))) a
            WHERE d.oid=%s AND a.grantee<>d.datdba LIMIT 1''',(self.target_oid,)).fetchone()
        if extra:raise ValueError('Restore target grants are not exclusive')
        admin.execute(sql.SQL('ALTER DATABASE {} ALLOW_CONNECTIONS true').format(sql.Identifier(target)))

    @property
    def source_role(self):
        return self.namespace['owner_role']

    def verify_source(self,connection):
        row=connection.execute('''SELECT d.oid::bigint,d.datdba::bigint,current_database(),
            current_user,session_user FROM pg_database d WHERE datname=current_database()''').fetchone()
        if tuple(row or ())!=(self.binding['database_oid'],self.binding['owner_oid'],
                self.namespace['database_name'],self.source_role,self.namespace['issuer_role']):
            raise ValueError('Source snapshot owner/issuer identity differs')

    def verify_target(self,connection,target):
        row=connection.execute('''SELECT d.oid::bigint,d.datdba::bigint,current_database(),
            current_user,session_user FROM pg_database d WHERE datname=current_database()''').fetchone()
        if tuple(row or ())!=(self.target_oid,self.binding['provisioner_oid'],target,
                              self.binding['provisioner_role'],self.binding['provisioner_role']):
            raise ValueError('Restore target identity changed')

    def receipt(self,target):
        if self.target_oid is None:raise ValueError('No observed restore target')
        return dict(policy=POLICY,registration_digest=self.binding['registration_digest'],
            source_database=self.namespace['database_name'],source_oid=self.binding['database_oid'],
            source_owner_oid=self.binding['owner_oid'],source_issuer_oid=self.namespace['issuer_oid'],
            provisioner_oid=self.binding['provisioner_oid'],provisioner_role=self.binding['provisioner_role'],
            target_database=target,target_oid=self.target_oid,target_owner_oid=self.binding['provisioner_oid'],
            public_connect=False)


def bind_restore(options,source,source_receipt,database):
    from mta.mdm.owned_namespace import verify_binding
    verify_binding(source_receipt)
    namespace=source_receipt['owned_namespace']
    if (source!=database['NAME'] or source!=namespace['database_name']
            or database['USER']!=namespace['issuer_role']):
        raise ValueError('Registered backup source differs')
    return OwnedRestore(options,namespace,database)
