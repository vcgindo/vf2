from django.urls import path
from .views import (GetBOMLevelWiseAllocationDataView )
from .Common.views import (CalculateAndUpdateBufferPenetration , AssignRouteView , GetLineCCRDetailsView , UpdateBMReportRemarksView,
CreateOverallBMReportView,UpdateFOLandSTPL,BomLevelExplosionView)
from .DDQ.views import ( GetOrdersForDDQView , AssignBufferAndEstimatedDueDateView, 
DDQBufferAndRouteAssignment,AssignDueDateView , ScheduleOrdersView)
from .OrderRescheduling.views import GetOrderReschedulingDataView , UpdateOrderDueDateView , GetHolidaysForMaxFolCCROfOrder
from .EnquiryResponse.views import EnquiryResponseView
from .DeptWiseBMReport.views import DeptWiseBMReportView,DepartmentWiseWIPForOrdersView , UpdateBMReportOrdersView ,DeptHighAgeingView
from .OverallBMReport.views import OverAllBMReportView
from .ElapsedTime.views import GetElapsedTimeDataView, ElapsedTimeForPlantAndDeptView
from .STPLandFullkit.views import STPLandFullkitInDaysView
from .BMTrend.views import BMTrendDataView
from .OrderAtRisk.views import OrdersAtRiskView
from .LeadTime.views import LeadTimeForOrdersView
from .OrderBalance.views import GetOrderBalanceView
from .DRM.views import DynamicReleaseView,UpdateDynamicReleaseOrderView , CalculateFOLBasedDueDateView
from .FullKitAssignment.views import (FullKitOnSimulationView, StockAllocationOnSimulationView ,GetFullKitAssignmentDataWithGraphView,ResetOrderView,
ExcludeOrdersForFullkitAssignmentView)
from .FutureOrderLoadChart.views import (FutureOrderLoadCCRFOLHorizonDateView ,FutureOrderLoadChartAPIView)

urlpatterns = [
    path('getEnquiryResponseData/', EnquiryResponseView.as_view(), name='Get Enquiry Response Data'),
    path('GetOrderReschedulingData/',GetOrderReschedulingDataView.as_view(),name = 'Get Order Rescheduling Data'),
    path('getBMTrendData/',BMTrendDataView.as_view(),name = 'Get BM trend data '),
    path('UpdateOrderDueDate/' ,UpdateOrderDueDateView.as_view(),name = 'Update Order Due Date'),
    path('getOrdersForDDQ/' ,GetOrdersForDDQView.as_view(),name = ' Get orders for Due Date Quotation'),
    path('updateBufferAssignment/',AssignBufferAndEstimatedDueDateView.as_view(),name='Update buffer for the orders'),
    path('updateOrderDataRoute/',AssignRouteView.as_view(),name='Update routes for the orders'),
    path('assignOrderDueDate/',AssignDueDateView.as_view(),name='Update due date for the orders'),
    path('getOrdersAtRiskData/',OrdersAtRiskView.as_view(),name='Get top 10 reasons for order at risk'),
    path('getOrderBalanceData/',GetOrderBalanceView.as_view(),name='get balance order for trailing department'),
    path('getDeptWiseBMReportData/',DeptWiseBMReportView.as_view(),name='get dept wise bm report data'),
    path('getDeptWiseWipData/',DepartmentWiseWIPForOrdersView.as_view(),name='get dept wise wip data for order'),
    path('createBMReportRemarksData/',UpdateBMReportRemarksView.as_view(),name='create BM Report Remarks data for order'),
    path('getFullKitAssignmentDataWithGraphData/',GetFullKitAssignmentDataWithGraphView.as_view(),name='get fullkit assignment data with graph data'),
    path('updateExcludedOrdersForFullkitAssignment/',ExcludeOrdersForFullkitAssignmentView.as_view(),name='add free RM stock'),
    path('updateResetOrderData/',ResetOrderView.as_view(),name='update free RM stock and update excluded orders'),
    path('getSTPLandFullkitInDaysData/' ,STPLandFullkitInDaysView.as_view(),name = 'fetch STPL and Fullkit in days data'),
    path('UpdateFolAndStpl/',UpdateFOLandSTPL.as_view(),name='update fol and stpl'),
    path('getElapsedTimeData/',GetElapsedTimeDataView.as_view(),name='get elapsed time data'),
    path('getElapsedDaysforDeptPlantData/',ElapsedTimeForPlantAndDeptView.as_view(),name='get elapsed days data for dept and plant'),
    path('getBomExplosionData/',BomLevelExplosionView.as_view(),name='bom level explosion'),
    path('getOverAllBMReportData/',OverAllBMReportView.as_view(),name='get overall bm report data'),
    path('getLeadTimeData/',LeadTimeForOrdersView.as_view(),name='get lead time data for orders'),
    path('getHighAgeingData/',DeptHighAgeingView.as_view(),name='get dept ageing data for the order'),
    path('getLineCCRDetailsData/',GetLineCCRDetailsView.as_view(),name='get the line ccr details'),
    path('updateScheduleOrders/',ScheduleOrdersView.as_view(),name='Schedule orders for DDQ'),
    path('updateOverallBMReportData/',CreateOverallBMReportView.as_view(),name='create overall bm report data'),
    path('getDynamicReleaseData/',DynamicReleaseView.as_view(),name='get dynamic release data view'),
    path('UpdateBufferPenetrationData/',CalculateAndUpdateBufferPenetration.as_view(),name='update the bpp for the orders'),
    path('UpdateDynamicReleaseData/',UpdateDynamicReleaseOrderView.as_view(),name='update the orders for dynamic release'),
    path('getBOMLevelWiseAllocationData/',GetBOMLevelWiseAllocationDataView.as_view(),name='get the level wise allocation data'),
    path('UpdateBuffRouteCCREstDate/',DDQBufferAndRouteAssignment.as_view(),name='assing Buffer Route FOL Data and Estimated Due Date in single api'),
    path('UpdateOrSimulateStockAllocation/',StockAllocationOnSimulationView.as_view(),name='Update or simulate stock allocation data'),
    path('UpdateFullkitOnSimulation/',FullKitOnSimulationView.as_view(),name='Update fullkit data on simulation'),
    path('updateBMReportOrders/',UpdateBMReportOrdersView.as_view(),name='mark BM report orders closed or open'),
    path('GetFOLBasedDueDate/',CalculateFOLBasedDueDateView.as_view(),name='Get FOL based due date'),
    path('getFutureOrderLoadCCRFOLHorizonDate/',FutureOrderLoadCCRFOLHorizonDateView.as_view(),name='Get Future Order Load CCR FOL Horizon Date'),
    path('getFutureOrderLoadChartData/',FutureOrderLoadChartAPIView.as_view(),name='Get Future Order Load Chart Data'),   
    path('getHolidaysForMaxFolCCROfOrder/',GetHolidaysForMaxFolCCROfOrder.as_view(),name='Get holidays for max FOL CCR of order'),
]