from django.urls import path

# from .views.get_master_view import GetCountView, GetMasterDataView
from .views.basic_validation import MasterValidationView
# from .views.add_master_view import AddMasterDataView
# from .views.modify_master_view import ModifyMasterDataView
# from .views.delete_master_view import DeleteMasterdataView
from .views.get_upload_progress import GetUploadProgressView
# from .views.get_ui_configuration_view import GetUiConfigView
urlpatterns = [
    path('basic-validation/<path:masterId>', MasterValidationView.as_view()),
    # path('add-valid-master/', AddMasterDataView.as_view()),
    # path('get-count/', GetCountView.as_view()),
    # path('get-master-data/', GetMasterDataView.as_view()),
    # path('modify-master-data/', ModifyMasterDataView.as_view()),
    # path('remove-master-data/', DeleteMasterdataView.as_view()),
    # path('get-ui-configurations/', GetUiConfigView.as_view()),
    path('get-upload-progress/<path:processId>', GetUploadProgressView.as_view())
]
