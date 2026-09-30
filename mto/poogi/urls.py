from django.urls import path

from .PoogiReasonsForDelayedOrders.views import (GetDelayedOrdersForPoogiReasonAssignmentView , PoogiMajorMinorReasonMasterView , 
GetPoogiReasonsForDelayedOrdersAnalyticsDataView , AssignPoogiReasonForOrdersView)
from .views import (GetBMReportRemarksView)
from .ResourceUtilizationAndWIP.views import (GetResourceUtilizationAndWIPProfileView)
from .OTIFAnalysis.views import (GetOTIFAnalysisView)
from .TopFailureReasons.views import (TopFailureReasonsView)
from .TrendOfFailureReasons.views import (TrendOfFailureReasonsView)
from .OTAndIFAnalysis.views import (GetOTandIFAnalysisView)
urlpatterns = [
    path('getPoogiReasonForDealyedOrdersData/',GetDelayedOrdersForPoogiReasonAssignmentView.as_view(),name='Poogi reasons for delayed orders'),
    path('getBMReportRemarksData/',GetBMReportRemarksView.as_view(),name='Get remarks for the order'),
    path('getPoogiReasonMasterData/',PoogiMajorMinorReasonMasterView.as_view(),name='Get poogi reason master view'),
    path('getPoogiReasonForDelayedOrdersAnalyticsData/',GetPoogiReasonsForDelayedOrdersAnalyticsDataView.as_view(),name='get the analytics data for delayed orders'),
    path('updatePoogiReasonsforOrders/',AssignPoogiReasonForOrdersView.as_view(),name='Assignment of the poogi reasons for the order'),
    path('getOTIFAnalysisData/', GetOTIFAnalysisView.as_view(), name='Get OTIF analysis data'),
    path('getOTandIFAnalysisData/', GetOTandIFAnalysisView.as_view(), name='Get OT&IF analysis data'),    
    path('getResourceUtilizationAndWIPProfileData/' ,GetResourceUtilizationAndWIPProfileView.as_view(),name = 'fetch STPL and Fullkit in days data'),
    path('getTopFailureReasonsData/',TopFailureReasonsView.as_view(),name='Get top failure reasons'),
    path('getTrendOfFailureReasonsData/',TrendOfFailureReasonsView.as_view(),name='Get top failure reasons'),
]