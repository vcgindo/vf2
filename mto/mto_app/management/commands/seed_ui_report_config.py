import logging
from django.core.management.base import BaseCommand
from mto_app.models import UIReportConfigurations, HeaderGroupingMaster
from django.db import transaction

# Correctly get the logger for this module
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds report configurations and color settings for UI reports'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self.stdout.write(
                    self.style.SUCCESS('Starting UI Report Configuration seeding...')
                )
                # Check if seeding has already been performed
                if self.check_seeding_status():
                    return

                report_configs_data = [
                    # DueDateQuotation
                    {'report_name': 'DueDateQuotation', 'col_code': 'OrderID', 'col_position': 1, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'LineItem', 'col_position': 2, 'header': 'Line Item', 'visible': False, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'CRDD', 'col_position': 3, 'header': 'CRDD', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'cedd', 'header_grouping_id': 5, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'ItemName', 'col_position': 4, 'header': 'Item Name', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'in', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'OrderQty', 'col_position': 5, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'Plant', 'col_position': 6, 'header': 'Plant', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'Department', 'col_position': 7, 'header': 'Department', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'dn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'Customer', 'col_position': 8, 'header': 'Customer', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'ProductionBuffer', 'col_position': 9, 'header': 'Production Buffer', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'prodc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'ProcurementBuffer', 'col_position': 10, 'header': 'Procurement Buffer', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'procc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'Route', 'col_position': 11, 'header': 'Route', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'EstimatedDD', 'col_position': 12, 'header': 'Estimated DD', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cdd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'DueDate', 'col_position': 13, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'OrderKey', 'col_position': 14, 'header': 'Order Key', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ok', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DueDateQuotation', 'col_code': 'PlannedReleaseDate', 'col_position': 15, 'header': 'Planned release date', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'plrd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # Material Coverage for Open Sales Order Page (Procurement)
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderLineItem', 'col_position': 2, 'header': 'Order Line Item', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oli', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderNo', 'col_position': 3, 'header': 'Order No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderQty', 'col_position': 4, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'BatchSize', 'col_position': 5, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'FullKitAvail', 'col_position': 6, 'header': 'Full Kit Avail', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fka', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'CustName', 'col_position': 7, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'CustCode', 'col_position': 8, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'Item Code', 'col_position': 9, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fgc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'ItemDescp', 'col_position': 10, 'header': 'Item Descp', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fgd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderReceiptDate', 'col_position': 11, 'header': 'Order Receipt Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderDueDate', 'col_position': 12, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder', 'col_code': 'OrderReleaseDate', 'col_position': 13, 'header': 'Order Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ordRD', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # Material Requirement (Procurement)
                    {'report_name': 'MaterialRequirement', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'MaterialRequirement', 'col_code': 'RMCode', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'RMDescription', 'col_position': 3, 'header': 'RM Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'NoofOrderImpacted', 'col_position': 4, 'header': 'No of Orders Impacted', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'nooi', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'RMRequired', 'col_position': 5, 'header': 'RM Required', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmr', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'rmh', 'col_position': 6, 'header': 'RM In Stock', 'visible': True, 'cell_alignment': 'CENTER', 'value': None, 'short_col_code': 'rmh', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'rmt', 'col_position': 7, 'header': 'RM In Transit', 'visible': True, 'cell_alignment': 'CENTER', 'value': None, 'short_col_code': 'rmt', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'ppo', 'col_position': 8, 'header': 'Pending PO', 'visible': True, 'cell_alignment': 'CENTER', 'value': None, 'short_col_code': 'ppo', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialRequirement', 'col_code': 'net_r', 'col_position': 9, 'header': 'Net Requirement', 'visible': True, 'cell_alignment': 'CENTER', 'value': None, 'short_col_code': 'net_r', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Enquiry Response (Production Planning & Scheduling)
                    {'report_name': 'EnquiryResponse', 'col_code': 'Plant', 'col_position': 1, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'EnquiryResponse', 'col_code': 'Department', 'col_position': 2, 'header': 'Department', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dpnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'EnquiryResponse', 'col_code': 'CCRGroup', 'col_position': 3, 'header': 'CCR Group', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'gnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'EnquiryResponse', 'col_code': 'CCRName', 'col_position': 4, 'header': 'CCR Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'EnquiryResponse', 'col_code': 'FOL(inDays)', 'col_position': 5, 'header': 'FOL (in Days)', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fol', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Order Rescheduling (Production Planning & Scheduling)
                    {'report_name': 'OrderRescheduling', 'col_code': 'OrderID', 'col_position': 1, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'LineItem', 'col_position': 2, 'header': 'Line Item', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'ProcurementBuffer', 'col_position': 3, 'header': 'Procurement Buffer', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'PcSz', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'ProductionBuffer', 'col_position': 4, 'header': 'Production Buffer', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'PdSz', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'Route', 'col_position': 5, 'header': 'Route', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'DueDate', 'col_position': 6, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'OrderRescheduling', 'col_code': 'Reason', 'col_position': 7, 'header': 'Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rs', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Procurement Planning Simulation
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'Colorpriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'OrderLineItem', 'col_position': 2, 'header': 'Order Line Item', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oli', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'OrderNo', 'col_position': 3, 'header': 'Order No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'ItemCode', 'col_position': 4, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'item', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'Itemdescp', 'col_position': 5, 'header': 'Item Descp', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'Orderqty', 'col_position': 6, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'BatchSize', 'col_position': 7, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'KitsBeforeSM', 'col_position': 8, 'header': 'Kits Before SM', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'kbs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'FullKitsAvail', 'col_position': 9, 'header': 'Full Kits Avail', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fka', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'CustName', 'col_position': 10, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'CustCode', 'col_position': 11, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'OrderReceiptDate', 'col_position': 12, 'header': 'Order Receipt Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'od', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'OrderDueDate', 'col_position': 13, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ProcurementPlanningSimulation', 'col_code': 'OrderReleaseDate', 'col_position': 14, 'header': 'Order Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # Procurement Planning Available (Procurement)
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'RMCode', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'RMDescription', 'col_position': 3, 'header': 'RM Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'NoOfOrderImapcted', 'col_position': 4, 'header': 'No Of Order Imapcted', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'nooi', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'TotalReq', 'col_position': 5, 'header': 'Total Req', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'req', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'UOM', 'col_position': 6, 'header': 'UOM', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'uom', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'StockOn-Hand', 'col_position': 7, 'header': 'Allocated Stock On-Hand', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'soh', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'StockInQC', 'col_position': 8, 'header': 'Allocated Stock In QC', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'siqc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'StockInTransit', 'col_position': 9, 'header': 'Allocated Stock In Transit', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'sit', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'Gap', 'col_position': 10, 'header': 'Gap', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'gap', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'PendingPO', 'col_position': 11, 'header': 'Pending PO', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ppo', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'ExpAdd.StockToday', 'col_position': 12, 'header': 'Exp Add. Stock Today', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'eas', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningAvailable', 'col_code': 'TotalStockforSimulation', 'col_position': 13, 'header': 'Total Stock for Simulation', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tsfs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Procurement Planning Shortage (Procurement)
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'RMCode', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'RMDescription', 'col_position': 3, 'header': 'RM Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'NoOfOrderImapcted', 'col_position': 4, 'header': 'No Of Order Imapcted', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'nooi', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'TotalReq', 'col_position': 5, 'header': 'Total Req', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'req', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'UOM', 'col_position': 6, 'header': 'UOM', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'uom', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'StockOn-Hand', 'col_position': 7, 'header': 'Allocated Stock On-Hand', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'soh', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'StockInQC', 'col_position': 8, 'header': 'Allocated Stock In QC', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'siqc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'StockInTransit', 'col_position': 9, 'header': 'Allocated Stock In Transit', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'sit', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'Gap', 'col_position': 10, 'header': 'Gap', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'gap', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'PendingPO', 'col_position': 11, 'header': 'Pending PO', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ppo', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'ExpAdd.StockToday', 'col_position': 12, 'header': 'Exp Add. Stock Today', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'eas', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcurementPlanningShortage', 'col_code': 'TotalStockforSimulation', 'col_position': 13, 'header': 'Total Stock for Simulation', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tsfs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # RM/PM OrderWise Coverage (Procurement)
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'Plant', 'col_position': 2, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pnm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'OrderID', 'col_position': 3, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'OrderType', 'col_position': 4, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': None, 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'LineItemID', 'col_position': 5, 'header': 'Line ID', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'ItemCode', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'ItemDescription', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'DueDate', 'col_position': 8, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'ReleaseDate', 'col_position': 9, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'OrderQauntity', 'col_position': 10, 'header': 'Order Qauntity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'BatchSize', 'col_position': 11, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'FullKitAvailable', 'col_position': 12, 'header': 'FullKit Available', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fk', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'RMPMCoverage', 'col_position': 13, 'header': 'RMPM Coverage', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmpm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'CustomerCode', 'col_position': 14, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'RMPMOrderWiseCoverage', 'col_code': 'CustomerName', 'col_position': 15, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Overall BM Report (Production Planning & Scheduling)
                    {'report_name': 'BMReport', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': True},
                    {'report_name': 'BMReport', 'col_code': 'DeptAgeing', 'col_position': 2, 'header': 'Department Ageing', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'da', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'Order Type', 'col_position': 3, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'OrderID', 'col_position': 4, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'LineItem', 'col_position': 5, 'header': 'Line Item', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'ItemCode', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'ItemDescription', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'OrderQuantity', 'col_position': 8, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'WIPOnHand', 'col_position': 9, 'header': 'WIP On Hand', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'woh', 'header_grouping_id': 'Order Attributes', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'Mfg.Balance', 'col_position': 10, 'header': 'Mfg. Balance', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mfg', 'header_grouping_id': 'Order Attributes', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'DueDate', 'col_position': 11, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'TrailingDepartment', 'col_position': 12, 'header': 'Trailing Department', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tdept', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'CRDD', 'col_position': 13, 'header': 'CRDD', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'crdd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'CCRName', 'col_position': 14, 'header': 'CCR Name ', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ccr', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'CustomerName', 'col_position': 15, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    # {'report_name': 'BMReport', 'col_code': 'Customer', 'col_position': 8, 'header': 'Customer', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'ReleaseDate', 'col_position': 16, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    # {'report_name': 'BMReport', 'col_code': 'CustCode', 'col_position': 28, 'header': 'Cust Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'Cust_Cd', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False}, 
                    {'report_name': 'BMReport', 'col_code': 'ActualReleaseDate', 'col_position': 18, 'header': 'Actual Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ard', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'RemarkHistory', 'col_position': 19, 'header': 'Remarks History', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'Rmrk_Hstry', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'LatestRemark', 'col_position': 20, 'header': 'Latest Remark', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lr', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'ElapsedDays', 'col_position': 18, 'header': 'Elapsed Days', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ed', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'PlantName', 'col_position': 20, 'header': 'Plant Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': 'Order Attributes', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'pending_ccr_qty', 'col_position': 45, 'header': 'Pending CCR Qty', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'pcq', 'header_grouping_id': 'Order Attributes', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BMReport', 'col_code': 'PlantCode', 'col_position': 10, 'header': 'Plant Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plc', 'header_grouping_id': 'Order Attributes', 'data_type': 'string','is_color': False},

                    # Day Wise Coverage (Manufacturing Intelligence Hub)
                    {'report_name': 'DayWiseCoverage', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'clr', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'OrderNumber', 'col_position': 2, 'header': 'Order Number', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'OrderReceiveDate', 'col_position': 3, 'header': 'Order Receive Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'OrderDueDate', 'col_position': 4, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'OrderQuantity', 'col_position': 5, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'CustomerName', 'col_position': 6, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'CustomerCode', 'col_position': 7, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'ItemCode', 'col_position': 8, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'ItemDescp', 'col_position': 9, 'header': 'Item Descp', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverage', 'col_code': 'Status', 'col_position': 10, 'header': 'Status', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 's', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Full Kit Assignment (Production Planning & Scheduling)
                    {'report_name': 'FullKitAssignment', 'col_code': 'Tags', 'col_position': 1, 'header': 'Tags', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 't', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'ColorPriority', 'col_position': 2, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'FullKitAssignment', 'col_code': 'Route', 'col_position': 3, 'header': 'Route', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'OrderNo', 'col_position': 4, 'header': 'Order No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'OrderQty', 'col_position': 5, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'BatchSize', 'col_position': 6, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'KitsBeforeSM', 'col_position': 7, 'header': 'Kits Before SM', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'kbs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'FullKitsAvailable', 'col_position': 8, 'header': 'Full Kits Available', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fka', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'OrderInFullKitToday', 'col_position': 9, 'header': 'Order In Full Kit Today', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oifkt', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'ItemCode', 'col_position': 10, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'ItemDescription', 'col_position': 11, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'OrderDueDate', 'col_position': 12, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'FullKitAssignment', 'col_code': 'OrderReceiveDate', 'col_position': 13, 'header': 'Order Receive Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # STPL & Full Kits (Production Planning & Scheduling)
                    {'report_name': 'STPLAndFullKits', 'col_code': 'Plant', 'col_position': 1, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'STPLAndFullKits', 'col_code': 'Department', 'col_position': 2, 'header': 'Department', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dept', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'STPLAndFullKits', 'col_code': 'CCRGroup', 'col_position': 3, 'header': 'CCR Group', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cg', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'STPLAndFullKits', 'col_code': 'CCR', 'col_position': 4, 'header': 'CCR', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ccr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'STPLAndFullKits', 'col_code': 'ReleasedWIPInDays', 'col_position': 5, 'header': 'Released WIP In Days', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rwip', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'STPLAndFullKits', 'col_code': 'UnReleasedFullKitsInDays', 'col_position': 6, 'header': 'UnReleased Full Kits In Days', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'un_fk', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Orders At Risk (Manufacturing Intelligence Hub)
                    {'report_name': 'OrdersAtRisk', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'Plant', 'col_position': 2, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'OrderID', 'col_position': 3, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'OrderType', 'col_position': 4, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'otyp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'LineItemID', 'col_position': 5, 'header': 'Line Item ID', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'li_id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'ItemCode', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'itmc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'ItemDescription', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'itmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'OrderQuantity', 'col_position': 8, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'MajorReason', 'col_position': 9, 'header': 'Major Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mjr_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'MinorReason', 'col_position': 10, 'header': 'Minor Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'min_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'CustomerCode', 'col_position': 11, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrdersAtRisk', 'col_code': 'CustomerName', 'col_position': 12, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Order Balance (Manufacturing Intelligence Hub)
                    {'report_name': 'OrderBalance', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'OrderBalance', 'col_code': 'Plant', 'col_position': 2, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'OrderID', 'col_position': 3, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'OrderType', 'col_position': 4, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'otyp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'LineItemID', 'col_position': 5, 'header': 'Line Item ID', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'li_id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'ItemCode', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'itmc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'ItemDescription', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'itmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'OrderQuantity', 'col_position': 8, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'TrailingDepartment', 'col_position': 9, 'header': 'Trailing Department', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tdept', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'QuantityBalanceToManufacture', 'col_position': 10, 'header': 'Quantity Balance To Manufacture', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bal_mfg', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'QuantityBalanceToDispatch', 'col_position': 11, 'header': 'Quantity Balance To Dispatch', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bal_dis', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'CustomerCode', 'col_position': 12, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OrderBalance', 'col_code': 'CustomerName', 'col_position': 13, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # OTIF Analysis (Manufacturing Intelligence Hub)
                    {'report_name': 'OTIFAnalysis', 'col_code': 'Tags', 'col_position': 1, 'header': 'Tags', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tag', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'BPP', 'col_position': 2, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'Plant', 'col_position': 3, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'OrderID', 'col_position': 4, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'OrderType', 'col_position': 5, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'LineItemID', 'col_position': 6, 'header': 'Line Item ID', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'ItemCode', 'col_position': 7, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'ItemDescription', 'col_position': 8, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'OrderQuantity', 'col_position': 9, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'DueDate', 'col_position': 10, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'OrderClosingDate', 'col_position': 11, 'header': 'Order Closing Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cdt', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'ExtendOfDelay', 'col_position': 12, 'header': 'Extend Of Delay (In Days)', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ed', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'ExtendOfShortage', 'col_position': 13, 'header': 'Extend Of Shortage', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'es', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'CustomerCode', 'col_position': 14, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'CustomerName', 'col_position': 15, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'CRDD', 'col_position': 16, 'header': 'CRDD', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'crdd', 'header_grouping_id': 5, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'ReleaseDate', 'col_position': 17, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'MajorReason', 'col_position': 21, 'header': 'Major Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mjr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'OTIFAnalysis', 'col_code': 'MinorReason', 'col_position': 22, 'header': 'Minor Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mnr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Reason For Delayed Orders (POOGI)
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'Plant', 'col_position': 2, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pln', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'OrderId', 'col_position': 3, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'LineItem', 'col_position': 4, 'header': 'Line Item', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'OrderStatus', 'col_position': 5, 'header': 'Order Status', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'os', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'ItemName', 'col_position': 6, 'header': 'Item Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'OrderQty', 'col_position': 7, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'CustomerCode', 'col_position': 8, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'CustomerName', 'col_position': 9, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'AllocatedFG', 'col_position': 10, 'header': 'Alocated FG', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'afg', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'ElapsedDays', 'col_position': 11, 'header': 'Elapsed Days', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ed', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'PlannedReleaseDate', 'col_position': 12, 'header': 'Planned Release Date / Delta', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'prd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'QuotedDueDate', 'col_position': 13, 'header': 'Quoted Due Date / Delta', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'RemarksHistory', 'col_position': 14, 'header': 'Remarks History', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rmrk_hstry', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'MajorReason', 'col_position': 15, 'header': 'Major Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mjr_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ReasonForDelayedOrders', 'col_code': 'MinorReason', 'col_position': 16, 'header': 'Minor Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'min_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Lead Time (Manufacturing Intelligence Hub)
                    {'report_name': 'LeadTime', 'col_code': 'Tag', 'col_position': 1, 'header': 'Tag', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'tg', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'BPP', 'col_position': 2, 'header': 'BPP', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'LeadTime', 'col_code': 'PlantName', 'col_position': 3, 'header': 'Plant Name', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'PlantCode', 'col_position': 4, 'header': 'Plant Code', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'pc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'OrderType', 'col_position': 5, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'OrderID', 'col_position': 5, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'OrderKey', 'col_position': 6, 'header': 'Order Key', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'ok', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'LineId', 'col_position': 7, 'header': 'Line ID', 'visible': False, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'ItemCode', 'col_position': 8, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'ItemDesc', 'col_position': 9, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'OrderQty', 'col_position': 10, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'LeadTime', 'col_position': 11, 'header': 'Lead Time', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'lt', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'DueDate', 'col_position': 12, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'CustomerCode', 'col_position': 13, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'CustomerName', 'col_position': 14, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'Crdd', 'col_position': 15, 'header': 'CRDD', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'crdd', 'header_grouping_id': 5, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'ReleaseDate', 'col_position': 16, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'ar', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'LeadTime', 'col_code': 'Color', 'col_position': 17, 'header': 'Color', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'cl', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'LeadTime', 'col_code': 'ClosureDate', 'col_position': 18, 'header': 'Closure Date', 'visible': True, 'cell_alignment': 'Center', 'value': None, 'short_col_code': 'cd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # Elapsed Time (Production Planning & Scheduling)
                    {'report_name': 'Elapse Time', 'col_code': 'Tags', 'col_position': 1, 'header': 'Tags', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tg', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'BPP', 'col_position': 2, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'Elapse Time', 'col_code': 'PlantID', 'col_position': 3, 'header': 'Plant ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pl', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'PlantName', 'col_position': 4, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'OrderID', 'col_position': 5, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'OrderKey', 'col_position': 6, 'header': 'Order Key', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ok', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'OrderType', 'col_position': 7, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'LineID', 'col_position': 8, 'header': 'Line ID', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'ItemCode', 'col_position': 9, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'ItemDesc', 'col_position': 10, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'OrderQty', 'col_position': 11, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'LeadTime', 'col_position': 13, 'header': 'Lead Time (In Days)', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lt', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'DueDate', 'col_position': 14, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'Customer Code', 'col_position': 15, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'CustomerName', 'col_position': 16, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'Elapse Time', 'col_code': 'Color', 'col_position': 17, 'header': 'Color', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cl', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},

                    # Dynamic Release Management (Production Planning & Scheduling)
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'DropDown', 'col_position': 0, 'header': '', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dpd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'Action', 'col_position': 1, 'header': 'Action', 'visible': True, 'cell_alignment': 'center', 'value': 'NULL ', 'short_col_code': 'act', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'ColorPriority', 'col_position': 2, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'ReleaseDate', 'col_position': 3, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pdd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'OrderNo', 'col_position': 4, 'header': 'Order No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'BatchNo', 'col_position': 5, 'header': 'Batch No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'batch_no', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'SFGCode', 'col_position': 6, 'header': 'SFG Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'itemt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'BatchSize', 'col_position': 9, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'batch_sz', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'Route', 'col_position': 10, 'header': ' Route', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'TargetSODispatchedDate', 'col_position': 11, 'header': 'Target Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cedd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'BPP', 'col_position': 12, 'header': ' BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'ItemDescription', 'col_position': 13, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ide', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DynamicReleaseManagement', 'col_code': 'OrderQuantity', 'col_position': 13, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Simulate Fullkit
                    {'report_name': 'SimulateFullkit', 'col_code': 'ic', 'col_position': 0, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderLineItem', 'col_position': 2, 'header': 'Order Line Item', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oli', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderNumber', 'col_position': 3, 'header': 'Order Number', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'ItemCode', 'col_position': 4, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'item', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'ItemDesc', 'col_position': 5, 'header': 'Item Desc', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderQty', 'col_position': 6, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'BatchSize', 'col_position': 7, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'KitsBeforeSM', 'col_position': 8, 'header': 'Kits Before Simulation', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'kbs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'FullKitsAvail', 'col_position': 9, 'header': 'Full Kits Avail', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fka', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'CustName', 'col_position': 10, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'CustCode', 'col_position': 11, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderReceiptDate', 'col_position': 12, 'header': 'Order Receipt Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'od', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderDueDate', 'col_position': 13, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'SimulateFullkit', 'col_code': 'OrderReleaseDate', 'col_position': 14, 'header': 'Order Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},

                    # Bom Explosion
                    {'report_name': 'BomExplosion', 'col_code': 'ItemName', 'col_position': 1, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'path', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'BomExplosion', 'col_code': 'Requirement', 'col_position': 2, 'header': 'Requirement', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'qty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BomExplosion', 'col_code': 'Allocated Stock', 'col_position': 3, 'header': 'Allocated Stock', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'soh', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BomExplosion', 'col_code': 'Allocated WIP', 'col_position': 4, 'header': 'Allocated WIP', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'wip', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'BomExplosion', 'col_code': 'Gap', 'col_position': 5, 'header': 'Gap', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'gap', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # ProcPlanningReportChildren
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'clr', 'col_position': 1, 'header': '', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'clr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'on', 'col_position': 2, 'header': 'Order No', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'oq', 'col_position': 3, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'cn', 'col_position': 4, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'cc', 'col_position': 5, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'odd', 'col_position': 6, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'ord', 'col_position': 7, 'header': 'Order Release Date', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'pn', 'col_position': 8, 'header': 'Plant Name', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'lid', 'col_position': 9, 'header': 'Line Item', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReportChildren', 'col_code': 'ot', 'col_position': 10, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # MaterialCoverageforOpenSalesOrder_Child
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'clr', 'col_position': 1, 'header': 'FullKit Status', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'clr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'RMCode', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'RMDescp', 'col_position': 3, 'header': 'RM Descp', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'RMReqdQty', 'col_position': 4, 'header': 'RM ReqdQty', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    # {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'RMAvailable', 'col_position': 5, 'header': 'RM Available', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rma', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'RMAllocated', 'col_position': 6, 'header': 'RM Allocated', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmall', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'PurchaseGap', 'col_position': 7, 'header': 'Purchase Gap', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'pg', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesOrder_Child', 'col_code': 'kit', 'col_position': 8, 'header': 'Kit Status', 'visible': False, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'kit', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # ProcPlanningReport_Child
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'clr', 'col_position': 1, 'header': 'FullKit Status', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'clr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'rm', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rm', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'rmd', 'col_position': 3, 'header': 'RM Descp', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'rmqty', 'col_position': 4, 'header': 'RM ReqdQty', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'rma', 'col_position': 5, 'header': 'RM Available', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rma', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'rmall', 'col_position': 6, 'header': 'RM Allocated', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmall', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'pg', 'col_position': 7, 'header': 'Purchase Gap', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'pg', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'kit', 'col_position': 8, 'header': 'Kit Status', 'visible': False, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'kit', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'ProcPlanningReport_Child', 'col_code': 'eas', 'col_position': 9, 'header': 'Exp. Add Stock today', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'eas', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Top Failure Reasons (Manufacturing Intelligence Hub)
                    {'report_name': 'TopFailureReasons', 'col_code': 'tag', 'col_position': 0, 'header': 'Tags', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'tag', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'bpp', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': None, 'data_type': 'number', 'is_color': True},
                    {'report_name': 'TopFailureReasons', 'col_code': 'plnt', 'col_position': 2, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plnt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'oid', 'col_position': 3, 'header': 'Order Id', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'ot', 'col_position': 4, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'lid', 'col_position': 5, 'header': 'Line Item Id', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'ic', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'id', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'oqty', 'col_position': 8, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oqty', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'dd', 'col_position': 9, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'cdt', 'col_position': 10, 'header': 'Order Closing Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cdt', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'mjr_r', 'col_position': 11, 'header': 'Major Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mjr_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'min_r', 'col_position': 12, 'header': 'Minor Reason', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'min_r', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'cc', 'col_position': 13, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'TopFailureReasons', 'col_code': 'cn', 'col_position': 14, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # DeptWiseReport
                    {'report_name': 'DeptWiseReport', 'col_code': 'BPP', 'col_position': 1, 'header': 'BPP', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bpp', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': True},
                    {'report_name': 'DeptWiseReport', 'col_code': 'DeptAgeing', 'col_position': 2, 'header': 'Dept Ageing', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'da', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Order Type', 'col_position': 3, 'header': 'Order Type', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ot', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'OrderID', 'col_position': 4, 'header': 'Order ID', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oid', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'LineItem', 'col_position': 5, 'header': 'Line Item', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lid', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'ItemCode', 'col_position': 6, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ic', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'ItemDescription', 'col_position': 7, 'header': 'Item Description', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'id', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'OrderQuantity', 'col_position': 8, 'header': 'Order Quantity', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': 'Default Attribute', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'WIPOnHand', 'col_position': 9, 'header': 'WIP On Hand', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'woh', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Mfg.Balance', 'col_position': 10, 'header': 'Mfg. Balance', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mfg', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'DueDate', 'col_position': 11, 'header': 'Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'dd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'TrailingDepartment', 'col_position': 12, 'header': 'Trailing Department', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'Trail_Dpt', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'CRDD', 'col_position': 13, 'header': 'CRDD', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'crdd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'CCRName', 'col_position': 14, 'header': 'CCR Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ccr', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'CustomerName', 'col_position': 15, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'ReleaseDate', 'col_position': 16, 'header': 'Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'rd', 'header_grouping_id': 'Default Attribute', 'data_type': 'date', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'ElapsedDays', 'col_position': 18, 'header': 'Elapsed Days', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ed', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'PlantName', 'col_position': 20, 'header': 'Plant Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'pn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'PONo.', 'col_position': 21, 'header': 'PO No.', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'PO_No', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Price', 'col_position': 22, 'header': 'Price', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'Price', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'ItemGroup', 'col_position': 23, 'header': 'Item Group', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': None, 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'CustCode', 'col_position': 28, 'header': 'Cust Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'string','is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Plant', 'col_position': 30, 'header': 'Plant', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'plc', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'pending_ccr_qty', 'col_position': 45, 'header': 'Pending CCR Qty', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'pcq', 'header_grouping_id': 'Order Attributes', 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Remark History', 'col_position': 48, 'header': 'Remark History', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'Rmk_Hstry', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'LatestRemark', 'col_position': 47, 'header': 'Latest Remark', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'lr', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DeptWiseReport', 'col_code': 'Remark', 'col_position': 46, 'header': 'Remark', 'visible': True, 'cell_alignment': 'center', 'value': 'Rmk', 'short_col_code': 'r', 'header_grouping_id': 'Default Attribute', 'data_type': 'string', 'is_color': False},
                
                    #future order load chart UI Report Configuration 
                     {'report_name': 'FutureOrderLoadChart', 'col_code': 'Date', 'col_position': 2, 'header': 'Date', 'visible': True, 'cell_alignment': 'left', 'value': 'date', 'short_col_code': 'date', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                     {'report_name': 'FutureOrderLoadChart', 'col_code': 'PendingCCR', 'col_position': 4, 'header': 'Pending CCR Quantity', 'visible': True, 'cell_alignment': 'left', 'value': 'pend_qty', 'short_col_code': 'load', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                     {'report_name': 'FutureOrderLoadChart', 'col_code': 'CCR', 'col_position': 3, 'header': 'CCR', 'visible': True, 'cell_alignment': 'left', 'value': 'ccr_name', 'short_col_code': 'ccr', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                     {'report_name': 'FutureOrderLoadChart', 'col_code': 'Tag', 'col_position': 1, 'header': 'Tags', 'visible': True, 'cell_alignment': 'left', 'value': 'tag', 'short_col_code': 'tag', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                     {'report_name': 'FutureOrderLoadChart', 'col_code': 'Load', 'col_position': 5, 'header': 'Load in Days', 'visible': True, 'cell_alignment': 'left', 'value': 'load_days', 'short_col_code': 'load', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},

                    # Material Coverage for Open Sales Order Page All Orders (Procurement)
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'ColorPriority', 'col_position': 1, 'header': 'Color Priority', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cp', 'header_grouping_id': None, 'data_type': 'string', 'is_color': True},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderLineItem', 'col_position': 2, 'header': 'Order Line Item', 'visible': False, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oli', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderNo', 'col_position': 3, 'header': 'Order No', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'on', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderQty', 'col_position': 4, 'header': 'Order Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'oq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'BatchSize', 'col_position': 5, 'header': 'Batch Size', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'bs', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'FullKitAvail', 'col_position': 6, 'header': 'Full Kit Avail', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fka', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'CustName', 'col_position': 7, 'header': 'Customer Name', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cn', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'CustCode', 'col_position': 8, 'header': 'Customer Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'cc', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'Item Code', 'col_position': 9, 'header': 'Item Code', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fgc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'ItemDescp', 'col_position': 10, 'header': 'Item Descp', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fgd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderReceiptDate', 'col_position': 11, 'header': 'Order Receipt Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ord', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderDueDate', 'col_position': 12, 'header': 'Order Due Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'odd', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'OrderReleaseDate', 'col_position': 13, 'header': 'Order Release Date', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'ordRD', 'header_grouping_id': None, 'data_type': 'date', 'is_color': False},
                    {'report_name': 'MaterialCoverageforOpenSalesAllOrders', 'col_code': 'fk_status', 'col_position': 14, 'header': 'Status', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'fk_status', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},

                    # Daywise Coverage Orders Children (Procurement)
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'MRQ', 'col_position': 1, 'header': 'Missing RM Qty', 'visible': True, 'cell_alignment': 'center', 'value': None, 'short_col_code': 'mrq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'RMC', 'col_position': 2, 'header': 'RM Code', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rmc', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'RMD', 'col_position': 3, 'header': 'RM Descp', 'visible': True, 'cell_alignment': 'left', 'value': None, 'short_col_code': 'rmd', 'header_grouping_id': None, 'data_type': 'string', 'is_color': False},
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'RMQ', 'col_position': 4, 'header': 'RM ReqQty', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmq', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'RMAV', 'col_position': 5, 'header': 'RM Available', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmav', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                    {'report_name': 'DayWiseCoverageChild', 'col_code': 'RMAL', 'col_position': 6, 'header': 'RM Allocated', 'visible': True, 'cell_alignment': 'right', 'value': None, 'short_col_code': 'rmal', 'header_grouping_id': None, 'data_type': 'number', 'is_color': False},
                ]
                                    
                # Seed main report configuration data
                self.seed_header_grouping_master()
                self.seed_report_configs(report_configs_data)
                
                self.stdout.write(
                    self.style.SUCCESS('UI Report Configuration seeding completed.')
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))

    def check_seeding_status(self):
        """Check if seeding has already been performed"""
        # Count existing configurations
        total = sum([
            UIReportConfigurations.objects.count(),
            HeaderGroupingMaster.objects.count()
        ])
        
        if total > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Seeding appears to have been performed already. '
                    f'Found {total} existing configurations.'
                )
            )
            
            # Ask for confirmation to proceed
            if not self.confirm_proceed():
                self.stdout.write(
                    self.style.SUCCESS('Seeding cancelled by user.')
                )
                return True
        
        return False

    def confirm_proceed(self):
        """Ask user for confirmation to proceed with seeding"""
        try:
            response = input('Do you want to proceed anyway? (y/N): ').lower().strip()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False

    def seed_header_grouping_master(self):
        """Seed the Header Grouping Master data - only update when values actually change"""
        logger.info("Seeding Header Grouping Master...")
        
        created_count = 0
        skipped_count = 0
        
        header_data = [
            {'header_name': "Calculated Attributes"},
            {'header_name': "Order Attributes"},
            {'header_name': "Default Attribute"},
            {'header_name': "Product Attributes"},
            {'header_name': "Customer Attributes"},
        ]

        # FETCH KEYS OF EXISTING RECORDS FOR EFFICIENT LOOKUPS 
        header_master_names = set(HeaderGroupingMaster.objects.values_list('header_name', flat=True))
        self.stdout.write(f"  Found {len(header_master_names)} existing Header Grouping Master keys.")

        headers_to_create = []
        for item in header_data:
            lookup_key = (item['header_name'])
            # If the master_id already exists in the database, we skip this item.
            if lookup_key in header_master_names:
                skipped_count += 1
                continue
            # Entry does not exist, so we prepare it for creation
            headers_to_create.append(HeaderGroupingMaster(**item))
                    
        # PERFORM A SINGLE BULK CREATE OPERATION 
        if headers_to_create:
            # Create all the new records in one database query.
            created_objects = HeaderGroupingMaster.objects.bulk_create(headers_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new Header Grouping Masters.")
        else:
            self.stdout.write("  No new Header Grouping Masters to create.")
            
        # SHOW SUMMARY 
        self.stdout.write(
            self.style.SUCCESS(
                f'Header Grouping Masters: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )       

    def seed_report_configs(self, report_configs_data):
        """Seed the main report configuration data - only update when values actually change"""
        logger.info('Seeding report configuration data...')
        
        created_count = 0
        skipped_count = 0

        # Fetch Header Groupings to resolve foreign keys from their names.
        header_groupings_map = {hg.header_name: hg for hg in HeaderGroupingMaster.objects.all()}
        logger.info(f"  Fetched {len(header_groupings_map)} header groupings.")
        
        # Fetch the composite keys of all existing configs.
        existing_config_keys = set(
            UIReportConfigurations.objects.values_list('report_name', 'col_code')
        )
        logger.info(f"  Found {len(existing_config_keys)} existing report configuration keys.")

        configs_to_create = []
        # Adding the header_grouping data
        for config_data in report_configs_data:
            lookup_key = (config_data['report_name'], config_data['col_code'])

            # If the key already exists in the database, we skip it.
            if lookup_key in existing_config_keys:
                skipped_count += 1
                continue
            
            # Resolve the Header Grouping foreign key object from its name.
            hg_name = config_data.get('header_grouping_id')
            header_grouping_obj = None
            if isinstance(hg_name, str):
                header_grouping_obj = header_groupings_map.get(hg_name)
                if not header_grouping_obj:
                    raise ValueError(
                        f'Invalid header_grouping_id: "{hg_name}" not found. Halting process to trigger rollback.'
                    )
            # Create a new model instance (but DON'T save it to the DB yet).
            new_config = UIReportConfigurations(
                report_name=config_data['report_name'],
                col_code=config_data['col_code'],
                col_position=config_data.get('col_position', 0),
                header=config_data.get('header', ''),
                visible=config_data.get('visible', True),
                cell_alignment=config_data.get('cell_alignment', ''),
                value=config_data.get('value', ''),
                short_col_code=config_data.get('short_col_code', ''),
                header_grouping=header_grouping_obj,
                data_type=config_data.get('data_type', ''),
                is_color=config_data.get('is_color', False),
            )
            configs_to_create.append(new_config)

        if configs_to_create:
            # Create all the new records in one database query.
            created_objects = UIReportConfigurations.objects.bulk_create(configs_to_create)
            created_count = len(created_objects)
            logger.info(f"  Bulk created {created_count} new report configurations.")
        else:
            logger.info("  No new report configurations to create.")

        # Show summary statistics
        self.stdout.write(
            self.style.SUCCESS(
                f'Report configs: {created_count} created, {skipped_count} skipped (no changes)'
            )
        )