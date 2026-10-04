"""Owned PostgreSQL guards for immutable completed BTR reporting generations."""
FORWARD = """
CREATE FUNCTION mta.guard_btr_generation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status <> 'BUILDING' THEN
    RAISE EXCEPTION 'Completed BTR reporting attempts are immutable';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER btr_generation_immutable BEFORE UPDATE OR DELETE
ON mta.fresh_mta_btrreportinggeneration FOR EACH ROW
EXECUTE FUNCTION mta.guard_btr_generation();
CREATE FUNCTION mta.guard_btr_reference() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner_status text;
BEGIN
  IF TG_OP <> 'INSERT' THEN
    SELECT status INTO owner_status FROM mta.fresh_mta_btrreportinggeneration
      WHERE id=OLD.generation_id FOR SHARE;
    IF owner_status IS DISTINCT FROM 'BUILDING' THEN
      RAISE EXCEPTION 'Completed BTR references are immutable';
    END IF;
  END IF;
  IF TG_OP <> 'DELETE' THEN
    SELECT status INTO owner_status FROM mta.fresh_mta_btrreportinggeneration
      WHERE id=NEW.generation_id FOR SHARE;
    IF owner_status IS DISTINCT FROM 'BUILDING' THEN
      RAISE EXCEPTION 'BTR references require a private BUILDING generation';
    END IF;
    RETURN NEW;
  END IF;
  RETURN OLD;
END $$;
CREATE TRIGGER btr_reference_immutable BEFORE INSERT OR UPDATE OR DELETE
ON mta.fresh_mta_btrjoinreference FOR EACH ROW
EXECUTE FUNCTION mta.guard_btr_reference();
"""
REVERSE = """
DROP TRIGGER btr_reference_immutable ON mta.fresh_mta_btrjoinreference;
DROP FUNCTION mta.guard_btr_reference();
DROP TRIGGER btr_generation_immutable ON mta.fresh_mta_btrreportinggeneration;
DROP FUNCTION mta.guard_btr_generation();
"""
