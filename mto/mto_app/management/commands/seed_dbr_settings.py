import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from mto_app.models import DBRSettings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds MasterMapper and MDMConfiguration tables with full sync detection.'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                logger.info(
                    self.style.SUCCESS('Starting DBR Settings seeding...')
                )

                if self.check_seeding_status():
                    return

                self.stdout.write(self.style.SUCCESS("Starting seeding process..."))

                self.seed_dbr_settings()

                self.stdout.write(self.style.SUCCESS("Seeding process for DBR Settings completed."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))

    def check_seeding_status(self):
        """Check if seeding has already been performed"""
        # Count existing entries
        total = sum([
            DBRSettings.objects.count()
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

    def seed_dbr_settings(self):
        """Seed the DBRSettings table - only update when values actually change"""
        logger.info("Seeding DBRSettings...")

        data = [
            {"flag": "IsDataPermissionEnabled", "value": "0", "description": "1 if the user wise data permission is enabled in the system else 0"},
            {"flag": "BOM_Allocation_In_Decimal", "value": "0", "description": "BOM : 0 for round allocation and 1 for Decimal"},
            {"flag": "BOM_Alternate_Code_Allocation", "value": "0", "description": "0: Do not consider alternate code for stock allocation. 1: Consider alternate code for stock allocation."},
            {"flag": "BOM_Batchsize_Component_Allocation", "value": "0", "description": "BOM : 0 for Consider batchsize of ordered item. and 1 for Consider batchsize of each bom level"},
            {"flag": "BOM_FG_Allocation_With_Parent_Batchsize", "value": "0", "description": "BOM: 0 for False and 1 for True"},
            {"flag": "BOMActive", "value": "0", "description": "If this flag is true then VFlowBOM.exe will execute"},
            {"flag": "BufferFactor", "value": "0.5", "description": "Buffer Factor value"},
            {"flag": "CanFinishFromUI", "value": "0", "description": "0- Finish Button Invisible on BM Report, 1- Finish Button is Visible on BM Report"},
            {"flag": "ConsiderSLTInDDQ", "value": "0", "description": "1 - Consider SLT in Due date calculation, 0 - Do not consider SLT in Due date calculation"},
            {"flag": "DeliveryTolerance", "value": "3", "description": "Used in getOTIFAnalysisData API"},
            {"flag": "DynamicReleaseControlFilters", "value": "0", "description": "1-PLANT, 2-SKUCode , 3-Category, Only CCR - 0"},
            {"flag": "FOLHorizon", "value": "180", "description": "FOL Horizon Value"},
            {"flag": "full kit threshold", "value": "1", "description": "NULL"},   #check
            {"flag": "FutureSpikeCapacityAttr", "value": "0", "description": "Capacity Attribute for Future Attribute Spike Report"},
            {"flag": "FutureSpikeCategoryAttr", "value": "0", "description": "Category Attribute for Future Attribute Spike Report"},
            {"flag": "GenerateDownloadableInputData", "value": "0", "description": "1 - Generate Downloadable InputData, 0 - Not to Generate Downloadable InputData"},
            {"flag": "IsCapacityInUnits", "value": "0", "description": "1 - CCR Capacity in Units/Day, 0 - Working Hours/Day"},
            {"flag": "IsDDQActive", "value": "0", "description": "Used in DDQ Page"},
            {"flag": "MaxBufferSize", "value": "200", "description": "Settings Buffer UI - This is the maximum buffer size allowed for both Production and Procurement Buffers"},
            {"flag": "MfgTolerance", "value": "5", "description": "Used in getOTIFAnalysisData API"},
            {"flag": "MinBufferSize", "value": "2", "description": "Settings Buffer UI - This is the minimum buffer size allowed for both Production and Procurement Buffers"},
            {"flag": "OrderType", "value": "0", "description": "0- OneOrderOneLine 1- OneOrderMultipleLine Used on Order Rescheduling UI"},
            {"flag": "PlannedLoadGraphHorizon", "value": "15", "description": "Value is in Weeks - DaywisePlannedLoadGraph(DueDate and ReleaseDate) and FutureOrderPlannedLoadGraph"},
            {"flag": "PlotWithinFOLHorizonOnly", "value": "0", "description": "1- Plot orders within FOL horizon only, 0- Plot orders outside FOL horizon"},
            {"flag": "ReasonIsEmergentIfImpactedOrdersIncreasedBy", "value": "15", "description": "NULL"},
            {"flag": "SchedulingHorizon", "value": "180", "description": "Scheduling Horizon Value"},
            {"flag": "ShowCategoryFilter", "value": "0", "description": "0-do not show Category Filter 1-Show Category Filter - CCRAssignment page"},
            {"flag": "ShowMTABlueOrders", "value": "0", "description": "1-ShowMTABlueOrders, 0-HideMTABlueOrders"},
            {"flag": "TopFailureReasons", "value": "10", "description": "NULL"},
            {"flag": "UnitOfMeasurement", "value": "m", "description": "Used in getOTIFAnalysisData API"},
            {"flag": "WIPThresholdLimit", "value": "10", "description": "NULL"},
            {"flag": "BOM_Component_Allocation_Type", "value": "0", "description": "BOM : 0 for FullOrderwise and 1 for Batchwise. 'BOM Batchsize Component Allocation' flag is check in case of 1"},
            {"flag": "BOM_Order_Allocation_For_Transit_Buffer", "value": "0", "description": "BOM : 0 for FullOrderwise and 1 for Batchwise(Order qty should be in multiple of batchsize) and 2 for Partial and  3 for Batchwise(Order qty need not to be in multiple of batchsize)"},
            {"flag": "BOM_Fg_Sfg_Conversion_Required", "value": "0", "description": "Reverse rationing"},
            {"flag": "SystemType", "value": "0", "description": "0-OnlyMTO, 1-OnlyMTA, 2-MTO_MTA"},
            {"flag": "CloseOrdersFromUI", "value": "False", "description": "to enable order closing for ui-1"},
            {"flag": "SiteName", "value": "", "description": "Site Name is used in DDQ Controller"},
            {"flag": "MaterialSOAllData", "value": "0", "description": "1- button enable, 0- button disable"},
            {"flag": "simulationEnable", "value": "disabled", "description": "enabled-simulationOn disabled-simulationOff"},
            {"flag": "OrderCloseEnable", "value": "0", "description": "0-orderClosingOFF 1-orderClosingOn"},
            {"flag": "IsMTACapacityReserved", "value": "0", "description": "0- Consider MTA and MTO load on CCR, 1- Consider only MTO load on CCR"},
            {"flag": "ConsiderCRDDInDDQ", "value": "0", "description": "1 - consider CRDD in DDQ Calculation 0 - do not consider CRDD in DDQ Calculation"},
            {"flag": "AutoRelease", "value": "0", "description": "0-Manual Order Released 1- Automatic Order Release.Used to release orders after scheduling and rescheduling"},
            {"flag": "IsDDQFromUI","value": "0", "description": "0-DDQ is not from UI  1-DDQ is from UI" },
            {"flag": "BOM_Allocation_Type", "value": "0", "description": "0 : Soft allocation and 1: Hard Allocation"},
            {"flag": "UnresolvedReasonThreshold", "value": "0", "description": ""},
            {"flag": "EmergentReasonThreshold", "value": "0", "description": ""},
            {"flag" :"OLOperator", "value": "0", "description": "0 - Multiply , 1 - Divide" },
            {"flag" :"showAllItems", "value": "0", "description": "0 - show only items that have related orders on the procurement planning page; 1 - show all items regardless of whether they have orders" }
        ]

        created_count = 0
        skipped_count = 0

        # FETCH KEYS OF EXISTING RECORDS FOR EFFICIENT LOOKUPS 
        existing_flags = set(DBRSettings.objects.values_list('flag', flat=True))
        self.stdout.write(f"  Found {len(existing_flags)} existing DBRSettings keys.")

        # PREPARE NEW RECORDS IN-MEMORY ---
        settings_to_create = []
        for item in data:
            # If the flag already exists in the database, we skip it.
            if item['flag'] in existing_flags:
                skipped_count += 1
                continue
            # Entry does not exist, so we prepare it for creation 
            settings_to_create.append(DBRSettings(**item))

        # PERFORM A SINGLE BULK CREATE OPERATION 
        if settings_to_create:
            # Create all the new records in one database query.
            created_objects = DBRSettings.objects.bulk_create(settings_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new DBRSettings.")
        else:
            self.stdout.write("  No new DBRSettings to create.")

        # SHOW SUMMARY 
        self.stdout.write(
            self.style.SUCCESS(
                f'DBRSettings: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )
