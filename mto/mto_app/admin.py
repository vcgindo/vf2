from django.contrib import admin

# Register your models here.

# admin.py
from import_export import resources, fields
from import_export.widgets import BooleanWidget
from import_export.admin import ImportExportModelAdmin

from mto_app.Masters.views import DeptMasterView
from .models import BufferMaster, CCRGroupMaster, CCRMaster, POOGIMajorReason, POOGIMinorReason, PlantHolidayList, PlantMaster, ProjectionOrder, UIReportConfigurations, ProjectionOrderDetails, BOMHeader, BOMDetail, PendingOrder, BatchwiseOrderAllocation, MTOOrderData, DeptMaster, FOL_Data, BufferItemTypeMapping, CCRItemTypeMapping, ItemTypeMaster, BufferTypeMaster, RouteMaster,MarketOperatingLeadTimeMaster
class UIReportConfigurationsResource(resources.ModelResource):
    Visible = fields.Field(attribute='Visible', column_name='Visible', widget=BooleanWidget())

    class Meta:
        model = UIReportConfigurations
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['report_name', 'col_code', 'col_position', 'header']
        fields = ('report_name', 'col_code', 'col_position', 'header', 'visible', 'cell_alignment', 'value','short_col_code')

class UIReportConfigurationsAdmin(ImportExportModelAdmin):
    resource_class = UIReportConfigurationsResource

class PlantMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = PlantMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['plant_id']
        fields = ('plant_id','plant_code','plant_name', 'is_valid')


class PlantMasterAdmin(ImportExportModelAdmin):
    resource_class = PlantMasterResource

class DeptMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = DeptMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['dept_id']
        fields = ('dept_id','dept_code','dept_name', 'is_valid', 'need_confirmation')


class DeptMasterAdmin(ImportExportModelAdmin):
    resource_class = DeptMasterResource

class CCRGroupMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = CCRGroupMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['ccr_group_id']
        fields = ('ccr_group_id','ccr_group_code','ccr_group_name', 'is_valid')


class CCRGroupMasterAdmin(ImportExportModelAdmin):
    resource_class = CCRGroupMasterResource


class CCRMasterResource(resources.ModelResource):

    class Meta:
        model = CCRMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['ccr_id','ccr_code','ccr_name', 'capacity_per_day','working_hours_per_day','schedule_horizon','fol_horizon','residual_buffer','ccr_attr1', 'ccr_attr2','ccr_attr3', 'ccr_attr4', 'ccr_attr5', 'ccr_attr6', 'ccr_attr7', 'ccr_attr8', 'ccr_attr9', 'ccr_attr10','is_valid', 'ccr_group_id','dept_id','plant_id']
        fields = ('ccr_id','ccr_code','ccr_name', 'capacity_per_day','working_hours_per_day','schedule_horizon','fol_horizon','residual_buffer','ccr_attr1', 'ccr_attr2','ccr_attr3', 'ccr_attr4', 'ccr_attr5', 'ccr_attr6', 'ccr_attr7', 'ccr_attr8', 'ccr_attr9', 'ccr_attr10','is_valid', 'ccr_group','dept','plant')


class CCRMasterAdmin(ImportExportModelAdmin):
    resource_class = CCRMasterResource

class ItemTypeMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = PlantMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['item_type_id']
        fields = ('item_type_id','item_type')


class ItemTypeMasterAdmin(ImportExportModelAdmin):
    resource_class = ItemTypeMasterResource


class BufferMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = BufferMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['buffer_id']
        fields = ('buffer_id','buffer_code','buffer_desc','buffer_size','SLT','MLT','is_blue','is_prod_buff','is_proc_buff','is_valid')


class BufferMasterAdmin(ImportExportModelAdmin):
    resource_class = BufferMasterResource

class BufferTypeMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = BufferTypeMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['buffer_type_id']
        fields = ('buffer_type_id','type_code','type_name', 'is_valid')


class BufferTypeMasterAdmin(ImportExportModelAdmin):
    resource_class = BufferTypeMasterResource

class RouteMasterResource(resources.ModelResource):
    # is_valid = fields.Field(attribute='is_valid', column_name='Is Valid', widget=BooleanWidget())

    class Meta:
        model = RouteMaster
        skip_unchanged = True
        report_skipped = False
        import_id_fields = ['route_id']
        fields = ('route_id','route_code','route_name', 'is_valid')


class RouteMasterAdmin(ImportExportModelAdmin):
    resource_class = RouteMasterResource


admin.site.register(UIReportConfigurations, UIReportConfigurationsAdmin)
admin.site.register(ProjectionOrderDetails)
admin.site.register(BOMDetail)
admin.site.register(BOMHeader)
admin.site.register(PendingOrder)
admin.site.register(BatchwiseOrderAllocation)
admin.site.register(MTOOrderData)
admin.site.register(ProjectionOrder)
admin.site.register(PlantMaster, PlantMasterAdmin)
admin.site.register(CCRGroupMaster, CCRGroupMasterAdmin)
admin.site.register(CCRMaster, CCRMasterAdmin)
admin.site.register(BufferMaster, BufferMasterAdmin)
admin.site.register(PlantHolidayList)
admin.site.register(POOGIMajorReason)
admin.site.register(POOGIMinorReason)
admin.site.register(DeptMaster, DeptMasterAdmin)
admin.site.register(FOL_Data)
admin.site.register(ItemTypeMaster, ItemTypeMasterAdmin)
admin.site.register(BufferItemTypeMapping)
admin.site.register(CCRItemTypeMapping)
admin.site.register(BufferTypeMaster)
admin.site.register(RouteMaster, RouteMasterAdmin)
admin.site.register(MarketOperatingLeadTimeMaster)
