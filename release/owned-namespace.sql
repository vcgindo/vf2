-- One-time VectorFLOW native namespace registration template.
--
-- Run only as the trusted cluster provisioning authority, after creating the
-- unique database, applying Django migrations under its dedicated owner, and
-- verifying that no MDM/workflow source has been installed.  This file creates
-- no serving grant and contains no credential.  Required psql variables:
--   database_name, owner_role, issuer_role, consumer_role,
--   registration_id, artifact_sha256, adapter_sha256
--
-- The preceding cluster-level setup is deliberately explicit and one-time:
--   CREATE ROLE fresh_namespace_registrar NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
--     NOREPLICATION NOBYPASSRLS NOINHERIT;
--   CREATE ROLE <owner> NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
--     NOREPLICATION NOBYPASSRLS NOINHERIT;
--   CREATE ROLE <issuer> LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
--     NOREPLICATION NOBYPASSRLS NOINHERIT; -- credential supplied out of Git
--   CREATE ROLE <consumer> LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
--     NOREPLICATION NOBYPASSRLS NOINHERIT; -- credential supplied out of Git
--   -- fresh_operational_acceptor is the existing canonical NOLOGIN role from
--   -- packaging/cohort5/offline-issuer.sql; do not create an alias.
--   GRANT <owner>, fresh_operational_acceptor TO <issuer>;
--   CREATE DATABASE <database> OWNER <owner>;
-- Connect this script to that exact database. The application guard independently
-- rechecks every role/database/ACL fact below from the PostgreSQL catalogues.

\set ON_ERROR_STOP on

GRANT :"owner_role", fresh_operational_acceptor TO :"issuer_role";
REVOKE ALL PRIVILEGES ON DATABASE :"database_name" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"database_name" TO :"issuer_role", :"consumer_role";
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA mta FROM PUBLIC;
GRANT USAGE ON SCHEMA mta TO :"consumer_role", fresh_operational_acceptor;
GRANT SELECT ON ALL TABLES IN SCHEMA mta TO fresh_operational_acceptor;
GRANT UPDATE ON mta.fresh_mta_calculationrun, mta.fresh_mta_dailyuipublication,
 mta.fresh_mta_operationalattempt TO fresh_operational_acceptor;
GRANT INSERT ON mta.fresh_mta_operationalacceptance,
 mta.fresh_mta_dailyuiactivation TO fresh_operational_acceptor;

CREATE SCHEMA fresh_control AUTHORIZATION fresh_namespace_registrar;
REVOKE ALL ON SCHEMA fresh_control FROM PUBLIC;

CREATE TABLE fresh_control.owned_namespace (
 singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton IS TRUE),
 registration_id uuid NOT NULL UNIQUE,
 policy text NOT NULL CHECK (policy='fresh-owned-mdm-namespace-v1'),
 database_oid oid NOT NULL,
 database_name name NOT NULL,
 owner_oid oid NOT NULL,
 issuer_oid oid NOT NULL,
 consumer_oid oid NOT NULL,
 acceptor_oid oid NOT NULL,
 artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
 adapter_sha256 text NOT NULL CHECK (adapter_sha256 ~ '^[0-9a-f]{64}$'),
 CHECK (owner_oid<>issuer_oid AND owner_oid<>consumer_oid AND owner_oid<>acceptor_oid
        AND issuer_oid<>consumer_oid AND issuer_oid<>acceptor_oid
        AND consumer_oid<>acceptor_oid)
);
ALTER TABLE fresh_control.owned_namespace OWNER TO fresh_namespace_registrar;

CREATE FUNCTION fresh_control.deny_owned_namespace_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'Fresh owned namespace registration is immutable';
END $$;
ALTER FUNCTION fresh_control.deny_owned_namespace_change() OWNER TO fresh_namespace_registrar;
REVOKE ALL ON FUNCTION fresh_control.deny_owned_namespace_change() FROM PUBLIC;
CREATE TRIGGER owned_namespace_immutable
 BEFORE UPDATE OR DELETE ON fresh_control.owned_namespace
 FOR EACH ROW EXECUTE FUNCTION fresh_control.deny_owned_namespace_change();

INSERT INTO fresh_control.owned_namespace (
 singleton,registration_id,policy,database_oid,database_name,
 owner_oid,issuer_oid,consumer_oid,acceptor_oid,artifact_sha256,adapter_sha256)
SELECT TRUE, :'registration_id'::uuid, 'fresh-owned-mdm-namespace-v1',
       d.oid,d.datname,o.oid,i.oid,c.oid,a.oid,:'artifact_sha256',:'adapter_sha256'
  FROM pg_catalog.pg_database d
  JOIN pg_catalog.pg_roles o ON o.rolname=:'owner_role' AND o.oid=d.datdba
  JOIN pg_catalog.pg_roles i ON i.rolname=:'issuer_role'
  JOIN pg_catalog.pg_roles c ON c.rolname=:'consumer_role'
  JOIN pg_catalog.pg_roles a ON a.rolname='fresh_operational_acceptor'
 WHERE d.datname=current_database() AND d.datname=:'database_name';

REVOKE ALL ON fresh_control.owned_namespace FROM PUBLIC, :"owner_role", :"issuer_role", :"consumer_role", fresh_operational_acceptor;
GRANT USAGE ON SCHEMA fresh_control TO :"owner_role", :"consumer_role", fresh_operational_acceptor;
GRANT SELECT ON fresh_control.owned_namespace TO :"owner_role", :"consumer_role", fresh_operational_acceptor;

-- No application-table grants are made here. Grant the nonowner consumer SELECT
-- only on the later approved typed read set, then retain the catalogue/denial proof.
