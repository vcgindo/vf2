-- Run only by the separately authorized owner of the target isolated database.
-- No LOGIN, password or membership grant is created here. Never grant this role
-- to a serving account. Runtime serving accounts must not be owners/superusers.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='fresh_operational_acceptor') THEN
  CREATE ROLE fresh_operational_acceptor NOLOGIN;
 END IF;
END $$;
GRANT USAGE ON SCHEMA mta TO fresh_operational_acceptor;
GRANT SELECT ON ALL TABLES IN SCHEMA mta TO fresh_operational_acceptor;
-- SELECT FOR UPDATE needs UPDATE privilege; immutable business guards still apply.
GRANT UPDATE ON mta.fresh_mta_calculationrun, mta.fresh_mta_dailyuipublication,
 mta.fresh_mta_operationalattempt TO fresh_operational_acceptor;
GRANT INSERT ON mta.fresh_mta_operationalacceptance,
 mta.fresh_mta_dailyuiactivation TO fresh_operational_acceptor;
