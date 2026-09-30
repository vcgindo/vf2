from django.urls import path
from .ProcurementPlanning.views import (ProcurementPlanningView, BatchwiseComponentAllocationUpdateAtSimulationView, GetProdDataAfterSimulationView, 
ProcurementSimulationView, ProcurementPlanningSimulationView)
from .MaterialCoverageForOpenSo.views import (GetOpenSOSummaryDataView , GetOpenSODetailsView)
from .MaterialRequirement.views import (GetMaterialRequirementDataView, GetMaterialRequirementDayWiseDataView)
from .RMPMCoverage.views import (GetProdDataForRMPMCoverageView)
from .RMPMBufferTrend.views import (GetRMPMBufferTrendMTOMTAView)
from .ExpeditingRM.views import (ExpiditingRMAndSupplierView)
from .DayWiseCoverage.views import (GetDayWiseCoverageView)

urlpatterns = [
    path('getProcPlanningData/', ProcurementPlanningView.as_view(), name='Get Procurement Planning Data'),
    path('updateBatchwiseCompAllocAtSimulation/', BatchwiseComponentAllocationUpdateAtSimulationView.as_view(), name='Update simulated quantity in Batchwise Component Allocation'),
    path('getProdDataAfterSimulation/', GetProdDataAfterSimulationView.as_view(), name='Get Prod Data After Simulation'),
    path('getOpenSOSummaryData/', GetOpenSOSummaryDataView.as_view(), name='Get Open SO Summary Data'),
    path('getOpenSODetailsData/', GetOpenSODetailsView.as_view(), name='Get Open SO Details Data'),
    path('getMaterialRequirementData/', GetMaterialRequirementDataView.as_view(), name='Get Material Requirement Data'),
    path('getMaterialRequirementDayWiseData/', GetMaterialRequirementDayWiseDataView.as_view(), name='Get Material Requirement day wise Data'),
    path('getRMPMCoverageData/', GetProdDataForRMPMCoverageView.as_view(), name='RM PM wise coverage'),
    path('getRMPMBufferTrendData/',GetRMPMBufferTrendMTOMTAView.as_view(),name = ' Get RM PM buffer trend Data'),
    path('getExpiditingRMData/',ExpiditingRMAndSupplierView.as_view(),name = ' Get expiditing Rm supplier graph data'),
    path('UpdateProcurementSimulationData/',ProcurementSimulationView.as_view(),name='Insert procurement simulation data'),
    path('getDayWiseCoverageData/', GetDayWiseCoverageView.as_view(), name='Get day wise coverage data'),
    path('updateProcurementPlanningSimulatedQty/', ProcurementPlanningSimulationView.as_view(), name='update Procurement planning simulation qty data'),

]
