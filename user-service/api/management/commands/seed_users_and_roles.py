import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import (
    Permission,
    ApplicationMaster,
    Roles,
    User,
    FeatureMaster,
    UserserviceConfig,
    ADS_Config,
    AlertEmailCCDetails
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds user-role-permission-location data into the database with full sync detection.'

    all_permission_urls = []
    all_feature_name = []

    def ask_confirmation(self, step_name):
        """Prompt the user for confirmation to run a seeding step"""
        while True:
            choice = input(f"Do you want to run '{step_name}' seeding? (y/n): ").strip().lower()
            if choice in ["y", "yes"]:
                return True
            elif choice in ["n", "no"]:
                return False
            else:
                self.stdout.write(self.style.WARNING("Please enter 'y' or 'n'."))

    def handle(self, *args, **options):
        try:
            if self.check_seeding_status():
                return

            self.stdout.write(self.style.SUCCESS("Starting seeding process..."))


            # Define seeding steps
            seeding_tables = [
                ("Applications", self.seed_applications),
                ("Userservice-Config", self.seed_userservice_config),
                ("Ads_Config", self.seed_ads_config),
                ("seed_alert_email_cc_details",self.seed_alert_email_cc_details),
                ("Permissions", self.seed_permissions),
                ("Roles", self.seed_roles),
                ("Role-Permissions", self.seed_role_permissions),
                ("Users", self.seed_users),
                ("User-Roles", self.seed_user_roles),
                ("Features", self.seed_features),
                ("Role-Feature", self.seed_role_features)    
            ]

            seeding_table = []

            for seeding_name, seeding_function in seeding_tables:
                if self.ask_confirmation(seeding_name):
                    try:
                        with transaction.atomic():
                            seeding_function()
                        seeding_table.append(seeding_name)
                        self.stdout.write(self.style.SUCCESS(f"✔ Completed: {seeding_name}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"✘ Failed: {seeding_name} ({e})"))

            if seeding_table:
                self.stdout.write(self.style.SUCCESS(f"\nCompleted: {', '.join(seeding_table)}"))
            else:
                self.stdout.write(self.style.WARNING("No steps executed."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))

    def check_seeding_status(self):
        """Check if seeding has already been performed"""
        # Count existing entries
        total = sum([
            Permission.objects.count(),
            ApplicationMaster.objects.count(),
            Roles.objects.count(),
            User.objects.count(),
        ])

        if total > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Seeding appears to have been performed already. Found {total} total seeded entries.'
                )
            )
            if not self.confirm_proceed():
                self.stdout.write(self.style.SUCCESS('Seeding cancelled by user.'))
                return True

        return False

    def confirm_proceed(self):
        """Ask user for confirmation to proceed with updates"""
        try:
            response = input('Do you want to proceed anyway? (y/N): ').lower().strip()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    def seed_permissions(self):
        """Seed the permissions data - only update when values actually change"""
        logger.info("Seeding Permissions...")
        
        created_count = 0   
        skipped_count = 0
        
        permissions = [
                {'name': 'VectorFlow. Master Data Management. Control Panel', 'code': 'MDM-CP', 'description': 'VectorFlow. Master Data Management. Control Panel', 'url': '/mta/master-data-management/control-panel'},
                {'name': 'VectorFlow. Master Data Management. View-Modify', 'code': 'MDM-CP-VM', 'description': 'VectorFlow. Master Data Management. View-Modify', 'url': '/mta/master-data-management/control-panel/view-modify'},
                {'name': 'VectorFlow. Master Data Management. Add', 'code': 'MDM-CP-ADD', 'description': 'VectorFlow. Master Data Management. Add', 'url': '/mta/master-data-management/control-panel/add'},
                {'name': 'VectorFlow. Master Data Management. Delete', 'code': 'MDM-CP-DEL', 'description': 'VectorFlow. Master Data Management. Delete', 'url': '/mta/master-data-management/control-panel/delete'},
                {'name': 'VectorFlow. Master Data Management. Task Pending For Review', 'code': 'MDM-TP', 'description': 'VectorFlow. Master Data Management. Task Pending For Review', 'url': '/mta/master-data-management/task-pending'},
                {'name': 'VectorFlow. Master Data Management. Task Status', 'code': 'MDM-TS', 'description': 'VectorFlow. Master Data Management. Task Status', 'url': '/mta/master-data-management/task-status'},
                {'name': 'VectorFlow. Master Data Management. Saved Drafts', 'code': 'MDM-SD', 'description': 'VectorFlow. Master Data Management. Saved Drafts', 'url': '/mta/master-data-management/saved-drafts'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. Planning', 'code': 'MTA-P', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Planning', 'url': '/mta/supply-chain-intelligence-hub/planning'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. BPR', 'code': 'MTA-BPR', 'description': 'VectorFlow. Supply Chain Intelligence Hub. BPR', 'url': '/mta/supply-chain-intelligence-hub/bpr'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. BOR', 'code': 'MTA-BOR', 'description': 'VectorFlow. Supply Chain Intelligence Hub. BOR', 'url': '/mta/supply-chain-intelligence-hub/bor'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. RRR', 'code': 'MTA-RRR', 'description': 'VectorFlow. Supply Chain Intelligence Hub. RRR', 'url': '/mta/supply-chain-intelligence-hub/rrr'},
                {'name': 'VectorFlow. Insights and Trends. Guided Insights', 'code': 'MTA-GI', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Guided Insights', 'url': '/mta/insights-and-trends/guided-insights'},
                {'name': 'VectorFlow. Insights and Trends. Research Insights', 'code': 'MTA-RI', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Research Insights', 'url': '/mta/insights-and-trends/research-insights'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. Open Expediting Requests', 'code': 'MTA-OER', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Open Expediting Requests', 'url': '/mta/supply-chain-intelligence-hub/open-expediting-requests'},
                {'name': 'VectorFlow. Insights and Trends. Buffer Trend Report (BTR)', 'code': 'MTA-BTR', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Buffer Trend Report (BTR)', 'url': '/mta/insights-and-trends/buffer-trend-report'},
                {'name': 'VectorFlow. Insights and Trends. Buffer Trends', 'code': 'MTA-BT', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Buffer Trends', 'url': '/mta/insights-and-trends/buffer-trends'},
                {'name': 'VectorFlow. DBM. DBM Norm Suggestions', 'code': 'MTA-DBMNS', 'description': 'VectorFlow. DBM. DBM Norm Suggestions', 'url': '/mta/dbm/dbm-norm-suggestions'},
                {'name': 'VectorFlow. Logistics. Intransit Whereabouts', 'code': 'MTA-IW', 'description': 'VectorFlow. Logistics. Intransit Whereabouts', 'url': '/mta/logistics/intransit-whereabouts'},
                {'name': 'VectorFlow. Procurement. Planning. Simulative Fullkit', 'code': 'MTO-PL-SF', 'description': 'VectorFlow. Procurement. Planning. Simulative Fullkit', 'url': '/mto/planning/simulative-fullkit'},
                {'name': 'VectorFlow. Procurement. Planning.', 'code': 'MTO-PR-PL', 'description': 'VectorFlow. Procurement. Planning.', 'url': '/mto/procurement-planning/planning'},
                {'name': 'VectorFlow. Procurement. Material Coverage Open Sales.', 'code': 'MTO-PR-MCOS', 'description': 'VectorFlow. Procurement. Material Coverage Open Sales.', 'url': '/mto/procurement/material-coverage-open-sales'},
                {'name': 'VectorFlow. Master Data Management. Data Modification History', 'code': 'MDM-DMH', 'description': 'VectorFlow. Master Data Management. Data Modification History', 'url': '/mta/master-data-management/data-modification-history'},
                {'name': 'VectorFlow. Procurement. Insights and Trends Sales. RMPM Orderwise Coverage', 'code': 'MTO-PR-RMPM', 'description': 'VectorFlow. Procurement. Insights and Trends Sales. RMPM Orderwise Coverage', 'url': '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage'},
                {'name': 'VectorFlow. Procurement. Material Requirement', 'code': 'MTO-PR-MR', 'description': 'VectorFlow. Procurement. Material Requirement', 'url': '/mto/procurement/material-requirement'},
                {'name': 'VectorFlow. Procurement. Insights and Trends. Day Wise Coverage', 'code': 'MTO-PR-DWC', 'description': 'VectorFlow. Procurement. Insights and Trends. Day Wise Coverage', 'url': '/mto/procurement/insights-and-trends/day-wise-coverage'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. SDR', 'code': 'MTA-SDR', 'description': 'VectorFlow. Supply Chain Intelligence Hub. SDR', 'url': '/mta/supply-chain-intelligence-hub/sdr'},
                {'name': 'VectorFlow. Procurement. Insights and Trends. RMPM Buffer Trend', 'code': 'MTO-PR-RMPMBT', 'description': 'VectorFlow. Procurement. Insights and Trends. RMPM Buffer Trend', 'url': '/mto/procurement/insights-and-trends/rmpm-buffer-trends'},
                {'name': 'VectorFlow. Procurement. Insights and Trends. Expediting - RM & Supplier', 'code': 'MTO-PR-RMPM R&S', 'description': 'VectorFlow. Procurement. Insights and Trends. Expediting - RM & Supplier', 'url': '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers'},
                {'name': 'VectorFlow. Production. Enquiry Response', 'code': 'ER', 'description': 'VectorFlow. Production. Enquiry Response', 'url': '/mto/production-planning-scheduling/enquiry-response'},
                {'name': 'VectorFlow. Production. STPL Full Kit', 'code': 'MTO-PR-STPL-FULL-KIT', 'description': 'VectorFlow. Production. STPL Full Kit', 'url': '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits'},
                {'name': 'VectorFlow. Production. BM Trend', 'code': 'MTO-PR-BM-TRENDS', 'description': 'VectorFlow. Production. BM Trend', 'url': '/mto/production-planning-scheduling/insight-and-trends/bm-trends'},
                {'name': 'VectorFlow. Production. Full Kit Assignment', 'code': 'MTO-PR-FK-ASSGN', 'description': 'VectorFlow. Production. Full Kit Assignment', 'url': '/mto/production-planning-scheduling/full-kit-assignment'},
                {'name': 'VectorFlow.Production.OrderReScheduling', 'code': 'MTO-PR-ORD-RESCHEDULE', 'description': 'VectorFlow.Production.OrderReScheduling', 'url': '/mto/production-planning-and-scheduling/order-rescheduling'},
                {'name': 'VectorFlow.Production.InsightsTrends.OrderRisks', 'code': 'MTO-IT-OR', 'description': 'VectorFlow.Production.InsightsTrends.OrderRisks', 'url': '/mto/production-planning-scheduling/insight-and-trends/order-at-risk'},
                {'name': 'VectorFlow.Production.Dpt.Bm.Rprt', 'code': 'MTO-PR-DPT-REPORT', 'description': 'VectorFlow.Production.Dpt.Bm.Rprt', 'url': '/mto/production-planning-scheduling/deptwise-bm-report'},
                {'name': 'VectorFlow.Production.Dynamic.Release.Management', 'code': 'MTO-PR-DRM', 'description': 'VectorFlow.Production.Dynamic.Release.Management', 'url': '/mto/production-planning-scheduling/dynamic-release-mangement'},
                {'name': 'VectorFlow.Production.InsightTrends.OrderBalance', 'code': 'MTO-PR-IT-OB', 'description': 'VectorFlow.Production.InsightTrends.OrderBalance', 'url': '/mto/production-planning-scheduling/insight-and-trends/order-balance'},
                {'name': 'VectorFlow.Production.InsightsTrends.FOLSummary', 'code': 'MTO-PR-IT-FOL-SUMM', 'description': 'VectorFlow.Production.InsightsTrends.FOLSummary', 'url': '/mto/production-planning-scheduling/insights-and-trends/fol-summary'},
                {'name': 'VectorFlow.POOGI.InsightsTrends.OtifAnalysis', 'code': 'MTO-POOGI-IT-OTIF-ANLYS', 'description': 'VectorFlow.POOGI.InsightsTrends.OtifAnalysis', 'url': '/mto/poogi/insight-and-trends/otif-analysis'},
                {'name': 'VectorFlow.Poogi.InsightTrends.Resource.WIP.Profile', 'code': 'MTO-POOGI-IT-RU-WIP', 'description': 'VectorFlow.Poogi.InsightTrends.Resource.WIP.Profile', 'url': '/mto/poogi/insight-and-trends/resource-utilization-wip-profile'},
                {'name': 'VectorFlow.POOGI.Reasons.DelayedOrders', 'code': 'MTO-POOGI-RDO', 'description': 'VectorFlow.POOGI.Reasons.DelayedOrders', 'url': '/mto/poogi/reasons-for-delayed-orders'},
                {'name': 'VectorFlow.Production.DDQ', 'code': 'MTO-PR-DDQ', 'description': 'VectorFlow.Production.DDQ', 'url': '/mto/production-planning-and-scheduling/due-date-quotation'},
                {'name': 'VectorFlow.Poogi.OTANDIF', 'code': 'MTO.OT.AND.IF', 'description': 'VectorFlow.Poogi.OTANDIF', 'url': '/mto/poogi/insight-and-trends/ot-and-if-analysis'},
                {'name': 'VectorFlow.Poogi.InsightsTrends.TrendsOfFailureReason', 'code': 'MTO-POOGI-IT-FAILURE-REASON', 'description': 'VectorFlow.Poogi.InsightsTrends.TrendsOfFailureReason', 'url': '/mto/poogi/insight-and-trends/trend-of-failure-reason'},
                {'name': 'VectorFlow.Poogi.InsightTrends.LeadTime', 'code': 'MTO-POOGI-IT-LT', 'description': 'VectorFlow.Poogi.InsightTrends.LeadTime', 'url': '/mto/poogi/insight-and-trends/lead-time'},
                {'name': 'VectorFlow.Production.InsightTrends.ElapsedTime', 'code': 'MTO-PR-IT-ET', 'description': 'VectorFlow.Production.InsightTrends.ElapsedTime', 'url': '/mto/production-planning-scheduling/insights-and-trends/elapsed-time'},
                {'name': 'VectoFlow.POOGI.InsightTrends.TopFailureReaons', 'code': 'MTO-POOGI-IT-TFR', 'description': 'VectoFlow.POOGI.InsightTrends.TopFailureReaons', 'url': '/mto/poogi/insight-and-trends/top-failure-reasons'},
                {'name': 'Vector.Production.Overall.BM.Report', 'code': 'MTO-PR-OBR', 'description': 'Vector.Production.Overall.BM.Report', 'url': '/mto/production-planning-scheduling/overall-bm-report'},
                {'name': 'VectorFlow.IntelligenceHub.Delivery.BMTrend', 'code': 'MTO-IH-DP-BM', 'description': 'VectorFlow.IntelligenceHub.Delivery.BMTrend', 'url': '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends'},
                {'name': 'VectorFlow.IntelligenceHub.Delivery.OTIFAnalysis', 'code': 'MTO-IH-DP-OTIF', 'description': 'VectorFlow.IntelligenceHub.Delivery.OTIFAnalysis', 'url': '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis'},
                {'name': 'VectorFlow.IntelligenceHub.Delivery.OTANDIF', 'code': 'MTO-IH-DP-OT-AND-IF', 'description': 'VectorFlow.IntelligenceHub.Delivery.OTANDIF', 'url': '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis'},
                {'name': 'VectorFlow.IntelligenceHub.Delivery.LeadTime', 'code': 'MTO-IH-DP-LD', 'description': 'VectorFlow.IntelligenceHub.Delivery.LeadTime', 'url': '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time'},
                {'name': 'VectorFlow.IntelligenceHub.Congestion.ElapsedTime', 'code': 'MTO-IH-CA-ET', 'description': 'VectorFlow.IntelligenceHub.Congestion.ElapsedTime', 'url': '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time'},
                {'name': 'VectorFlow.IntelligenceHub.Congestion.OrderAtRisk', 'code': 'MTO-IH-CA-OAR', 'description': 'VectorFlow.IntelligenceHub.Congestion.OrderAtRisk', 'url': '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk'},
                {'name': 'VectorFlow.IntelligenceHub.Congestion.OrderBalance', 'code': 'MTO-IH-CA-OB', 'description': 'VectorFlow.IntelligenceHub.Congestion.OrderBalance', 'url': '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.FOL', 'code': 'MTO-IH-FW-FOL', 'description': 'VectorFlow.IntelligenceHub.Forward.FOL', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.STPL.FK', 'code': 'MTO-IH-FW-STPL-FK', 'description': 'VectorFlow.IntelligenceHub.Forward.STPL.FK', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.Day.WiseCoverage', 'code': 'MTO-IH-FW-DWC', 'description': 'VectorFlow.IntelligenceHub.Forward.Day.WiseCoverage', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.RM.PM.Orderwise', 'code': 'MTO-IH-FW-RMPM-OW-COV', 'description': 'VectorFlow.IntelligenceHub.Forward.RM.PM.Orderwise', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.RM.Exp.Supp', 'code': 'MTO-IH-FW-RM-EXP', 'description': 'VectorFlow.IntelligenceHub.Forward.RM.Exp.Supp', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier'},
                {'name': 'VectorFlow.IntelligenceHub.Forward.RM.PM.Buffer.Trend', 'code': 'MTO-IH-FW-RM-PM-BUF-TREND', 'description': 'VectorFlow.IntelligenceHub.Forward.RM.PM.Buffer.Trend', 'url': '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend'},
                {'name': 'VectorFlow.IntelligenceHub.ImprovementAreas.Top.Failure.Reason', 'code': 'MTO-IH-IA-TFR', 'description': 'VectorFlow.IntelligenceHub.ImprovementAreas.Top.Failure.Reason', 'url': '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons'},
                {'name': 'VectorFlow.IntelligenceHub.ImprovementAreas.Trend.Failure.Reason', 'code': 'MTO-IH-IA-TFFR', 'description': 'VectorFlow.IntelligenceHub.ImprovementAreas.Trend.Failure.Reason', 'url': '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons'},
                {'name': 'VectorFlow.IntelligenceHub.ImprovementAreas.Resource.WIP', 'code': 'MTO-IH-IA-RS-WIP', 'description': 'VectorFlow.IntelligenceHub.ImprovementAreas.Resource.WIP', 'url': '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. Merchandising Grid', 'code': 'MTA-MCGRID', 'description': 'VectorFlow. Supply Chain Intelligence Hub. Merchandising Grid', 'url': '/supply-chain-intelligence-hub/merchandising-grid'},
                {'name': 'VectorFlow : Landing Page', 'code': 'LP', 'description': 'VectorFlow : Landing Page', 'url': '/landing-page'},
                {'name': 'MDM.control Panel interceptor', 'code': 'MDM-MTO-CP', 'description': 'MDM.control Panel interceptor', 'url': '/masters-interceptor/control-panel'},
                {'name': 'MDM.saved-drafts interceptor', 'code': 'MDM-MTO-SD', 'description': 'MDM.saved-drafts interceptor', 'url': '/masters-interceptor/saved-drafts'},
                {'name': 'MDM.task-pending interceptor', 'code': 'MDM-MTO-TP', 'description': 'MDM.task-pending interceptor', 'url': '/masters-interceptor/task-pending'},
                {'name': 'MDM.taskStatus interceptor', 'code': 'MDM-MTO-TS', 'description': 'MDM.taskStatus interceptor', 'url': '/masters-interceptor/task-status'},
                {'name': 'MDM.data-modification interceptor', 'code': 'MDM-MTO-DM', 'description': 'MDM.data-modification interceptor', 'url': '/masters-interceptor/data-modification-history'},
                {'name': 'MDM.MTO.control.panel', 'code': 'MTO-CP', 'description': 'MDM.MTO.control.panel', 'url': '/mto/master-data-management/control-panel'},
                {'name': 'MDM.MTO.control.panel.add', 'code': 'MTO-CP-ADD', 'description': 'MDM.MTO.control.panel.add', 'url': '/mto/master-data-management/control-panel/add'},
                {'name': 'MDM.MTO.control.panel.modify', 'code': 'MTO-CP-MOD', 'description': 'MDM.MTO.control.panel.modify', 'url': '/mto/master-data-management/control-panel/view-modify'},
                {'name': 'MDM.MTO.saved', 'code': 'MTO-SD', 'description': 'MDM.MTO.saved', 'url': '/mto/master-data-management/saved-drafts'},
                {'name': 'MDM.MTO.taskPending', 'code': 'MDM.MTO.TaskP', 'description': 'MDM.MTO.taskPending', 'url': '/mto/master-data-management/task-pending'},
                {'name': 'MDM.MTO.taskStatus', 'code': 'MDM.MTO.TaskS', 'description': 'MDM.MTO.taskStatus', 'url': '/mto/master-data-management/task-status'},
                {'name': 'MDM.MTO.dmh', 'code': 'MTO-DMH', 'description': 'MDM.MTO.dmh', 'url': '/mto/master-data-management/data-modification-history'},
                {'name': 'VectorFlow.Profile', 'code': 'VF-P', 'description': 'VectorFlow. Profile', 'url': '/profile'},
                {'name': 'RRR-color', 'code': 'rrr-color-bandwise', 'description': 'rrr-color-bandwise', 'url': '/mta/supply-chain-intelligence-hub/rrr-color-bandwise'},
                {'name': 'SCIH-BOR-color', 'code': 'SCIH-BOR-color', 'description': 'SCIH-BOR-color', 'url': '/mta/supply-chain-intelligence-hub/bor-color-bandwise'},
                {'name': 'SCIH-Supplier-Wise-Allocation', 'code': 'SCIH-Supplier-Wise-Allocation', 'description': 'SCIH-Supplier-Wise-Allocation', 'url': '/mta/supply-chain-intelligence-hub/SupplierWiseAllocation'},
                {'name': 'mto-report-urls', 'code': 'mto-report-urls', 'description': 'mto-report-urls', 'url': 'mto-report-urls'},
                {'name': 'mta-report-urls', 'code': 'mta-report-urls', 'description': 'mta-report-urls', 'url': 'mta-report-urls'},
                {'name': 'VectorFlow. Supply Chain Intelligence Hub. EO', 'code': 'MTA-EO', 'description': 'VectorFlow. Supply Chain Intelligence Hub. EO', 'url': '/mta/supply-chain-intelligence-hub/eo'},
                {'name': 'VectorFlow.IntelligenceHub.FutureLoadChart', 'code': 'IH-FOLC', 'description': 'VectorFlow.IntelligenceHub.FutureLoadChart', 'url': '/mto/manufacturing-intelligence-hub/future-order-load-chart'},
                {'name': 'VectorFlow.Production.Scheduling', 'code': 'Scheduling', 'description': 'VectorFlow.Production.Scheduling', 'url': '/mto/production/scheduling'},
                {'name': 'VectorFlow.Production.FutureLoadChart', 'code': 'MTO-PR-FOLC', 'description': 'VectorFlow.Production.FutureLoadChart', 'url': '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart'},
                {'name': 'VectorFlow.LoginAuditReport', 'code': 'US-LAR', 'description': 'VectorFlow.LoginAuditReport', 'url': '/login-audit-report'},
                {'name': 'Bulk Upload', 'code': 'VectorFlow.Usermanagement.BulkUpload', 'description': 'bulk upload module', 'url': '/profile/bulk-upload'},
                {'name': 'MTO Scheduling', 'code': 'VectorFlow.Production.Scheduling', 'description': 'scheduling', 'url': 'mto/production/scheduling'}

        ]
        # This will be used to grant all permissions to the Super Admin role, vectorconsultant 
        Command.all_permission_urls = [p['url'] for p in permissions]

        # Fetch all existing permission names from the DB in a SINGLE query.
        existing_permissions_keys = set(Permission.objects.values_list('url', flat=True))
        logger.info(f"  Found {len(existing_permissions_keys)} existing permissions in the database.")
            
        # Determine which permissions need to be created.
        permissions_to_create = []
        for data in permissions:
            lookup_key = (data['url'])

            if lookup_key not in existing_permissions_keys:
                # Create a Permission object instance but DON'T save it yet.
                permissions_to_create.append(
                    Permission(
                        name=data['name'],
                        code=data['code'],
                        description=data['description'],
                        url=data['url']
                    )
                )
            else:
                skipped_count += 1

        # Create all the new permissions in a SINGLE bulk query.
        if permissions_to_create:
            created_objects = Permission.objects.bulk_create(permissions_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new permissions.")
        else:
            logger.info("  No new permissions to create.")
            
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Permissions: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_applications(self):
        """Seed the applications data - only update when values actually change"""
        logger.info("Seeding Applications...")
        
        created_count = 0
        skipped_count = 0
        
        applications = [
            {'application_id': 2, 'application_name': 'Distribution'},
            {'application_id': 3, 'application_name': 'Orders'},
        ]
        
        # Fetch all existing application IDs from the DB in a SINGLE query.
        existing_application_ids = set(ApplicationMaster.objects.values_list('application_id', 'application_name'))
        logger.info(f"  Found {len(existing_application_ids)} existing applications in the database.")

        # Determine which applications need to be created.
        applications_to_create = []
        for data in applications:
            lookup_key = (data['application_id'], data['application_name'])
            if lookup_key not in existing_application_ids:
                # Add a new ApplicationMaster instance to our list for bulk creation.
                applications_to_create.append(
                    ApplicationMaster(
                        application_id=data['application_id'],
                        application_name=data['application_name']
                    )
                )
            else:
                skipped_count += 1
                
        # Create all the new applications in a SINGLE bulk query.
        if applications_to_create:
            created_objects = ApplicationMaster.objects.bulk_create(applications_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new applications.")
        else:
            logger.info("  No new applications to create.")
    
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Applications: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_roles(self):
        """Seed the roles data - only update when values actually change"""
        logger.info("Seeding Roles...")
        
        created_count = 0
        skipped_count = 0
        
        roles = [  
            {'name': 'SuperAdmin', 'description': 'Must have access to all pages', 'code': 'SUPERADMIN', 'is_visible': False, 'application_id': 3},

            {'name': 'Admin', 'description': 'Must have access to User Administration', 'code': 'ADMIN', 'is_visible': True, 'application_id': 2},
            {'name': 'VectorConsultant', 'description': 'Must have access to all pages', 'code': 'VectorConsultant', 'is_visible': True, 'application_id': 2},
            {'name': 'DBMManager', 'description': 'No Description Available', 'code': 'DBMManager', 'is_visible': True, 'application_id': 2},
            {'name': 'BPRManager', 'description': 'No Description Available', 'code': 'BPRManager', 'is_visible': True, 'application_id': 2},
            {'name': 'MasterUpdater', 'description': 'No Description Available', 'code': 'MasterUpdater', 'is_visible': True, 'application_id': 2},
            {'name': 'MasterApprover', 'description': 'No Description Available', 'code': 'MasterApprover', 'is_visible': True, 'application_id': 2},
            {'name': 'Supplier', 'description': 'Only has access to Supplier Dispatch Report and Supplier Wise Allocation Report', 'code': 'Supplier', 'is_visible': True, 'application_id': 2},
            {'name': 'PermissionsManager', 'description': 'No Description Available', 'code': 'PermissionsManager', 'is_visible': True, 'application_id': 2},


            {'name': 'MTO Admin', 'description': 'Only has access to User Administration', 'code': 'MTOADMIN', 'is_visible': True, 'application_id': 3},
            {'name': 'MTO VectorConsultant', 'description': 'Must have access to all pages', 'code': 'MTOVectorConsultant', 'is_visible': True, 'application_id': 3},
            {'name': 'Salesperson', 'description': 'Only has access to Enquiry Response', 'code': 'Salesperson', 'is_visible': True, 'application_id': 3},
            {'name': 'Master Scheduler', 'description': 'Only has access to DDQ, Order rescheduling', 'code': 'MasterScheduler', 'is_visible': True, 'application_id': 3},
            {'name': 'Production Planner', 'description': 'No Description Available', 'code': 'ProductionPlanner', 'is_visible': True, 'application_id': 3},
            {'name': 'Production Planner - View Only', 'description': 'No Description Available', 'code': 'ProductionPlanner-ViewOnly', 'is_visible': True, 'application_id': 3},
            {'name': 'Dept Manager', 'description': 'Only has access to Dept-wise BM Report', 'code': 'DeptManager', 'is_visible': True, 'application_id': 3},
            {'name': 'Dept Manager - View Only', 'description': 'Only has access to Dept-wise BM Report', 'code': 'DeptManager-ViewOnly', 'is_visible': True, 'application_id': 3},
            {'name': 'Production Manager - View Only', 'description': 'Only has Overall Production Incharge', 'code': 'ProductionManager-ViewOnly', 'is_visible': True, 'application_id': 3},
            {'name': 'Production Manager', 'description': 'Only has Overall Production Incharge', 'code': 'ProductionManager', 'is_visible': True, 'application_id': 3},
            {'name': 'Procurement Manager', 'description': 'Only has Procurement Incharge', 'code': 'ProcurementManager', 'is_visible': True, 'application_id': 3},
            {'name': 'Procurement Manager - View Only', 'description': 'Only has Procurement Incharge', 'code': 'ProcurementManager-ViewOnly', 'is_visible': True, 'application_id': 3},
            {'name': 'POOGI Manager', 'description': 'Only has POOGI Incharge', 'code': 'POOGIManager', 'is_visible': True, 'application_id': 3},
            {'name': 'Plant Head', 'description': 'Only has health of Production Check', 'code': 'PlantHead', 'is_visible': True, 'application_id': 3},
            {'name': 'Master Data Updater', 'description': 'Only has MDM', 'code': 'MasterDataUpdater', 'is_visible': True, 'application_id': 3},
            {'name': 'Master Data Approver', 'description': 'Only has MDM', 'code': 'MasterDataApprover', 'is_visible': True, 'application_id': 3},
            {'name': 'BMReportManager', 'description': 'Must have access to BM report Page', 'code': 'BMReportManager', 'is_visible': True, 'application_id': 3},
            {'name': 'SchedulerManager', 'description': 'Access to production Scheduler with run trigger Permission', 'code': 'SchedulerManager', 'is_visible': True, 'application_id': 3}, 
            {'name': 'SchedulerManagerViewer', 'description': 'Access to production Scheduler without run trigger', 'code': 'SchedulerManagerViewer', 'is_visible': True, 'application_id': 3},
            {'name': 'MasterRouteManager', 'description': 'user with this role can change route in DDQ but cant schedule it', 'code': 'MasterRouteManager', 'is_visible': True, 'application_id': 3}

        ]
        
        # Fetch all existing application IDs from the DB in a SINGLE query.
        existing_roles_name = set(Roles.objects.values_list('name', flat=True))
        logger.info(f"  Found {len(existing_roles_name)} existing applications in the database.")
        
        # Determine which applications need to be created.
        roles_to_create = []
        for data in roles:
            lookup_key= (data['name'])
            if lookup_key not in existing_roles_name:
                # Add a new ApplicationMaster instance to our list for bulk creation.
                roles_to_create.append(
                    Roles(
                        name=data['name'],
                        description=data['description'],
                        code=data['code'],
                        application_id=data['application_id'],
                        is_visible = data['is_visible']
                    )
                )
            else:
                # This one already exists, so we'll count it as skipped.
                skipped_count += 1
                
        # Create all the new applications in a SINGLE bulk query.
        if roles_to_create:
            created_objects = Roles.objects.bulk_create(roles_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new applications.")
        else:
            logger.info("  No new applications to create.")
        
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Roles: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_users(self):
        """Seed the users data - only update when values actually change"""
        logger.info("Seeding Users...")
        
        created_count = 0
        skipped_count = 0
        
        users = [
            {
                'email': 'vflow.support@vectorconsulting.in',
                'name': 'admin',
                'tc': True,
                'password': 'pbkdf2_sha256$390000$9QkGWMUDRQlFgayOJCBfff$mAa6+gOV4cL72KyWDrufyCYw+RFbhNjD7w/8SXVIDLY=',
                'is_admin': True,
                'is_active': True,
                'is_changed': True,
                'is_deleted': False,
                'theme_ui': 'NOIRFUSION'
            }
        ]
        
        # Fetch all existing user emails from the DB in a SINGLE query.
        existing_user_key = set(User.objects.values_list('name', 'email'))
        logger.info(f"  Found {len(existing_user_key)} existing users in the database.")

        # Identify which users are new. This loop has NO database queries.
        users_to_create = [] 
        for data in users:
            lookup_key = (data['name'], data['email'])
            if lookup_key not in existing_user_key:
                users_to_create.append(
                    User(
                        name=data['name'],
                        email=data['email'],
                        tc=data['tc'],
                        password=data['password'],
                        is_admin=data['is_admin'],
                        is_active=data['is_active'],
                        is_changed=data['is_changed'],
                        is_deleted=data['is_deleted'],
                        theme_ui=data['theme_ui']
                    )
                )
            else:
                # This user already exists, so we'll count it as skipped.
                skipped_count += 1
        
        # Create new users one-by-one to ensure password hashing is handled correctly.
        if users_to_create:
            created_objects = User.objects.bulk_create(users_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_objects} new users.")
        else:
            logger.info("  No new users to create.")
        
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Users: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_features(self):
        """Seed the feature data"""
        logger.info("Seeding Features...")
        
        created_count = 0
        skipped_count = 0
        
        features = [
            {"feature": "Order_Closing", "page": "Overall_BM", "is_active": True},
            {"feature": "Simulation_Enable", "page": "Procurment_Planning", "is_active": True},
            {"feature": "Schedule_Orders", "page": "DDQ", "is_active": True},
            {"feature": "Rewrite_Due_Date", "page": "Order_Rescheduling", "is_active": True},
            {"feature": "Unschedule_Order", "page": "Order_Rescheduling", "is_active": True},
            {"feature": "Add_Comments", "page": "Dept-Wise_BM_Report", "is_active": True},
            {"feature": "POOGI_Reasons", "page": "Reasons_For_Delayed_Order", "is_active": True},
            {"feature": "Change_Route", "page": "Full_Kit_Assignment", "is_active": True},
            {"feature": "Deselect_Orders", "page": "Full_Kit_Assignment", "is_active": True},
            {"feature": "Scheduler_Run_Trigger", "page": "Scheduling", "is_active": True},
            {"feature": "Bulk_upload", "page": "Bulk_Upload", "is_active": True}
        ]

        # This will be used to grant all features to the Super Admin role, vectorconsultant 
        Command.all_feature_name = [p['feature'] for p in features]

        # Fetch all existing application IDs from the DB in a SINGLE query.
        existing_features = set(FeatureMaster.objects.values_list('feature', flat=True))
        logger.info(f"  Found {len(existing_features)} existing features in the database.")
        
        # Determine which applications need to be created.
        feature_to_create = []
        for data in features:
            lookup_key= (data['feature'])
            if lookup_key not in existing_features:
                # Add a new ApplicationMaster instance to our list for bulk creation.
                feature_to_create.append(
                    FeatureMaster(
                        feature=data['feature'],
                        page=data['page'],
                        is_active=data['is_active']
                    )
                )
            else:
                # This one already exists, so we'll count it as skipped.
                skipped_count += 1
                
        # Create all the new applications in a SINGLE bulk query.
        if feature_to_create:
            created_objects = FeatureMaster.objects.bulk_create(feature_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new features.")
        else:
            logger.info("  No new features to create.")
        
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Features: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )

    def seed_role_features(self):
        """Seed the Role-Feature mappings from predefined static configuration (ROLE_FEATURE)"""
        self.stdout.write("Seeding Role-Feature mappings from static config...")

        created_count = 0
        skipped_count = 0
        error_count = 0

        role_feature_map = {
            # role_name: [feature_name, ...]

            "SuperAdmin" : self.all_feature_name,
            "VectorConsultant": self.all_feature_name,
            'MTO VectorConsultant': self.all_feature_name,
            
            "Production Manager": [
                "Order_Closing"
            ],
            "Procurement Manager": [
                "Simulation_Enable"
            ],
            "Master Scheduler": [
                "Schedule_Orders",
                "Rewrite_Due_Date",
                "Unschedule_Order"
            ],
            "Dept Manager": [
                "Add_Comments"
            ],
            "POOGI Manager": [
                "POOGI_Reasons"
            ],
            "Production Planner": [
                "Change_Route",
                "Deselect_Orders"
            ],
            "SchedulerManager": [
                "Scheduler_Run_Trigger"
            ]
        }

        # Fetch all required data from the DB 
        # Create a mapping of role_name -> role_id for quick lookups.
        roles_map = {role.name: role.id for role in Roles.objects.all()}
        logger.info(f"  Fetched {len(roles_map)} roles from the database.")

        # Create a mapping of permission_code -> permission_id for quick lookups.
        feature_map = {feature.feature: feature.id for feature in FeatureMaster.objects.all()}
        logger.info(f"  Fetched {len(feature_map)} features from the database.")
        
        # Get the through model for the many-to-many relationship.
        RoleFeatureLink = FeatureMaster.role_id.through
        
        # Fetch all existing role-permission links as a set of (role_id, permission_id) tuples for fast lookups.
        existing_links = set(RoleFeatureLink.objects.values_list('roles_id', 'featuremaster_id'))
        logger.info(f"  Found {len(existing_links)} existing role-feature links.")

        # Determine which role-permission links need to be created in memory.
        links_to_create = []
        for role_name, feature_name in role_feature_map.items():
            role_id = roles_map.get(role_name)
            if not role_id:
                self.stdout.write(self.style.ERROR(f"  Role with name '{role_name}' not found in the database. Skipping its feature."))
                error_count += len(feature_name)
                continue

            for feature in feature_name:
                feature_id = feature_map.get(feature)
                if not feature_id:
                    self.stdout.write(self.style.WARNING(f"  Features with name '{feature}' not found for role '{role_name}'. Skipping."))
                    error_count += 1
                    continue
                
                # If the link does not already exist, prepare it for creation.
                if (role_id, feature_id) not in existing_links:
                    links_to_create.append(
                        RoleFeatureLink(roles_id=role_id, featuremaster_id=feature_id)
                    )
                else:
                    skipped_count += 1

        # Create all the new links in a SINGLE bulk query.
        if links_to_create:
            created_objects = RoleFeatureLink.objects.bulk_create(links_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new role-feature links.")
        else:
            logger.info("  No new role-feature links to create.")
        
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f"Role-Feature: {created_count} created, {skipped_count} skipped, {error_count} errors"
            )
        )

    def seed_role_permissions(self):
        """Seed the Role-Permission mappings from predefined static configuration (ROLE_FUNCTION)"""
        self.stdout.write("Seeding Role-Permission mappings from static config...")

        created_count = 0
        skipped_count = 0
        error_count = 0

        role_permission_map = {
            # role_name: [permission_url, ...]
            "SuperAdmin" : self.all_permission_urls,
            # "VectorConsultant": self.all_permission_urls,

            #MTA
            "VectorConsultant" : [
               '/login-audit-report'
            ],
            "Admin": [
                '/landing-page',
                '/', 
                '/profile',
                '/login-audit-report'
            ],
            "DBMManager": [
                '/mta/supply-chain-intelligence-hub/planning', 
                '/mta/supply-chain-intelligence-hub/bpr', 
                '/mta/supply-chain-intelligence-hub/rrr', 
                '/mta/insights-and-trends/guided-insights', 
                '/mta/insights-and-trends/research-insights', 
                '/mta/supply-chain-intelligence-hub/open-expediting-requests', 
                '/mta/insights-and-trends/buffer-trend-report', 
                '/mta/insights-and-trends/buffer-trends', 
                '/mta/dbm/dbm-norm-suggestions', 
                '/mta/supply-chain-intelligence-hub/bor-color-bandwise',
            ],
            "BPRManager": [
                '/mta/supply-chain-intelligence-hub/planning', 
                '/mta/supply-chain-intelligence-hub/bpr', 
                '/mta/supply-chain-intelligence-hub/rrr', 
                '/mta/insights-and-trends/guided-insights', 
                '/mta/insights-and-trends/research-insights', 
                '/mta/supply-chain-intelligence-hub/open-expediting-requests', 
                '/mta/insights-and-trends/buffer-trend-report', 
                '/mta/insights-and-trends/buffer-trends', 
                '/mta/logistics/intransit-whereabouts', 
                '/mta/supply-chain-intelligence-hub/bor-color-bandwise'
            ],
            "MasterUpdater": [
                '/masters-interceptor/control-panel', 
                '/masters-interceptor/saved-drafts', 
                '/mta/master-data-management/control-panel', 
                '/mta/master-data-management/control-panel/view-modify', 
                '/mta/master-data-management/control-panel/add', 
                '/mta/master-data-management/control-panel/delete', 
                '/mta/master-data-management/task-status', 
                '/mta/master-data-management/saved-drafts', 
                'mta-report-urls', 
                'intercept-task-status'
            ],
            "MasterApprover": [
                '/landing-page', 
                '/masters-interceptor/task-pending', 
                '/mta/master-data-management/control-panel/add', 
                '/mta/master-data-management/control-panel/delete', 
                '/mta/master-data-management/task-pending'
            ],
            'Supplier': [
                '/mta/supply-chain-intelligence-hub/sdr',
                '/mta/supply-chain-intelligence-hub/SupplierWiseAllocation',
                '/profile'
                ],
            # "UserManager": [ # ADDED: Missing role. Permissions need to be defined.
            #     # Add relevant permission codes for User Management
            # ]

            # MTO
            'MTO VectorConsultant': self.all_permission_urls,
            'MTO Admin': [
                '/landing-page',
                '/profile',
                '/',
                '/login-audit-report'
            ],
            "BMReportManager": [
                '/mto/procurement/material-coverage-open-sales',
                '/mto/procurement-planning/planning',
                '/mto/production-planning-and-scheduling/due-date-quotation',
                '/mto/production-planning-and-scheduling/order-rescheduling',
                '/mto/production-planning-scheduling/deptwise-bm-report',
                '/mto/production-planning-scheduling/overall-bm-report',
                '/mto/production-planning-scheduling/insight-and-trends/bm-trends',
                '/mto/poogi/insight-and-trends/otif-analysis',
                '/mto/poogi/insight-and-trends/ot-and-if-analysis',
                '/mto/poogi/insight-and-trends/lead-time'
            ],
            "Salesperson": [
                '/mto/production-planning-scheduling/enquiry-response',
                '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart'
            ],
            "Master Scheduler": [
                '/mto/production-planning-and-scheduling/due-date-quotation',
                '/mto/production-planning-and-scheduling/order-rescheduling'
            ],
            "Production Planner": [
                '/mto/procurement/material-coverage-open-sales',
                '/mto/procurement-planning/planning',
                '/mto/procurement/material-requirement',
                '/mto/procurement/insights-and-trends/day-wise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-buffer-trends',
                '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers',
                '/mto/production-planning-scheduling/full-kit-assignment',
                '/mto/production-planning-scheduling/dynamic-release-mangement',
                '/mto/production-planning-scheduling/insight-and-trends/bm-trends',
                '/mto/production-planning-scheduling/insights-and-trends/fol-summary',
                '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits',
                '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
                '/mto/production-planning-scheduling/insight-and-trends/order-at-risk',
                '/mto/production-planning-scheduling/insight-and-trends/order-balance',
                '/mto/planning/simulative-fullkit'                            
            ],
            "Dept Manager": [
                "/mto/production-planning-scheduling/deptwise-bm-report",
            ],
            "Dept Manager - View Only": [
                "/mto/production-planning-scheduling/deptwise-bm-report",
            ],
            "Production Manager - View Only": [ 
                '/mto/production-planning-scheduling/overall-bm-report',
                '/mto/production-planning-scheduling/insight-and-trends/bm-trends',
                '/mto/production-planning-scheduling/insights-and-trends/fol-summary',
                '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits',
                '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
                '/mto/production-planning-scheduling/insight-and-trends/order-balance',
                '/mto/production-planning-scheduling/insight-and-trends/order-at-risk',
                '/mto/manufacturing-intelligence-hub/future-order-load-chart',
                '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart'           
            ],
            "Production Manager": [
                '/mto/production-planning-scheduling/overall-bm-report',
                '/mto/production-planning-scheduling/insights-and-trends/fol-summary',
                '/mto/production-planning-scheduling/insights-and-trends/elapsed-time',
                '/mto/production-planning-scheduling/insight-and-trends/order-at-risk',
                '/mto/production-planning-scheduling/insight-and-trends/order-balance',
                '/mto/manufacturing-intelligence-hub/future-order-load-chart',
                '/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart'
            ],
            "Procurement Manager": [
                '/mto/procurement/material-coverage-open-sales',
                '/mto/procurement-planning/planning',
                '/mto/procurement/material-requirement',
                '/mto/procurement/insights-and-trends/day-wise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-buffer-trends',
                '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers',
                '/mto/planning/simulative-fullkit'           
            ],
            "Procurement Manager - View Only": [
                '/mto/procurement/material-coverage-open-sales',
                '/mto/procurement-planning/planning',
                '/mto/procurement/material-requirement',
                '/mto/procurement/insights-and-trends/day-wise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage',
                '/mto/procurement/insights-and-trends/rmpm-buffer-trends',
                '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers',
                '/mto/planning/simulative-fullkit'          
            ],
            "POOGI Manager": [
                '/mto/poogi/insight-and-trends/resource-utilization-wip-profile',
                '/mto/poogi/insight-and-trends/otif-analysis',
                '/mto/poogi/insight-and-trends/ot-and-if-analysis',
                '/mto/poogi/insight-and-trends/lead-time',
                '/mto/poogi/insight-and-trends/trend-of-failure-reason',
                '/mto/poogi/insight-and-trends/top-failure-reasons',
                '/mto/poogi/reasons-for-delayed-orders'        
            ],
            "Plant Head": [
                '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends',
                '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis',
                '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis',
                '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time',
                '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time',
                '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk',
                '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance',
                '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary',
                '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit',
                '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage',
                '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage',
                '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier',
                '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend',
                '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons',
                '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons',
                '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile' 
            ],
            "Master Data Updater": [
                '/masters-interceptor/control-panel',
                '/masters-interceptor/saved-drafts',
                # '/masters-interceptor/task-pending',
                '/masters-interceptor/task-status',
                '/mto/master-data-management/control-panel',
                '/mto/master-data-management/control-panel/add',
                '/mto/master-data-management/control-panel/view-modify',
                '/mto/master-data-management/saved-drafts',
                # '/mto/master-data-management/task-pending',
                '/mto/master-data-management/task-status'             
            ],
            "Master Data Approver": [
                '/masters-interceptor/control-panel',
                '/masters-interceptor/saved-drafts',
                '/masters-interceptor/task-pending',
                '/masters-interceptor/task-status',
                '/mto/master-data-management/control-panel',
                '/mto/master-data-management/control-panel/add',
                '/mto/master-data-management/control-panel/view-modify',
                '/mto/master-data-management/saved-drafts',
                '/mto/master-data-management/task-pending',
                '/mto/master-data-management/task-status'         
            ],
            "SchedulerManager":[
                '/mto/production/scheduling',
            ],
            "SchedulerManagerViewer":[
                '/mto/production/scheduling',
            ]
        }

        # Fetch all required data from the DB 
        # Create a mapping of role_code -> role_id for quick lookups.
        roles_map = {role.name: role.id for role in Roles.objects.all()}
        logger.info(f"  Fetched {len(roles_map)} roles from the database.")

        # Create a mapping of permission_code -> permission_id for quick lookups.
        permissions_map = {perm.url: perm.id for perm in Permission.objects.all()}
        logger.info(f"  Fetched {len(permissions_map)} permissions from the database.")
        
        # Get the through model for the many-to-many relationship.
        RolePermissionLink = Permission.role_id.through
        
        # Fetch all existing role-permission links as a set of (role_id, permission_id) tuples for fast lookups.
        existing_links = set(RolePermissionLink.objects.values_list('roles_id', 'permission_id'))
        logger.info(f"  Found {len(existing_links)} existing role-permission links.")

        # Determine which role-permission links need to be created in memory.
        links_to_create = []
        for role_name, permission_urls in role_permission_map.items():
            role_id = roles_map.get(role_name)
            if not role_id:
                self.stdout.write(self.style.ERROR(f"  Role with name '{role_name}' not found in the database. Skipping its permissions."))
                error_count += len(permission_urls)
                continue

            for perm_url in permission_urls:
                permission_id = permissions_map.get(perm_url)
                if not permission_id:
                    self.stdout.write(self.style.WARNING(f"  Permission with url '{perm_url}' not found for role '{role_name}'. Skipping."))
                    error_count += 1
                    continue
                
                # If the link does not already exist, prepare it for creation.
                if (role_id, permission_id) not in existing_links:
                    links_to_create.append(
                        RolePermissionLink(roles_id=role_id, permission_id=permission_id)
                    )
                else:
                    skipped_count += 1

        # Create all the new links in a SINGLE bulk query.
        if links_to_create:
            created_objects = RolePermissionLink.objects.bulk_create(links_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new role-permission links.")
        else:
            logger.info("  No new role-permission links to create.")
        
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f"Role-Permissions: {created_count} created, {skipped_count} skipped, {error_count} errors"
            )
        )

    def seed_user_roles(self):
        """Seed the User-Role mappings based on defined static assignments (USER_ROLE)"""
        self.stdout.write("Seeding User-Role mappings from static config...")

        created_count = 0
        skipped_count = 0
        error_count = 0

        user_role_map = {
            # user_name: [role_code, ...]
            # SuperAdmin owns all recovered URLs/features. Admin and
            # VectorConsultant are also required because the frontend's
            # application catalog is projected from these operational roles.
            'admin': ['SUPERADMIN', 'ADMIN', 'VectorConsultant']
        }
        
        # Fetch all required data from the DB.
        target_user_names = user_role_map.keys()
        users_map = {user.name: user.id for user in User.objects.filter(name__in=target_user_names)}
        logger.info(f"  Fetched {len(users_map)} matching users from the database.")

        # Create a mapping of role_code -> role_id for quick lookups.
        roles_map = {role.code: role.id for role in Roles.objects.all()}
        logger.info(f"  Fetched {len(roles_map)} roles from the database.")
        
        # Get the through model for the many-to-many relationship.
        UserRoleLink = Roles.user_id.through
        
        # Fetch all existing user-role links as a set of (user_id, role_id) tuples for fast lookups.
        existing_links = set(UserRoleLink.objects.values_list('user_id', 'roles_id'))
        logger.info(f"  Found {len(existing_links)} existing user-role links.")

        # Determine which user-role links need to be created in memory.
        links_to_create = []
        for user_name, role_codes in user_role_map.items():
            user_id = users_map.get(user_name)
            if not user_id:
                self.stdout.write(self.style.ERROR(f"  User '{user_name}' does not exist in the database. Skipping their roles."))
                error_count += len(role_codes)
                continue

            for role_code in role_codes:
                role_id = roles_map.get(role_code)
                if not role_id:
                    self.stdout.write(self.style.WARNING(f"  Role with code '{role_code}' not found for user '{user_name}'. Skipping."))
                    error_count += 1
                    continue
                
                # If the link does not already exist, prepare it for creation.
                if (user_id, role_id) not in existing_links:
                    links_to_create.append(
                        UserRoleLink(user_id=user_id, roles_id=role_id)
                    )
                else:
                    skipped_count += 1

        # Create all the new links in a SINGLE bulk query.
        if links_to_create:
            created_objects = UserRoleLink.objects.bulk_create(links_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new user-role links.")
        else:
            logger.info("  No new user-role links to create.")

        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f"User-Roles: {created_count} created, {skipped_count} skipped, {error_count} errors"
            )
        )

    def seed_ads_config(self):
        """ seeding the ADS_CONFIG model witn data  the two urls inside the config  
        will be constant, and will hold the azure directory services credentials for each client
        """   
        logger.info("Seeding ADS_config data....")
        created_count=0
        skipped_count=0
        config=[
            {'flag': 'client_name','value' :None, 'description': 'client/site name'},
            {'flag': 'ads_token_url','value' :'https://login.microsoftonline.com/{tenant_id} /oauth2/v2.0/token/', 'description': 'Retrieve the Bearer token using the Tenant ID, which is required to access the user_account_status'},
            {'flag' :'user_account_status_url', 'value': 'https://graph.microsoft.com/v1.0/users/{email}?$select=id,displayName,mail,accountEnabled', 'description': 'used to Fetch response from ADS whether user is an active user or is deactivated'},
            {'flag':'tenant_id','value':None,'description':'ADS Tenant Id for site users'},
            {'flag':'client_id','value':None,'description':'ADS Client Id for site users (also called as application id)'},
            {'flag':'client_secret','value':None,'description':'ADS Secret value key for site users(also called as value)'},
            {'flag': 'ads_cred_exp_date', 'value': None,'description': 'tenant id, client id & secret key expiration time store In yyyy-mm-dd format(request new cred from client after expiration)'},
            {'flag': 'verify_domain', 'value':None,'description': 'only these domains will be verified by ADS rest will be allowed without verification(for multiple domains, separate the domains via commas)'},
            {'flag': 'primary_email_notify', 'value': False ,'description':'primary email sent to support/client for requesting of updated credentials 10 days before ads_cred_exp_time (after updating creds, change to False)'},
            {'flag': 'secondary_email_notify', 'value': False ,'description': 'secondary email sent to support/client for requesting of updated credentials 5 days before ads_cred_exp_time (after updating creds, change to False)'},
            {'flag': 'bearer_token', 'value': None, 'description':'bearer token used as auth key for ads account details'},
            {'flag': 'bearer_token_exp_time', 'value': None, 'description':'bearer token expiry time after which token will be invalid stored in seconds'},
            {'flag': 'last_bearer_token_access_time', 'value': None, 'description': 'time stamp to keep the last login details'},

            
        ]
        current_config=set(ADS_Config.objects.values_list('flag',flat=True))
        logger.info(f"  {len(current_config)} are already the existing entries in the database.")
        config_to_create=[]

        for data in config:
            lookup_key=data['flag']
            if lookup_key not in current_config:
                config_to_create.append(
                    ADS_Config(
                        flag=data['flag'],
                        value=data['value'],
                        description = data['description'],
                    )
                )
            else:
                skipped_count+=1

        #bulk entry to the new config in ads model
        if config_to_create:
            new_created=ADS_Config.objects.bulk_create(config_to_create)
            created_count=len(new_created)
            logger.info(f"  Bulk created {created_count} new config.")
        else:
            logger.info("  No new config to create.")

        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Config: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )


    
    def seed_alert_email_cc_details(self):
        """ seed the AlertEmailCCDetails data"""
        logger.info("Seeding Userservice config data...")
        created_count = 0
        skipped_count = 0
        config = [
            {'event_key': 'active_dir_expire', 'email_to' : None, 'cc':None,'event_type':'alert','subject':'Active directory credentials are expriring soon!','is_active':True}
        ]
        existing_config = set(AlertEmailCCDetails.objects.values_list('event_key', flat=True))
        logger.info(f"  Found {len(existing_config)} existing entries in the database.")
        # Determine which applications need to be created.
        config_to_create = []
        for data in config:
            lookup_key = (data['event_key'])
            if lookup_key not in existing_config:
                # Add a new ApplicationMaster instance to our list for bulk creation.
                config_to_create.append(
                    AlertEmailCCDetails(
                        event_key=data['event_key'],
                        email_to=data['email_to'],
                        cc = data['cc'],
                        event_type=data['event_type'],
                        subject=data['subject'],
                        is_active=data['is_active']

                    )
                )
            else:
                skipped_count += 1

        # Create all the new applications in a SINGLE bulk query.
        if config_to_create:
            created_objects = AlertEmailCCDetails.objects.bulk_create(config_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new config.")
        else:
            logger.info("  No new config to create.")
    
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Config: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )
    def seed_userservice_config(self):
        """Seed the Userservice config data - only update when values actually change"""
        logger.info("Seeding Userservice config data...")
        
        created_count = 0
        skipped_count = 0
        
        config = [
            {'flag': 'CLIENT_LOGO', 'value' : None, 'description':None,'isvisible':True},
            {'flag': 'CLIENT_NAME', 'value' : None, 'description':None,'isvisible':True},
            {'flag': 'NUMBER_FORMAT', 'value' : None, 'description':None,'isvisible':True},
            {'flag': 'IDLE_TIMEOUT', 'value': '900000', 'description': 'IDLE_TIMEOUT should be in miliseconds','isvisible':False},
             {'flag':'Is_ADS_ACTIVE','value':False,'description':'To check if user data needs to be verified with ADS for inactivity (Keep values as  False/True only)','isvisible':False},
            {'flag':'UserDomain','value':None,'description':'allow user login requests from the mentioned domain only','isvisible':False},
        ]
        
        # Fetch all existing application IDs from the DB in a SINGLE query.
        existing_config = set(UserserviceConfig.objects.values_list('flag', flat=True))
        logger.info(f"  Found {len(existing_config)} existing entries in the database.")

        # Determine which applications need to be created.
        config_to_create = []
        for data in config:
            lookup_key = (data['flag'])
            if lookup_key not in existing_config:
                # Add a new ApplicationMaster instance to our list for bulk creation.
                config_to_create.append(
                    UserserviceConfig(
                        flag=data['flag'],
                        value=data['value'],
                        description = data['description'],
                        isvisible=data['isvisible']
                    )
                )
            else:
                skipped_count += 1
                
        # Create all the new applications in a SINGLE bulk query.
        if config_to_create:
            created_objects = UserserviceConfig.objects.bulk_create(config_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new config.")
        else:
            logger.info("  No new config to create.")
    
        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Config: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )
