"""Pure, source-positioned evaluation of the fourteen seeded legacy alerts.

This module deliberately performs no database, filesystem, archive, clock, or
mail operation.  Callers supply the source-stage row populations and artifact
facts explicitly; a missing required population is an error, never an empty
population.  The returned mapping is an alert intent/evaluation record only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any, Mapping, Sequence

from mta.domain.complete_daily_scalars import MONTHS, ascii_equal, parse_datetime


INTENT_SCHEMA = "fresh-operational-alert-intent-v1"
SEED_SOURCE = "Scripts/DBCreation/Importer_DBCreation.sql"
SEED_SOURCE_SHA256 = "11c004b7d790bf560549bcad8e3342c3bed15972a63d9e0f26458392edea6309"


# Order, spelling, activation and source ownership are the deployed seed
# contract.  ``subject_branch`` and ``body_branch`` identify the exact SQL
# branch to be rendered later from the cited source; this evaluator does not
# invent or normalize legacy message text.
ALERT_SEEDS: tuple[Mapping[str, Any], ...] = (
    {"name": "NoNormParentAlert", "active": "1", "stage": "parent-norm", "branch": "no-norm-parent", "wrapper": "Engine/ValidateParentNorm.bat", "sql": "Scripts/Importer/NoNormParentAlert.sql"},
    {"name": "InvalidDataAlert", "active": "1", "stage": "input-validation", "branch": "invalid-data", "wrapper": "Engine/InvalidDataAlert.bat", "sql": "Scripts/Importer/InvalidDataAlert.sql"},
    {"name": "DailyDataUnavailabilityAlert", "active": "1", "stage": "fullkit", "branch": "daily-data-unavailable", "wrapper": "Engine/DailyDataUnavailabilityAlert.bat", "sql": "Scripts/Importer/DataUnavailabilityAlert.sql"},
    {"name": "AutoNormAcceptanceAlert", "active": "1", "stage": "dbm-core", "branch": "auto-norm-acceptance", "wrapper": "Engine/AutoNormAcceptance.bat", "sql": "Scripts/DBM/AutoAcceptance/NormAcceptanceAlert.sql"},
    {"name": "MissingMasterDataForDistributorsAlert", "active": "1", "stage": "input-validation", "branch": "missing-distributor-master", "wrapper": "Engine/MissingMasterDataAlertForDistributor.bat", "sql": "Scripts/Distributor/MissingMasterDataAlertForDistributors.sql"},
    {"name": "LocationInventoryMissingAlert", "active": "0", "stage": "input-validation", "branch": "location-inventory-missing", "wrapper": "Engine/GenerateLocationInventoryMissingAlert.bat", "sql": "Scripts/Importer/GenerateLocationInventoryMissingAlert.sql"},
    {"name": "UnapprovedPhaseinPhaseoutAlert", "active": "1", "stage": "input-validation", "branch": "unapproved-phasein-phaseout", "wrapper": "Engine/UnapprovedPhaseinPhaseoutAlert.bat", "sql": "Scripts/Importer/Misc/UnApprovedPhaseinPhaseoutAlert.sql"},
    {"name": "FailedForceNormAlert", "active": "1", "stage": "norm-controls", "branch": "failed-force-norm", "wrapper": "Engine/NormChangesRun.bat", "sql": "Scripts/DBM/Misc/FailedForceNormChangeAlert.sql"},
    {"name": "PhaseInPhaseOutExceptionAlert", "active": "1", "stage": "norm-controls", "branch": "phasein-phaseout-exception", "wrapper": "Engine/PhaseInPhaseOutException.bat", "sql": "Scripts/DBM/Misc/PhaseInPhaseOutExceptionAlert.sql"},
    {"name": "RejectedInvoiceAlert", "active": "1", "stage": "distributor", "branch": "rejected-invoice", "wrapper": "Engine/RejectedInvoiceReport.bat", "sql": "Scripts/Distributor/RejectedInvoiceAlert.sql"},
    {"name": "DBMNormChangeAlert", "active": "0", "stage": "dbm-files", "branch": "dbm-norm-change", "wrapper": "Engine/SendDBMNormChangeReport.bat", "sql": "Scripts/DBM/DBMNormChange/DBMNormChangeAlert.sql"},
    {"name": "RunFinishAlert", "active": "0", "stage": "run-finish", "branch": "run-finish", "wrapper": "Engine/VectorFLOWv4.bat", "sql": "Scripts/Common/RunFinishAlert.sql"},
    {"name": "BPRExceptionAlert", "active": "1", "stage": "bpr-exception-files", "branch": "bpr-exception", "wrapper": "Engine/GenerateBPRExceptionReport.bat", "sql": "Scripts/BPR/SendBPRExceptionsAlert.sql"},
    {"name": "DailyDataValidationErrorAlert", "active": "1", "stage": "sanitation", "branch": "daily-data-validation-error", "wrapper": "Engine/DataValidationErrorAlert.bat", "sql": "Scripts/Importer/SendDataValidationExceptionsAlert.sql"},
)

_SEEDS = {seed["name"]: seed for seed in ALERT_SEEDS}
_REQUIRED_CONFIGURATION = ("recipient", "cc_recipient", "profile", "site", "business_date", "run_datetime")


class AlertInputError(ValueError):
    """A source-owned input required to evaluate an alert was not supplied."""


def seed_settings() -> dict[str, str]:
    """Return a mutable copy of the exact deployed alert activation roster."""

    return {seed["name"]: seed["active"] for seed in ALERT_SEEDS}


def evaluate_alert(
    alert_name: str,
    *,
    settings: Mapping[str, str],
    configuration: Mapping[str, Any],
    populations: Mapping[str, Sequence[Mapping[str, Any]]],
    artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate one alert at its native source position.

    ``settings`` must be the complete fourteen-row activation roster.  Row
    populations use their deployed table names.  Artifact facts are keyed by
    the exact attachment filename and contain ``available`` and ``members``;
    file-size predicates additionally require ``byte_size``.
    """

    if alert_name not in _SEEDS:
        raise AlertInputError(f"unknown alert setting: {alert_name}")
    _validate_settings(settings)
    _require_configuration(configuration)
    seed = _SEEDS[alert_name]
    result = _base_result(seed, configuration)
    if settings[alert_name] == "0":
        return _finish(result, "DISABLED_SETTING", "seed-disabled")

    auto_dbm = _config_flag(configuration, "auto_dbm_active") if alert_name in {"AutoNormAcceptanceAlert", "DBMNormChangeAlert"} else None
    distributor = _config_flag(configuration, "distributor_system_active") if alert_name in {"MissingMasterDataForDistributorsAlert", "RejectedInvoiceAlert"} else None
    if alert_name == "AutoNormAcceptanceAlert" and not auto_dbm:
        return _finish(result, "DISABLED_OPERATION", "auto-dbm-disabled")
    if alert_name == "DBMNormChangeAlert" and auto_dbm:
        return _finish(result, "DISABLED_OPERATION", "auto-dbm-enabled")
    if alert_name in {"MissingMasterDataForDistributorsAlert", "RejectedInvoiceAlert"} and not distributor:
        return _finish(result, "DISABLED_OPERATION", "distributor-system-disabled")

    predicate, branch, values, attachment = _evaluate_predicate(
        alert_name, configuration, populations, artifacts
    )
    result.update(branch=branch, values=values, attachment=attachment)
    if not predicate:
        return _finish(result, "PREDICATE_FALSE", branch)
    if not _recipient_suppressed(configuration["recipient"]):
        subject, body = _render_message(alert_name, branch, configuration, values)
        result.update(subject=subject, body=body)
    if attachment is not None and not attachment["available"]:
        return _finish(result, "UNAVAILABLE", "required-attachment-unavailable")
    if _recipient_suppressed(configuration["recipient"]):
        return _finish(result, "RECIPIENT_SUPPRESSED", "recipient-not-defined")
    return _finish(result, "READY", branch)


def _evaluate_predicate(
    name: str,
    config: Mapping[str, Any],
    populations: Mapping[str, Sequence[Mapping[str, Any]]],
    artifacts: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, str, dict[str, Any], dict[str, Any] | None]:
    run_dt = _as_datetime(config["run_datetime"], "run_datetime")
    run_date = _as_date(config["business_date"], "business_date")
    day = f"{run_date.day:02d}"

    if name == "NoNormParentAlert":
        csv = _artifact(artifacts, "NoNormParentReport.csv", require_size=True)
        present = csv["byte_size"] > 0
        return present, "file-size-positive" if present else "file-size-zero", {}, _artifact(artifacts, "NoNormParentReport.zip", members=("NoNormParentReport.csv",)) if present else None

    if name == "InvalidDataAlert":
        rows = _population(populations, "RejectedMaster")
        count = sum(_sql_number_compare(row.get("ReasonCode"), ">", 0) and _same_datetime(row.get("RejectionDate"), run_dt) for row in rows)
        if not count:
            return False, "no-invalid-data", {"invalid_count": 0}, None
        zipped = _config_flag(config, "attach_invalid_data_report_zip")
        filename = "InvalidDataReport.zip" if zipped else "InvalidDataReport.csv"
        members = ("InvalidDataReport.csv",) if zipped else None
        return True, "invalid-data-present", {"invalid_count": count, "attachment_mode": "zip" if zipped else "csv"}, _artifact(artifacts, filename, members=members)

    if name == "DailyDataUnavailabilityAlert":
        critical = _config_flag(config, "critical_data_available")
        reasons = _population(populations, "RunAbortReasons")
        count = sum(_same_datetime(row.get("RunDateTime"), run_dt) for row in reasons)
        present = not critical and count > 0
        return present, "critical-data-unavailable" if present else "run-start-criteria-satisfied", {"abort_reason_count": count}, _artifact(artifacts, "DailyDataUnavailabilityReport.zip", members=("DailyDataUnavailabilityReport.csv",)) if present else None

    if name == "AutoNormAcceptanceAlert":
        rows = _population(populations, "NormAcceptanceTbl")
        count = sum(_same_date(row.get("AcceptanceDate"), run_date) for row in rows)
        if count < 1:
            return True, "no-auto-accepted-norms", {"accepted_count": 0}, None
        filename = f"{run_date.isoformat()}-AutoAcceptedNorms.csv"
        return True, "auto-accepted-norms", {"accepted_count": count}, _artifact(artifacts, filename)

    if name == "MissingMasterDataForDistributorsAlert":
        retired = _population(populations, "RetiredNormsTbl")
        distributors = _population(populations, "DistributorList")
        batches = _population(populations, "LastBatchRunTbl")
        last_run = batches[0].get("LastRunDate") if batches else None
        warehouses = {row.get("WhCode") for row in distributors if row.get("WhCode") is not None}
        count = sum(row.get("WhCode") is not None and row.get("WhCode") in warehouses and _sql_number_compare(row.get("Event_Type"), "=", 0) and _same_datetime(row.get("Event_Date"), _as_datetime(last_run, "LastBatchRunTbl.LastRunDate")) for row in retired) if last_run is not None else 0
        if not count:
            return False, "no-missing-distributor-master", {"missing_count": 0}, None
        return True, "missing-distributor-master", {"missing_count": count}, _artifact(artifacts, "MissingMasterDataRpt_Distributor.zip", members=("MissingMasterDataRpt_Distributor.csv",))

    if name == "LocationInventoryMissingAlert":
        csv = _artifact(artifacts, "LocationInventoryMissing.csv", require_size=True)
        present = csv["byte_size"] > 0
        return present, "file-size-positive" if present else "file-size-zero", {}, _artifact(artifacts, "LocationInventoryMissing.zip", members=("LocationInventoryMissing.csv",)) if present else None

    if name == "UnapprovedPhaseinPhaseoutAlert":
        phase_out = _population(populations, "PhaseOut")
        phase_in = _population(populations, "PhaseInNorms")
        out_count = sum(_sql_number_compare(row.get("Approved"), "=", 0) for row in phase_out)
        in_count = sum(_sql_number_compare(row.get("Approved"), "=", 0) for row in phase_in)
        present = out_count > 0 or in_count > 0
        return present, "unapproved-requests" if present else "all-requests-approved", {"phaseout_count": out_count, "phasein_count": in_count}, None

    if name == "FailedForceNormAlert":
        requested = _population(populations, "ForceNormChange")
        failed = _population(populations, "FailedForceNormChange")
        master = _population(populations, "DBMMaster")
        master_raw = _population(populations, "MasterDataRaw")
        request_count = len(requested)
        failed_count = len(failed)
        approved = any(_sql_number_compare(row.get("Approved"), "=", 1) for row in requested)
        master_keys = {_nonnull_key(row.get("SKUCode"), row.get("WHCode"), row.get("Norm")) for row in master}
        master_keys.discard(None)
        success_count = sum(_nonnull_key(row.get("SKUCode"), row.get("WhCode"), row.get("NewNorm")) in master_keys for row in requested)
        fnc_ignore = not _config_flag(config, "fnc_match_master_norm")
        nms_active = _config_flag(config, "nms_active")
        master_invalid = not master_raw and not fnc_ignore and not nms_active
        values = {
            "request_count": request_count,
            "failed_count": failed_count,
            "success_count": success_count,
            "approval_missing": not approved,
            "master_invalid": master_invalid,
        }
        if request_count == 0:
            return False, "no-force-norm-requests", values, None
        if failed_count == 0 and approved:
            return True, "all-force-norm-success", values, None
        if not approved or master_invalid:
            return True, "force-norm-blocked", values, None
        if failed_count > 0:
            filename = f"{day}-FailedForceNormChanges.csv"
            return True, "force-norm-failed", values, _artifact(artifacts, filename)
        return False, "no-force-norm-alert-branch", values, None

    if name == "PhaseInPhaseOutExceptionAlert":
        rows = _population(populations, "PhaseInPhaseOutExceptionLog")
        count = sum(_same_datetime(row.get("Log_Date"), run_dt) for row in rows)
        return count > 0, "exceptions-present" if count else "no-exceptions", {"exception_count": count}, _artifact(artifacts, "PhaseInPhaseOutExceptionReport.zip", members=("PhaseInPhaseOutExceptionReport.csv",)) if count else None

    if name == "RejectedInvoiceAlert":
        invoices = _population(populations, "InvoiceDataRaw")
        norms = _population(populations, "DistributorDBMNorms")
        norm_keys = {_nonnull_key(row.get("SKUCode"), row.get("WarehouseCode")) for row in norms}
        norm_keys.discard(None)
        count = sum(_nonnull_key(row.get("SKUCode"), row.get("WHCode")) not in norm_keys for row in invoices)
        filename = f"{day}-RejectedInvoiceList.csv"
        return count > 0, "rejected-invoices" if count else "no-rejected-invoices", {"rejected_count": count}, _artifact(artifacts, "RejectedInvoiceList.zip", members=(filename,)) if count else None

    if name == "DBMNormChangeAlert":
        rows = _population(populations, "NormChangeLogTbl")
        batches = _population(populations, "LastBatchRunTbl")
        if not batches or batches[0].get("LastRunDate") is None:
            raise AlertInputError("LastBatchRunTbl must contain its source-selected LastRunDate row")
        report_date = _as_date(batches[0]["LastRunDate"], "LastBatchRunTbl.LastRunDate")
        horizon = _positive_int(config, "dbm_norm_change_report_horizon")
        lower = report_date - timedelta(days=horizon - 1)
        count = sum(_sql_number_compare(row.get("NormChangeReason"), "<", 100) and _date_at_or_after(row.get("NormChangeDate"), lower) for row in rows)
        if not count:
            return True, "no-accepted-norms", {"norm_change_count": 0, "horizon_days": horizon, "report_date": str(report_date)}, None
        return True, "accepted-norms", {"norm_change_count": count, "horizon_days": horizon, "report_date": str(report_date)}, _artifact(artifacts, "DBMNormChange.zip", members=("DBMNormChange.csv",))

    if name == "RunFinishAlert":
        importer = _population(populations, "ImporterSettingsTbl")
        daily = _population(populations, "DailyDataRaw")
        execution_date_matches = any(
            row.get("Parameter") == "BatchFileExecutionDate" and _same_datetime(row.get("Value"), run_dt)
            for row in importer
        )
        executed_flag = any(
            row.get("Parameter") == "IsBatchFileExecuted" and str(row.get("Value")) == "1"
            for row in importer
        )
        batch_executed = execution_date_matches and executed_flag
        if not batch_executed:
            return True, "run-failure-batch", {"daily_data_count": len(daily)}, None
        if not daily:
            return True, "run-failure-daily-empty", {"daily_data_count": 0}, None
        return True, "run-finish", {"daily_data_count": len(daily)}, None

    if name == "BPRExceptionAlert":
        rows = _population(populations, "BPRExceptions")
        count = len(rows)
        return count > 0, "bpr-exceptions" if count else "no-bpr-exceptions", {"exception_count": count}, _artifact(artifacts, "BPRExceptionReport.zip", members=("BPRExceptionReport.csv",)) if count else None

    if name == "DailyDataValidationErrorAlert":
        rows = _population(populations, "DataSanitizationResult")
        bad = {"Partial", "False"}
        count = sum(row.get("Critical_Flag") in bad or row.get("Non_Critical_Flag") in bad for row in rows)
        if not count:
            return False, "sanitation-clean", {"validation_error_count": 0}, None
        # The deployed wrapper's report writer is commented out.  Its positive
        # path cannot produce the CSV needed by the subsequent archive step.
        unavailable = {"name": "DailyDataValidationErrorReport.zip", "available": False, "members": ["DailyDataValidationErrorReport.csv"], "source_reason": "native-attachment-writer-commented-out"}
        return True, "sanitation-errors", {"validation_error_count": count}, unavailable

    raise AssertionError(name)


def _render_message(
    name: str,
    branch: str,
    config: Mapping[str, Any],
    values: Mapping[str, Any],
) -> tuple[str, str]:
    """Render the exact SQL subject and body for a branch entering DB mail."""

    site = _sqlcmd_ascii(config["site"], "site")
    run_day = _style_106(_as_datetime(config["run_datetime"], "run_datetime"))
    business_day = _style_106(_as_date(config["business_date"], "business_date"))

    if name == "NoNormParentAlert":
        return _varchar100(f"{site}|VectorFLOW : Normed items with No-Norm parents Alert [{run_day}]"), (
            "\r\nOne or many of the Normed items have No-Norm Parent. List of such items is attached.\r\n"
            "Note that the VectorFLOW run will continue but the rationing output may be affected.\r\n"
            "\t\t\t\t\t\t\r\nThis mail is automatically generated.\r\n\t\t\t\t\t\r\n"
            "Regards,\r\nVector Support."
        )
    if name == "InvalidDataAlert":
        return _varchar100(f"{site}|VectorFLOW : Invalid Data Alert [{run_day}]"), (
            "\r\nOne or many of the input files/database tables have invalid data.\r\n"
            "'Invalid Data Report' attached.\r\n\t\t\t\t\t\t\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
        )
    if name == "DailyDataUnavailabilityAlert":
        return _varchar100(f"{site}|VectorFLOW : Daily Data Unavailability Alert [{run_day}]"), (
            "\r\nOne or many of the input files/database tables are unavailable so VectorFLOW run is not started.\r\n"
            "'Unavailability Data Report' is attached.\r\n\t\t\t\t\t\t\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
        )
    if name == "AutoNormAcceptanceAlert":
        subject = f"{site}|VectorFLOW : Auto Norm Acceptance-{business_day}"
        if branch == "no-auto-accepted-norms":
            body = (
                "\r\nToday no new norm recommendations were generated.\r\n\r\n"
                "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        elif branch == "auto-accepted-norms":
            body = (
                "\r\nAttached csv has details of accepted norms. \r\n"
                "Norm changes will be visible in BPR after next scheduled run.\r\n\r\n"
                "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        else:
            raise AlertInputError(f"unsupported message branch for {name}: {branch}")
        return subject, body
    if name == "MissingMasterDataForDistributorsAlert":
        return _varchar100(f"{site}|VectorFLOW : Missing Master Data Alert For Distributors [{run_day}]"), (
            "\r\nList of SKU-Locations missing in today's master input data for Distributors is attached herewith.\r\n"
            "\t\t\t\t\t\t\r\n\r\n\r\nThis mail is automatically generated.\r\n"
            "\t\t\t\t\t \r\nRegards,\r\nVector Support."
        )
    if name == "LocationInventoryMissingAlert":
        return _varchar100(f"{site}|VectorFLOW: Inventory information missing for location(s) Alert on [{run_day}]"), (
            "\r\n\r\nInventory information is missing for enclosed location(s).\r\n"
            "            \r\nThis mail is automatically generated.\r\n\r\nRegards,\r\nVector Support."
        )
    if name == "UnapprovedPhaseinPhaseoutAlert":
        return f"{site}|VectorFLOW : PhaseIn-PhaseOut Approval Status -{business_day}", (
            "\r\nFollowing number of PhaseIn-PhaseOut itesms are waiting for approval. \r\n"
            "PhaseIn-PhaseOut process can not be started without approval.\r\n\t\r\n"
            f"Unapproved Phase-Out Item(s) : {_sql_int(values, 'phaseout_count')}\r\n"
            f"Unapproved Phase-In Item(s) : {_sql_int(values, 'phasein_count')}\r\n\r\n\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
        )
    if name == "FailedForceNormAlert":
        subject = f"{site}|VectorFLOW : Force Norm Change Status -{business_day}"
        requested = _sql_int(values, "request_count")
        succeeded = _sql_int(values, "success_count")
        failed = _sql_int(values, "failed_count")
        if branch == "all-force-norm-success":
            body = (
                "\r\n\tToday's Force Norm Change Status \r\n"
                f"\tRequested Force Norm change(s) : {requested}\r\n"
                f"\tSuccessful Force Norm Change(s) : {succeeded}\r\n"
                f"\tFailed Force Norm Change(s) : {failed}\r\n\r\n"
                "\tThis mail is automatically generated.\r\n\t\t\t\t\t\t\r\n"
                "\tRegards,\r\n\tVector Support."
            )
        elif branch == "force-norm-blocked":
            body = "Force norm changes have not been done as"
            if values.get("approval_missing") is True:
                body += "\r\n\tThere is no approval from Vector consultant."
            if values.get("master_invalid") is True:
                body += "\r\n\tMaster file/table is invalid."
            body += (
                "\r\n\r\n\tThis mail is automatically generated.\r\n\t\t\t\t\t\r\n"
                "\tRegards,\r\n\tVector Support."
            )
        elif branch == "force-norm-failed":
            body = (
                "\r\n\tToday's Force Norm Change Status \r\n"
                f"\tRequested Force Norm Change(s) : {requested}\r\n"
                f"\tSuccessful Force Norm Change(s) : {succeeded}\r\n"
                f"\tFailed Force Norm Change(s) : {failed}\r\n\r\n"
                "\tAttached csv has details of failed force norm changes. \r\n\r\n"
                "\tThis mail is automatically generated.\r\n\t\t\t\t\t\r\n"
                "\tRegards,\r\n\tVector Support."
            )
        else:
            raise AlertInputError(f"unsupported message branch for {name}: {branch}")
        return subject, body
    if name == "PhaseInPhaseOutExceptionAlert":
        return _varchar100(f"{site}|VectorFLOW : Phase-in Phase-out Exception Alert [{run_day}]"), (
            "\r\nAttached file has details of Phase-in Phase-out data on which processing cannot be done.\r\n"
            "\t\t\t\t\t\t\r\nThis mail is automatically generated.\r\n\t\t\t\t\t\r\n"
            "Regards,\r\nVector Support."
        )
    if name == "RejectedInvoiceAlert":
        return _varchar100(f"{site}|VectorFLOW : Rejected Invoice Alert [{run_day}]"), (
            "\r\nOne or many items from invoice file/table are not part of master data, Hence those invoices are rejected.\r\n"
            "Attached ZIP file contains the list of rejected invoices.\r\n\t\t\t\t\t\t\r\n"
            "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
        )
    if name == "DBMNormChangeAlert":
        report_date = _as_date(values.get("report_date"), "values.report_date")
        subject = f"{site}|VectorFLOW : Accepted Norms -{_style_106(report_date)}"
        if branch == "no-accepted-norms":
            body = (
                "\r\nNorm suggstions were not accepted.\r\n\r\nThis mail is automatically generated.\r\n"
                "\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        elif branch == "accepted-norms":
            body = (
                "\r\nAttached file has details of accepted norms. \r\n\r\nThis mail is automatically generated.\r\n"
                "\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        else:
            raise AlertInputError(f"unsupported message branch for {name}: {branch}")
        return subject, body
    if name == "RunFinishAlert":
        if branch == "run-failure-batch":
            subject = f"{site}|VectorFLOW : Run Failure [{run_day}]"
            body = (
                "\r\nVectorFLOW run was aborted as there is a problem in execution of Scheduled Task. Please contact Vector Support.\r\n"
                "\t\t\r\nThis mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        elif branch == "run-failure-daily-empty":
            subject = f"{site}|VectorFLOW : Run Failure [{run_day}]"
            body = (
                "\r\nVectorFLOW run was not completed successfully as there was a problem in reading Daily Data.\r\n\r\n"
                "This mail is automatically generated.\r\n\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        elif branch == "run-finish":
            subject = f"{site}|VectorFLOW : Run Finish Alert [{run_day}]"
            body = (
                "\r\nVectorFLOW run is over.\r\n\t\t\r\nThis mail is automatically generated.\r\n"
                "\t\t\t\t\t\r\nRegards,\r\nVector Support."
            )
        else:
            raise AlertInputError(f"unsupported message branch for {name}: {branch}")
        return _varchar100(subject), body
    if name == "BPRExceptionAlert":
        return _varchar100(f"{site}|VectorFLOW : BPR Exceptions Alert [{run_day}]"), (
            "\r\nOne or many of the items in the Buffer Penetation Report have Stock And/Or GIT values very high as compared to its Norm. As a result Technical/Economic Buffer Penetration has exceeded maximum limit.\r\n"
            "List of such items is attached.\r\n"
            "Note that the VectorFLOW has assigned maximum possible Technical/Economic Buffer Penetration for such items. \r\n\r\n"
            "Please check Stock/GIT values and make necessary corrections in the ERP if required.\r\n"
            "\t\t\t\t\t\t\r\nThis mail is automatically generated.\r\n\t\t\t\t\t\r\n"
            "Regards,\r\nVector Support."
        )
    if name == "DailyDataValidationErrorAlert":
        return _varchar100(f"{site}|VectorFLOW : Data Validation error Exceptions Alert [{run_day}]"), (
            "\r\nDuring the execution of the data validation utility, one or more input files failed to meet the defined data quality checks.\r\n\r\n"
            "Please review the attached error file for details, and make the necessary corrections if required.\r\n"
            "\t\t\t\t\t\t\r\nThis mail is automatically generated. No reply is necessary.\r\n"
            "\t\t\t\t\t\r\nRegards,\r\nVector Support."
        )
    raise AlertInputError(f"unsupported message source: {name}")


def _base_result(seed: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": INTENT_SCHEMA,
        "alert_name": seed["name"],
        "seed_source": SEED_SOURCE,
        "seed_source_sha256": SEED_SOURCE_SHA256,
        "stage": seed["stage"],
        "branch": seed["branch"],
        "status": None,
        "reason": None,
        "recipient": config["recipient"],
        "cc_recipient": config["cc_recipient"],
        "profile": config["profile"],
        "site": config["site"],
        "business_date": str(_as_date(config["business_date"], "business_date")),
        "run_datetime": _as_datetime(config["run_datetime"], "run_datetime").isoformat(),
        "subject_branch": seed["branch"],
        "body_branch": seed["branch"],
        "subject": None,
        "body": None,
        "source": {"wrapper": seed["wrapper"], "sql": seed["sql"]},
        "values": {},
        "attachment": None,
        "send_performed": False,
    }


def _finish(result: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    result["status"] = status
    result["reason"] = reason
    result["subject_branch"] = result["branch"]
    result["body_branch"] = result["branch"]
    return result


def _validate_settings(settings: Mapping[str, str]) -> None:
    expected = set(_SEEDS)
    actual = set(settings)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise AlertInputError(f"alert settings must be the exact 14-row roster; missing={missing}, extra={extra}")
    invalid = {name: value for name, value in settings.items() if value not in {"0", "1"}}
    if invalid:
        raise AlertInputError(f"alert settings must use literal '0'/'1': {invalid}")


def _require_configuration(config: Mapping[str, Any]) -> None:
    missing = [key for key in _REQUIRED_CONFIGURATION if key not in config]
    if missing:
        raise AlertInputError(f"missing alert configuration: {missing}")
    for key in ("recipient", "cc_recipient", "profile", "site"):
        if not isinstance(config[key], str):
            raise AlertInputError(f"alert configuration {key} must be text")


def _population(populations: Mapping[str, Sequence[Mapping[str, Any]]], name: str) -> Sequence[Mapping[str, Any]]:
    if name not in populations:
        raise AlertInputError(f"missing source population: {name}")
    rows = populations[name]
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise AlertInputError(f"source population {name} must be a row sequence")
    if any(not isinstance(row, Mapping) for row in rows):
        raise AlertInputError(f"source population {name} must contain row mappings")
    return rows


def _artifact(
    artifacts: Mapping[str, Mapping[str, Any]],
    name: str,
    *,
    members: tuple[str, ...] | None = None,
    require_size: bool = False,
) -> dict[str, Any]:
    if name not in artifacts:
        raise AlertInputError(f"missing artifact fact: {name}")
    source = artifacts[name]
    if "available" not in source:
        raise AlertInputError(f"artifact {name} is missing available")
    if not isinstance(source["available"], bool):
        raise AlertInputError(f"artifact {name}.available must be boolean")
    source_members = source.get("members", [])
    if isinstance(source_members, (str, bytes)) or not isinstance(source_members, Sequence) or any(not isinstance(member, str) for member in source_members):
        raise AlertInputError(f"artifact {name}.members must be a text sequence")
    result: dict[str, Any] = {"name": name, "available": source["available"], "members": list(source_members)}
    if require_size:
        if "byte_size" not in source:
            raise AlertInputError(f"artifact {name} is missing byte_size")
        result["byte_size"] = _nonnegative_int(source["byte_size"], f"{name}.byte_size")
        if result["byte_size"] > 0 and not result["available"]:
            raise AlertInputError(f"artifact {name} cannot have positive byte_size while unavailable")
    if members is not None and result["available"] and result["members"] != list(members):
        raise AlertInputError(f"artifact {name} members must be exactly {list(members)}")
    return result


def _config_flag(config: Mapping[str, Any], name: str) -> bool:
    if name not in config:
        raise AlertInputError(f"missing alert configuration: {name}")
    value = config[name]
    if value in (True, 1, "1"):
        return True
    if value in (False, 0, "0"):
        return False
    raise AlertInputError(f"configuration {name} must be a 0/1 flag")


def _recipient_suppressed(recipient: Any) -> bool:
    try:
        return ascii_equal(recipient, "") or ascii_equal(recipient, "Not-Defined")
    except ValueError as exc:
        raise AlertInputError(str(exc)) from exc


def _sqlcmd_ascii(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.isascii():
        raise AlertInputError(f"UNQUALIFIED_SCALAR_DOMAIN: ASCII SQLCMD {name}")
    if any(character in value for character in ("'", "\r", "\n", "\x00")):
        raise AlertInputError(f"UNQUALIFIED_SCALAR_DOMAIN: quoted SQLCMD {name}")
    return value


def _style_106(value: date | datetime) -> str:
    actual = value.date() if isinstance(value, datetime) else value
    return f"{actual.day:02d} {MONTHS[actual.month - 1]} {actual.year:04d}"


def _varchar100(value: str) -> str:
    # Every caller is already in the bounded ASCII domain, so SQL varchar(100)
    # character truncation is identical to slicing the first 100 code points.
    return value[:100]


def _sql_int(values: Mapping[str, Any], name: str) -> str:
    if name not in values:
        raise AlertInputError(f"missing message value: {name}")
    value = values[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AlertInputError(f"message value {name} must be a SQL integer")
    return str(value)


def _as_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is not None or value.microsecond % 1000:
            raise AlertInputError(f"{name} must be timezone-naive with millisecond precision")
        try:
            return parse_datetime(value.isoformat(timespec="milliseconds"))
        except ValueError as exc:
            raise AlertInputError(f"{name} must be a qualified native datetime") from exc
    if isinstance(value, str):
        try:
            return parse_datetime(value)
        except ValueError as exc:
            approved_midnight = re.fullmatch(r"(\d{4}-\d{2}-\d{2}) 12:00AM", value)
            if approved_midnight:
                try:
                    return parse_datetime(f"{approved_midnight.group(1)}T00:00:00")
                except ValueError:
                    pass
            raise AlertInputError(f"{name} must be a qualified native datetime") from exc
    raise AlertInputError(f"{name} must be a qualified native datetime")


def _as_date(value: Any, name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise AlertInputError(f"{name} must be an ISO date") from exc
    raise AlertInputError(f"{name} must be an ISO date")


def _same_datetime(value: Any, target: datetime) -> bool:
    if value is None:
        return False
    return _as_datetime(value, "source datetime") == target


def _same_date(value: Any, target: date) -> bool:
    if value is None:
        return False
    return _as_date(value, "source date") == target


def _date_at_or_after(value: Any, lower: date) -> bool:
    if value is None:
        return False
    actual = _as_date(value, "source date")
    return actual >= lower


def _number(value: Any) -> float:
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise AlertInputError(f"expected numeric source value, got {value!r}") from exc


def _sql_number_compare(value: Any, operator: str, target: float) -> bool:
    """Apply the numeric comparisons used by the source with SQL NULL semantics."""

    if value is None:
        return False
    actual = _number(value)
    if operator == "=":
        return actual == target
    if operator == "<":
        return actual < target
    if operator == ">":
        return actual > target
    raise AssertionError(operator)


def _nonnull_key(*values: Any) -> tuple[Any, ...] | None:
    return None if any(value is None for value in values) else tuple(values)


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AlertInputError(f"{name} must be a non-negative integer")
    return value


def _positive_int(config: Mapping[str, Any], name: str) -> int:
    if name not in config:
        raise AlertInputError(f"missing alert configuration: {name}")
    value = config[name]
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AlertInputError(f"configuration {name} must be a positive integer")
    return value

