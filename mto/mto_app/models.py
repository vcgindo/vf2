from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

# Create your models here.

# ========================================================
# DBR Tables
# ======================================================== 

# ========================================================
# OrderTypeMaster model
# ========================================================
class OrderTypeMaster(models.Model):
    order_type = models.AutoField(primary_key=True)
    desc = models.CharField(max_length=200)

    class Meta:
        db_table = 'Master_Order_Type'   

    def __str__(self):
        return f'{self.desc}'
 

# ========================================================
# Input_Files model
# ========================================================
class InputFiles(models.Model):
    file_name = models.CharField(max_length=100)
    input_folder = models.CharField(max_length=100)
    file_type = models.CharField(max_length=1)
    day = models.IntegerField()
    is_critical = models.BooleanField()
    variable_name = models.CharField(max_length=100)
    resolved_filename = models.CharField(max_length=100, null=True, blank=True)
    module_name = models.CharField(max_length = 10 , null = True)

    class Meta:
        db_table = 'InputFiles'

    def __str__(self):
        return f'{self.file_name}'

# ========================================================
# DBRSettings model
# ========================================================
class DBRSettings(models.Model):

    flag = models.CharField(max_length=50, primary_key=True)
    value = models.CharField(max_length=500)
    description = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'DBR_Settings'  
 
    def __str__(self):
        return f'{self.flag}'


# ========================================================
# InputTableList model
# ========================================================
class InputTableList(models.Model):

    database_name = models.CharField(max_length=100)
    tbl_name = models.CharField(max_length=100) 
    condition = models.CharField(max_length=500, null=True, blank=True)
    is_critical = models.BooleanField(default=False ,null = False)

    class Meta:
        db_table = 'InputTable_List'
        constraints = [
            models.UniqueConstraint(fields=['database_name', 'tbl_name'], name='inputtable_list_pkey')
        ]
 
    def __str__(self):
        return f'{self.database_name}-{self.tbl_name}'

# ========================================================
# BufferTypeMaster model
# ======================================================== 
class BufferTypeMaster(models.Model):
    buffer_type_id = models.IntegerField(primary_key=True)
    buffer_type = models.CharField(max_length=100)
    buffer_type_desc = models.CharField(max_length=200)
    is_valid = models.BooleanField(default=True)
 
    class Meta:
        db_table = 'Master_Buffer_Type'

        constraints = [
                models.UniqueConstraint(fields=['buffer_type_id', 'buffer_type'], name='Master_Buffer_Type_PK')
            ]
 
    def __str__(self):
        return f'{self.buffer_type_id}-{self.buffer_type}'

# ========================================================
# BufferMaster model
# ======================================================== 
class BufferMaster(models.Model):
    buffer_id = models.IntegerField(primary_key=True)
    buffer_code = models.CharField(max_length=100)
    buffer_desc = models.CharField(max_length=200)
    buffer_size = models.IntegerField()
    slt = models.IntegerField() 
    mlt = models.IntegerField() 
    is_blue = models.BooleanField(default=False)
    buffer_type = models.ForeignKey(BufferTypeMaster, on_delete=models.RESTRICT, related_name='master_buffer_master_buffer_type')
    is_valid = models.BooleanField(default=True)
 
    class Meta:
        db_table = 'Master_Buffer'

        constraints = [
                models.UniqueConstraint(fields=['buffer_id', 'buffer_code'], name='Master_Buffer_PK')
            ]
 
    def __str__(self):
        return f'{self.buffer_id}-{self.buffer_code}'

# ========================================================
# PlantMaster model
# ======================================================== 
class PlantMaster(models.Model):
    plant_id = models.IntegerField(primary_key=True)
    plant_code = models.CharField(max_length=100)
    plant_name = models.CharField(max_length=200)
    is_valid = models.BooleanField(default=True)
 
    class Meta:
        db_table = 'Master_Plant'

        constraints = [
                models.UniqueConstraint(fields=['plant_id', 'plant_code'], name='Master_Plant_PK')
            ]
 
    def __str__(self):
        return f'{self.plant_id}-{self.plant_code}'

# ========================================================
# CCR Group Master model
# ========================================================
class CCRGroupMaster(models.Model):
    ccr_group_id = models.IntegerField(primary_key=True)
    ccr_group_code = models.CharField(max_length=100)
    ccr_group_name = models.CharField(max_length=200)
    is_valid = models.BooleanField(default= True)

    class Meta:
        db_table = 'Master_CCRGroup'

        constraints = [
                models.UniqueConstraint(fields=['ccr_group_id', 'ccr_group_code'], name='Master_CCRGroup_PK')
            ]
 
    def __str__(self):
        return f'{self.ccr_group_id}-{self.ccr_group_code}'

# ========================================================
# DeptMaster model
# ========================================================
class DeptMaster(models.Model):
    dept_id = models.IntegerField(primary_key=True)
    dept_code = models.CharField(max_length=100)
    dept_name = models.CharField(max_length=200)
    is_valid = models.BooleanField(default=True)
    need_confirmation = models.BooleanField(default=False)
 
    class Meta:
        db_table = 'Master_Dept'

        constraints = [
                models.UniqueConstraint(fields=['dept_id', 'dept_code'], name='Master_Dept_PK')
            ]
 
    def __str__(self):
        return f'{self.dept_id}-{self.dept_code}-{self.dept_name}'

# ========================================================
# CCRMaster model
# ======================================================== 
class CCRMaster(models.Model):
    ccr_id = models.IntegerField(primary_key=True)
    ccr_code = models.CharField(max_length=100)
    ccr_name = models.CharField(max_length=200)    
    capacity_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    working_hours_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    schedule_horizon = models.IntegerField()
    fol_horizon = models.IntegerField()
    residual_buffer = models.DecimalField(max_digits=13, decimal_places=2) 
    ccr_attr1 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr2 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr3 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr4 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr5 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr6 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr7 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr8 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr9 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr10 = models.CharField(max_length=200, null= True, blank= True)
    is_valid = models.BooleanField(default=True)
    ccr_group = models.ForeignKey(CCRGroupMaster, on_delete=models.RESTRICT, related_name='Master_CCRGroup')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='Master_Plant')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='Master_Dept')
    cumulative_wip_limit = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'Master_CCR'

        constraints = [
                models.UniqueConstraint(fields=['ccr_id', 'ccr_code','ccr_group'], name='Master_CCR_PK')
            ]
 
    def __str__(self):
        return f'{self.ccr_id}-{self.ccr_code}'

# ========================================================
# OrderStageMaster model
# ========================================================
class OrderStageMaster(models.Model):
    stage_id = models.IntegerField(primary_key=True)
    stage_desc = models.CharField(max_length=300)
 
    class Meta:
        db_table = 'Master_OrderStage'

        constraints = [
                models.UniqueConstraint(fields=['stage_id', 'stage_desc'], name='Master_OrderStage_PK')
            ]
 
    def __str__(self):
        return f'{self.stage_id}-{self.stage_desc}'

# ========================================================
# ReasonMaster model
# ========================================================
class ReasonMaster(models.Model):
    reason_code = models.IntegerField(primary_key=True)
    reason_desc = models.CharField(max_length=200)
    display_desc = models.CharField(max_length=200)
    type = models.CharField(max_length=50)
 
    class Meta:
        db_table = 'Master_Reason'

        constraints = [
                models.UniqueConstraint(fields=['reason_code', 'reason_desc'], name='Master_Reason_PK')
            ]
 
    def __str__(self):
        return f'{self.reason_code}-{self.reason_desc}'


# ========================================================
# RouteMaster model
# ========================================================
class RouteMaster(models.Model):
    route_id = models.AutoField(primary_key=True)
    route_code = models.CharField(max_length=100)
    route_name = models.CharField(max_length=200)
 
    class Meta:
        db_table = 'Master_Route'

        constraints = [
                models.UniqueConstraint(fields=['route_id', 'route_code'], name='Master_Route_PK')
            ]
 
    def __str__(self):
        return f'{self.route_code}-{self.route_name}'

# ========================================================
# ItemTypeMaster model
# ========================================================
class ItemTypeMaster(models.Model):
    item_type_id = models.IntegerField(primary_key=True)
    item_type = models.CharField(max_length=500)
 
    class Meta:
        db_table = 'Master_ItemType'

        constraints = [
                models.UniqueConstraint(fields=['item_type_id', 'item_type'], name='Master_ItemType_PK')
            ]
 
    def __str__(self):
        return f'{self.item_type_id}-{self.item_type}'

# ========================================================
# ItemMaster model
# ======================================================== 
class ItemMaster(models.Model):
    item_code = models.CharField(max_length=50, primary_key=True) 
    item_description = models.CharField(max_length=100)
    item_type = models.ForeignKey(ItemTypeMaster, on_delete=models.RESTRICT, related_name='master_item_master_item_type')
    attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'Master_Item'

    def __str__(self):
        return f'{self.item_code}'

# ========================================================
# POOGIMajorReason model
# ========================================================
class POOGIMajorReason(models.Model):
    major_reason_id = models.AutoField(primary_key=True)
    major_reason_code = models.CharField(max_length=50)
    major_reason_desc = models.CharField(max_length=200)
    plant = models.ForeignKey(PlantMaster,on_delete=models.RESTRICT, related_name='poogi_major_reason_master_plant', null=True, blank= True)
    is_valid = models.BooleanField(default=True)
    class Meta:
        db_table = 'POOGI_MajorReason'
        constraints = [
            models.UniqueConstraint(
                fields=["major_reason_id", "major_reason_code"], name="POOGI_MajorReason_PK"
            )
        ]
 
    def __str__(self):
        return f'POOGIMajorReason {self.major_reason_id}-{self.major_reason_desc}'

# ========================================================
# POOGIMinorReason model
# ========================================================
class POOGIMinorReason(models.Model):
    minor_reason_id = models.AutoField(primary_key=True)
    minor_reason_code = models.CharField(max_length=50)
    minor_reason_desc = models.CharField(max_length=200)
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='poogi_minor_reason_poogi_major_reason')
    is_valid = models.BooleanField(default=True)
    class Meta:
        db_table = 'POOGI_MinorReason'
        constraints = [
            models.UniqueConstraint(
                fields=["minor_reason_id", "minor_reason_code", "major_reason"], name="POOGI_MinorReason_PK"
            )
        ]
 
    def __str__(self):
        return f'POOGIMinorReason {self.minor_reason_id}-{self.minor_reason_desc}-{self.major_reason}'

# ========================================================
# CustomerMaster model
# ========================================================
class CustomerMaster(models.Model):
    cust_code = models.CharField(max_length=200)
    cust_name = models.CharField(max_length=250)
    attribute = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'Master_Customer'
        constraints = [
            models.UniqueConstraint(
                fields=["cust_code", "cust_name"], name="Master_Customer_PK"
            )
        ]
 
    def __str__(self):
        return f'CustomerMaster {self.cust_code}-{self.cust_name}'

# ========================================================
# MarketOperatingLeadTimeMaster model
# ========================================================
class MarketOperatingLeadTimeMaster(models.Model):
    item_type = models.ForeignKey(ItemTypeMaster, on_delete= models.RESTRICT, related_name='market_lead_time_master_item_type_master')
    market_based_order_type = models.CharField(max_length=250, null=True, blank=True)
    lead_time = models.IntegerField()
    
    class Meta:
        db_table = 'Master_Market_Operating_Lead_Time'
        constraints = [
            models.UniqueConstraint(
                fields=["item_type", "market_based_order_type", "lead_time"], name="Master_Market_Operating_Lead_Time_PK"
            )
        ]
 
    def __str__(self):
        return f'MarketOperatingLeadTimeMaster {self.item_type}-{self.order_type}-{self.lead_time}'

# ========================================================
# CCRItemTypeMapping model
# ========================================================
class CCRItemTypeMapping(models.Model):
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='ccr_item_type_mapping_master_ccr')
    item_type = models.ForeignKey(ItemTypeMaster, on_delete=models.RESTRICT, related_name='ccr_item_type_mapping_master_item_type')
    touch_time_in_mins = models.DecimalField(max_digits=13, decimal_places=2, null=True)
    batch_size = models.DecimalField(max_digits=18 ,decimal_places=5,null=True, blank=True)

    class Meta:
        db_table = 'Map_CCR_ItemType'

        constraints = [
                models.UniqueConstraint(fields=['ccr_id', 'item_type'], name='Map_CCR_ItemType_PK')
            ]
 
    def __str__(self):
        return f'{self.ccr_id}-{self.item_type}-{self.touch_time_in_mins}'

# ========================================================
# BufferItemTypeMapping model
# ========================================================
class BufferItemTypeMapping(models.Model):

    item_type = models.ForeignKey(ItemTypeMaster, on_delete=models.RESTRICT, related_name='buffer_item_type_mapping_master_item_type')
    buffer = models.ForeignKey(BufferMaster, on_delete=models.RESTRICT, related_name='buffer_item_type_mapping_master_buffer')
  
    class Meta:
        db_table = 'Map_Buffer_ItemType'

        constraints = [
                models.UniqueConstraint(fields=['item_type', 'buffer'], name='Map_Buffer_ItemType_PK')
            ]
 
    def __str__(self):
        return f'{self.prod_buff}-{self.proc_buff}-{self.item_type}' 

# ========================================================
# OrderStageMapping model
# ========================================================
class OrderStageMapping(models.Model):

    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='order_stage_mapping_master_plant')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='order_stage_mapping_master_dept')
    stage = models.ForeignKey(OrderStageMaster, on_delete=models.RESTRICT, related_name='order_stage_mapping_master_order_stage')

    class Meta:
        db_table = 'Map_Order_Stage'

        constraints = [
                models.UniqueConstraint(fields=['plant', 'dept', 'stage'], name='Map_Order_Stage_PK')
            ]
 
    def __str__(self):
        return f'{self.plant}-{self.dept}-{self.stage}'

# ========================================================
# UserPlantDeptMapping model
# ========================================================
class UserPlantDeptMapping(models.Model):

    user_name = models.CharField(max_length=200)
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='user_plant_dept_mapping_master_plant')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='user_plant_dept_mapping_master_dept') 

    class Meta:
        db_table = 'Map_User_Plant_Dept'
 
    def __str__(self):
        return f'{self.user_name}-{self.plant}-{self.dept}'

# ========================================================
# DailyWorkingCalendar model
# ========================================================
class DailyWorkingCalendar(models.Model):

    lno = models.IntegerField()
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='daily_working_calendar_master_plant')
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='daily_working_calendar_master_ccr')
    working_date = models.DateField()

    class Meta:
        db_table = 'Daily_Working_Calendar'  
 
    def __str__(self):
        return f'{self.working_date}'

# ========================================================
# PlantHolidayList model
# ========================================================
class PlantHolidayList(models.Model):
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='plant_holiday_list_master_plant')
    ccr_id = ArrayField(models.IntegerField(), null=True, blank=True, default=list)
    is_week_day = models.BooleanField(default=False)
    day_of_week = models.JSONField(default=list, null=True, blank=True)
    holiday_start_date = models.DateField(null= True, blank= True)
    holiday_end_date = models.DateField(null= True, blank= True)
    is_working_day = models.BooleanField(default= False)    
    description = models.CharField(max_length=200)
    repeatation_bucket = models.CharField(max_length=100, null= True, blank= True)
    repeat_duration_in_weeks = models.IntegerField(null= True, blank= True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        db_table = 'Plant_Holiday_List'   
 
    def __str__(self):
        return f'{self.plant}-{self.ccr}'

# ========================================================
# PlantHolidayListLog model
# ========================================================
class PlantHolidayListLog(models.Model):
    is_week_day = models.BooleanField()
    day_of_week = models.JSONField(default=list, null=True, blank=True)    
    holiday_start_date = models.DateField(null= True, blank= True)
    holiday_end_date = models.DateField(null= True, blank= True)
    is_working_day = models.BooleanField()    
    description = models.CharField(max_length=200)
    ccr_id = ArrayField(models.IntegerField(), null=True, blank=True, default=list)
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='plant_holiday_list_log_master_plant')
    execution_date = models.CharField(max_length=50)
    repeatation_bucket = models.CharField(max_length=100, null= True, blank= True)
    repeat_duration_in_weeks = models.IntegerField(null= True, blank= True)

    class Meta:
        db_table = 'Plant_Holiday_List_Log'   
 
    def __str__(self):
        return f'{self.plant}-{self.ccr}-{self.execution_date}'

# ========================================================
# OrderAttributeDataRaw model
# ========================================================
class OrderAttributeDataRaw(models.Model):
    order_id = models.CharField(max_length=200)
    attributes = models.JSONField()

    class Meta:
        db_table = 'Order_Attribute_Data_Raw'   
 
    def __str__(self):
        return f'{self.order_id}'

# ========================================================
# LineAttributeDataRaw model
# ========================================================
class LineAttributeDataRaw(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    attributes = models.JSONField()

    class Meta:
        db_table = 'Line_Attribute_Data_Raw'   
 
    def __str__(self):
        return f'{self.order_id}'

# ========================================================
# MTAOrderDataRaw model
# ========================================================
class MTAOrderDataRaw(models.Model):

    order_id = models.CharField(max_length=200)
    line_id= models.CharField(max_length=250, null=True, blank=True)
    order_key = models.CharField(max_length=500)
    order_date = models.CharField(max_length=200)
    sku_code = models.CharField(max_length=200, null=True, blank=True)
    wh_code = models.CharField(max_length=200, null=True, blank=True)
    total_pending_qty = models.CharField(max_length=200, null=True, blank=True)
    route_id = models.IntegerField(null=True, blank=True)
    ccr = models.CharField(max_length=200, null=True, blank=True)
    plant = models.CharField(max_length=200, null=True, blank=True)
    item_group = models.CharField(max_length=50, null=True, blank=True)
    dept = models.CharField(max_length=200, null=True, blank=True)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'MTA_OrderDataRaw'   
 
    def __str__(self):
        return f'{self.order_id}-{self.line_id}'

# ========================================================
# MTAStockGITData model
# ========================================================
class MTAStockGITData(models.Model):

    sku_code = models.CharField(max_length=100)
    wh_code = models.CharField(max_length=100)
    norm = models.IntegerField(null=True, blank=True)
    closing_stock = models.IntegerField()
    git = models.IntegerField(default=0)
    time_buffer = models.IntegerField()
    virtual_norm = models.IntegerField(null=True, blank=True)
    blue_req = models.IntegerField()
    cbr_days = models.IntegerField( null=True, blank=True)
    dispatch_color = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'MTA_StockData'
        constraints = [
            models.UniqueConstraint(fields=['sku_code', 'wh_code'], name='MTA_StockData_PK')
        ]
 
    def __str__(self):
        return f'{self.sku_code}-{self.wh_code}'

# ========================================================
# MTOOrderData model
# ========================================================
class MTOOrderData(models.Model):
    order_id = models.CharField(max_length=200, primary_key=True)
    prod_buff_id = models.IntegerField()    
    prod_buff_date = models.DateField(null=True, blank=True)
    proc_rope_id = models.IntegerField(null=True, blank=True)
    proc_rope_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField()
    pre_order_buffer_size = models.IntegerField(null=True, blank=True)
    post_order_buffer_size = models.IntegerField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=20, null=True, blank=True)
    delay_days = models.IntegerField(null=True, blank=True)
    is_rm_released = models.BooleanField()
    can_finish_from_ui = models.BooleanField()
    is_manual_buffer_assigned = models.BooleanField()
    expected_due_date = models.DateField(null=True, blank=True)
    cust_code = models.CharField(max_length=20, null=True, blank=True)
    order_clearance_flag = models.CharField(max_length=1)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    class Meta:
        db_table = 'MTO_OrderData'
 
    def __str__(self):
        return f'Order {self.order_id}'

# ========================================================
# OrderData model
# ========================================================
class OrderData(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    order_key = models.CharField(primary_key=True ,max_length=500)
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='order_data_master_item')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='order_data_master_plant',null=True) 
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='order_data_master_dept', null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField()
    pre_order_buffer_size = models.IntegerField(null=True, blank=True)
    post_order_buffer_size = models.IntegerField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=20, null=True, blank=True)
    delay_days = models.IntegerField(null=True, blank=True)
    is_rm_released = models.BooleanField(default=False)
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='order_data_poogi_major_reason', null=True, blank=True)
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='order_data_poogi_minor_reason', null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True, default=0)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    allocated_fg = models.DecimalField(max_digits=13,decimal_places=3,null=True,blank=True)
    route = models.ForeignKey(RouteMaster,on_delete=models.RESTRICT, related_name='order_data_master_route', null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='order_data_master_ccr', null=True, blank=True)
    is_line_finished = models.BooleanField(default=False)
    computed_dd = models.DateField(null=True, blank=True)
    can_finish_from_ui = models.BooleanField(default=False)
    is_manual_buffer_assigned = models.BooleanField(default=False)
    expected_due_date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='order_data_master_customer', null=True, blank=True)
    order_stage = models.ForeignKey(OrderStageMaster, on_delete=models.RESTRICT, related_name='order_data_master_order_stage', null=True, blank=True)
    vf_order_type = models.CharField(max_length=10)
    market_based_order_type = models.CharField(max_length=250, null=True, blank=True)
    #Export-Urgent/Export-Normal/Domestic-Urgent/Domestic-Normal these types will be used in MarketLeadTimeMaster
    scheduled_on = models.DateField(null=True, blank=True)
    order_clearance_flag = models.CharField(max_length=1, default='N')
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    wh_code = models.CharField(max_length=100, null=True, blank=True)
    mta_po_date = models.DateField(null=True, blank=True)
    order_attributes = models.JSONField(null=True)
    line_order_attributes = models.JSONField(null=True)
    order_type = models.ForeignKey(OrderTypeMaster, on_delete=models.RESTRICT, related_name='order_data_master_order_type', null=True, blank=True) # As of now it is nullable, in future it may change to not null based on discussion
    is_closed = models.BooleanField(default=False)
    trailing_dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='order_data_master_trailing_dept', null=True, default='')
    computed_line_attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'OrderData'

        constraints = [
            models.UniqueConstraint(fields=['order_id', 'line_id'], name='Order_Data_PK')
        ]
 
    def __str__(self):
        return f'Order {self.order_id}-{self.line_id}'

#  =======================================================
# ItemDeptMapping Model
#  =======================================================
class ItemDeptMapping(models.Model):
    item_code = models.CharField(max_length=50)
    current_dept_id = models.IntegerField(null=True)
    next_dept_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'Map_Item_Dept'

        constraints = [
            models.UniqueConstraint(fields=['item_code','current_dept_id'],name='Item_DeptMapping_PK')
        ]

    def __str__(self):
        return f'{self.item_code}'

# =======================================================
# Order_WIPDetails Model
# =======================================================
class Order_WIPDetails(models.Model):
    order = models.ForeignKey(OrderData, on_delete=models.CASCADE, related_name='order_wip_details_order_data')
    item_code = models.CharField(max_length=50)
    wip_on_hand = models.DecimalField(max_digits=13, decimal_places=3,null=True)
    dept = models.ForeignKey(DeptMaster,on_delete=models.RESTRICT,related_name='order_wip_master_dept')
    mfg_balance = models.DecimalField(max_digits=13,decimal_places=3,null=True)
    entered_on = models.DateField(null=True)
    exited_on = models.DateField(null=True)
    elapsed_days = models.IntegerField(default=0)
    dispatch_balance = models.DecimalField(max_digits=13,decimal_places=3,null=True)

    class Meta:
        db_table = 'Order_WIPDetails'

    def __str__(self):
        return f'{self.order}'

# ========================================================
# MTOLineItemData model
# ========================================================
class MTOLineItemData(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    item_code = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='line_item_data_master_item')
    plant_id = models.IntegerField() 
    dept_id = models.IntegerField()
    major_id = models.IntegerField(null=True, blank=True)
    minor_id = models.IntegerField(null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    route_id = models.IntegerField(null=True, blank=True)
    ccr_id = models.IntegerField(null=True, blank=True)   
    line_entry_date = models.DateField()
    is_finished = models.BooleanField(default=False)
 
    class Meta:
        db_table = 'MTO_LineItemData'
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'line_id'], name='MTO_LineItemData_PK')
        ]
    def __str__(self):
        return f'{self.order_id}-{self.line_id}'

# ========================================================
# OrderBufferMapping model
# ========================================================
class OrderBufferMapping(models.Model):
    order = models.ForeignKey(OrderData, on_delete=models.RESTRICT, related_name='order_buffer_mapping_order_data')
    buffer = models.ForeignKey(BufferMaster, on_delete=models.RESTRICT, related_name='order_buffer_mapping_master_buffer')
    buffer_date = models.DateField(null=True, blank= True)

    class Meta:
        db_table = 'Map_Order_Buffer'
        constraints = [
            models.UniqueConstraint(fields=['order', 'buffer'], name='OrderBufferMapping_PK')
        ]

    def __str__(self):
        return f'{self.order}-{self.buffer}-{self.buffer_date}'
    
# ========================================================
# LineCCRDetails model
# ========================================================
class LineCCRDetails(models.Model):
 
    order = models.ForeignKey(OrderData, on_delete=models.RESTRICT, related_name='line_ccr_details_order_data')
    route = models.ForeignKey(RouteMaster, on_delete=models.RESTRICT, related_name='line_ccr_details_master_route', null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='line_ccr_details_master_ccr', null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, default = Decimal('0.00'), null=True, blank=True)
    order_load = models.DecimalField(max_digits=13, decimal_places=2, default = Decimal('0.00'), null=True, blank=True)
 
    class Meta:
        db_table = 'Line_CCR_Details'
        constraints = [
            models.UniqueConstraint(fields=['order','ccr'], name='Line_CCR_Details_PK')
        ]
 
    def __str__(self):
        return f'{self.order}'

# ========================================================
# DDQMultiStage model
# ========================================================
class DDQMultiStage(models.Model):

    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length= 250)
    stage_status = models.IntegerField()
    expected_due_date = models.DateField()
    tentative_due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'DDQ_MultiStage'  
 
    def __str__(self):
        return f'{self.flag}'

# ========================================================
# DDQChangesLog model
# ========================================================
class DDQChangesLog(models.Model):

    order = models.ForeignKey(OrderData, on_delete=models.DO_NOTHING, related_name='ddq_changes_log_order_data')
    org_due_date = models.DateField()
    is_unscheduled = models.BooleanField(default=False)
    is_due_date_changed = models.BooleanField(default=False)
    user_name = models.CharField(max_length=200)
    updated_on = models.DateTimeField()
    reason = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = 'DDQChanges_Log'  
 
    def __str__(self):
        return f'{self.order}'

# ========================================================
# Attributes_Order_Computed model
# ========================================================
class ComputedOrderAttributes(models.Model):
    order_id = models.CharField(max_length=200)
    c01 = models.CharField(max_length=150, null=True, blank=True)
    c02 = models.CharField(max_length=150, null=True, blank=True)
    c03 = models.CharField(max_length=150, null=True, blank=True)
    c04 = models.CharField(max_length=150, null=True, blank=True)
    c05 = models.CharField(max_length=150, null=True, blank=True)
    c06 = models.CharField(max_length=150, null=True, blank=True)
    c07 = models.CharField(max_length=150, null=True, blank=True)
    c08 = models.CharField(max_length=150, null=True, blank=True)
    c09 = models.CharField(max_length=150, null=True, blank=True)
    c10 = models.CharField(max_length=150, null=True, blank=True)
    c11 = models.CharField(max_length=150, null=True, blank=True)
    c12 = models.CharField(max_length=150, null=True, blank=True)
    c13 = models.CharField(max_length=150, null=True, blank=True)
    c14 = models.CharField(max_length=150, null=True, blank=True)
    c15 = models.CharField(max_length=150, null=True, blank=True)
    c16 = models.CharField(max_length=150, null=True, blank=True)
    c17 = models.CharField(max_length=150, null=True, blank=True)
    c18 = models.CharField(max_length=150, null=True, blank=True)
    c19 = models.CharField(max_length=150, null=True, blank=True)
    c20 = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        db_table = 'Attributes_Order_Computed'

        constraints = [
                models.UniqueConstraint(fields=['order_id'], name='Attributes_Order_Computed_PK')
            ]
 
    def __str__(self):
        return f'{self.order_id}'
 
# ========================================================
# Attributes_Order_Computed model
# ========================================================
#class ComputedOrderAttributes(models.Model):
#   order_id = models.CharField(max_length=200, primary_key=True)
#   attr_data = models.JSONField()
#
#   class Meta:
#       db_table = 'Attributes_Order_Computed'
#
#   constraints = [
#           models.UniqueConstraint(fields=['order_id'], name='Attributes_Order_Computed_PK')
#       ]
#
#   def __str__(self):
#       return f'{self.order_id}'

# ========================================================
# Attributes_Line_Computed model
# ========================================================
class ComputedLineAttributes(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    c01 = models.CharField(max_length=150, null=True, blank=True)
    c02 = models.CharField(max_length=150, null=True, blank=True)
    c03 = models.CharField(max_length=150, null=True, blank=True)
    c04 = models.CharField(max_length=150, null=True, blank=True)
    c05 = models.CharField(max_length=150, null=True, blank=True)
    c06 = models.CharField(max_length=150, null=True, blank=True)
    c07 = models.CharField(max_length=150, null=True, blank=True)
    c08 = models.CharField(max_length=150, null=True, blank=True)
    c09 = models.CharField(max_length=150, null=True, blank=True)
    c10 = models.CharField(max_length=150, null=True, blank=True)
    c11 = models.CharField(max_length=150, null=True, blank=True)
    c12 = models.CharField(max_length=150, null=True, blank=True)
    c13 = models.CharField(max_length=150, null=True, blank=True)
    c14 = models.CharField(max_length=150, null=True, blank=True)
    c15 = models.CharField(max_length=150, null=True, blank=True)
    c16 = models.CharField(max_length=150, null=True, blank=True)
    c17 = models.CharField(max_length=150, null=True, blank=True)
    c18 = models.CharField(max_length=150, null=True, blank=True)
    c19 = models.CharField(max_length=150, null=True, blank=True)
    c20 = models.CharField(max_length=150, null=True, blank=True)
    attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'Attributes_Line_Computed'

        constraints = [
                models.UniqueConstraint(fields=['order_id', 'line_id'], name='Attributes_Line_Computed_PK')
            ]
 
    def __str__(self):
        return f'{self.order_id}-{self.line_id}'
 
# ========================================================
# Attributes_Line_Computed model
# ========================================================
#class ComputedOrderAttributes(models.Model):
#   order_id = models.ForeignKey(MTO_OrderData, on_delete=models.CASCADE)
#   line_id = models.ForeignKey(MTO_OrderData, on_delete=models.CASCADE)
#   attr_data = models.JSONField()
#
#   class Meta:
#       db_table = 'Attributes_Line_Computed'
#
#   constraints = [
#           models.UniqueConstraint(fields=['order_id', 'line_id'], name='Attributes_Line_Computed_PK')
#       ]
#
#   def __str__(self):
#       return f'{self.order_id}'


# ========================================================
# BMReport_Remarks model
# ========================================================
class BMReportRemarks(models.Model):
 
    order = models.ForeignKey(OrderData, on_delete=models.RESTRICT, related_name='bm_report_remark_order_data')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='bm_report_remark_master_dept')
    remark = models.CharField(max_length=500)
    added_on = models.DateTimeField()
    added_by = models.CharField(max_length=200)
 
    class Meta:
        db_table = 'BMReport_Remarks'
 
    def __str__(self):
        return f'{self.order}-{self.remark}'


# ========================================================
# OrderDataProcessed model
# ========================================================
class OrderDataProcessed(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    order_key = models.CharField(max_length=200, null=True, blank=True)
    item_code = models.CharField(max_length=100, null=True, blank=True)
    item_desc = models.CharField(max_length=200, null=True, blank=True)
    item_group = models.CharField(max_length=100, null=True, blank=True)
    route_id = models.IntegerField(null=True, blank=True)
    ccr = models.CharField(max_length=100, null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    expected_due_date = models.CharField(max_length=200, null=True, blank=True)
    vf_due_date = models.CharField(max_length=200, null=True, blank=True)
    pre_order_buffer_size = models.CharField(max_length=200, null=True, blank=True)
    post_order_buff_size = models.CharField(max_length=200, null=True, blank=True)
    cust_code = models.CharField(max_length=200, null=True, blank=True)
    cust_name = models.CharField(max_length=200, null=True, blank=True)
    dept = models.CharField(max_length=200, null=True, blank=True)
    plant = models.CharField(max_length=200, null=True, blank=True)
    can_finish_from_ui = models.CharField(max_length=200, null=True, blank=True)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    class Meta:
        db_table = 'OrderData_Processed'
 
    def __str__(self):
        return f'Order {self.order_id}'

# ========================================================
# FOLData model
# ========================================================
class FOL_Data(models.Model):

    ccr = models.OneToOneField(CCRMaster, on_delete=models.CASCADE, related_name='fol_data_master_ccr', primary_key=True)
    fol_end_date = models.DateField()
    occupied_qty_in_units = models.IntegerField(null=True)
    occupied_qty_in_mins = models.IntegerField(null=True)
    fol_in_days = models.DecimalField(max_digits=13, decimal_places=2, default = Decimal('0.00'))
    stpl_in_days = models.DecimalField(max_digits=13, decimal_places=2, default = Decimal('0.00'))
    class Meta:
        db_table = 'FOL_Data'  
 
    def __str__(self):
        return f'{self.ccr_id}-{self.fol_end_date}'

# ========================================================
# HolidayCalendar model
# ========================================================
class HolidayCalendar(models.Model):

    plant = models.ForeignKey(PlantMaster, on_delete=models.CASCADE, related_name='holiday_calendar_master_plant')
    ccr = models.ForeignKey(CCRMaster, on_delete=models.CASCADE, related_name='holiday_calendar_master_ccr')
    holiday_date = models.DateField()

    class Meta:
        db_table = 'Holiday_Calendar'

        constraints = [
            models.UniqueConstraint(fields=['plant', 'ccr', 'holiday_date'], name='Holiday_Calendar_PK')
        ]
 
    def __str__(self):
        return f'{self.plant_id}-{self.ccr_id}-{self.holiday_date}'

# ========================================================
# OrderDataRaw model
# ========================================================
class OrderDataRaw(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    order_key = models.CharField(max_length=200, null=True, blank=True)
    item_code = models.CharField(max_length=100, null=True, blank=True)
    item_desc = models.CharField(max_length=200, null=True, blank=True)
    item_group = models.CharField(max_length=100, null=True, blank=True)
    route_id = models.IntegerField(null=True, blank=True)
    ccr = models.CharField(max_length=100, null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    expected_due_date = models.CharField(max_length=200, null=True, blank=True)
    cust_code = models.CharField(max_length=200, null=True, blank=True)
    cust_name = models.CharField(max_length=200, null=True, blank=True)
    dept = models.CharField(max_length=200, null=True, blank=True)
    plant = models.CharField(max_length=200, null=True, blank=True)
    can_finish_from_ui = models.CharField(max_length=200, null=True, blank=True)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    class Meta:
        db_table = 'OrderData_Raw'
 
    def __str__(self):
        return f'Order {self.order_id}'

# ========================================================
# MTOExclusion model
# ========================================================
class MTOExclusion(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    exclusion_type = models.CharField(max_length=200, null=True, blank=True)
    c01 = models.CharField(max_length=200, null=True, blank=True)
    c02 = models.CharField(max_length=200, null=True, blank=True)
    c03 = models.CharField(max_length=200, null=True, blank=True)
    c04 = models.CharField(max_length=200, null=True, blank=True)
    c05 = models.CharField(max_length=200, null=True, blank=True)
    c06 = models.CharField(max_length=200, null=True, blank=True)
    c07 = models.CharField(max_length=200, null=True, blank=True)
    c08 = models.CharField(max_length=200, null=True, blank=True)
    c09 = models.CharField(max_length=200, null=True, blank=True)
    c10 = models.CharField(max_length=200, null=True, blank=True)
    class Meta:
        db_table = 'MTO_Exclusion'
 
    def __str__(self):
        return f'Order {self.order_id}'

# ========================================================
# OrderExclusion model
# ========================================================
class OrderExclusion(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    c01 = models.CharField(max_length=200, null=True, blank=True)
    c02 = models.CharField(max_length=200, null=True, blank=True)
    c03 = models.CharField(max_length=200, null=True, blank=True)
    c04 = models.CharField(max_length=200, null=True, blank=True)
    c05 = models.CharField(max_length=200, null=True, blank=True)
    c06 = models.CharField(max_length=200, null=True, blank=True)
    c07 = models.CharField(max_length=200, null=True, blank=True)
    c08 = models.CharField(max_length=200, null=True, blank=True)
    c09 = models.CharField(max_length=200, null=True, blank=True)
    c10 = models.CharField(max_length=200, null=True, blank=True)
    class Meta:
        db_table = 'Order_Exclusion'
 
    def __str__(self):
        return f'Order {self.order_id}'

# ========================================================
# OrderHistory model
# ========================================================
class OrderHistory(models.Model):
    run_date =  models.DateField(null=True, blank=True)
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    order_key = models.CharField(max_length=500)
    delay_days = models.IntegerField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    allocated_fg = models.DecimalField(max_digits=13,decimal_places=3,null=True,blank=True)
    buffer_size = models.IntegerField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=10, null=True, blank=True)
    major_id = models.IntegerField(null=True, blank=True)
    minor_id = models.IntegerField(null=True, blank=True)    
    dept = models.CharField(max_length=200, null=True, blank=True)
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='order_history_master_plant',null=True) 
    cust_code = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='order_history_master_customer', null=True, blank=True)
    cust_name = models.CharField(max_length=200, null=True, blank=True)
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='order_history_master_item')
    vf_order_type = models.CharField(max_length=10)
    order_attributes = models.JSONField(null=True, blank=True)
    line_attributes = models.JSONField(null=True, blank=True)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    customer_attributes = models.JSONField(null=True, blank=True)
    item_attributes = models.JSONField(null=True, blank=True)
    computed_line_attributes = models.JSONField(null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='order_history_master_ccr', null=True, blank=True)

    class Meta:
        db_table = 'Order_History'
 
    def __str__(self):
        return f'Order {self.order_id}'


# ========================================================
# ClosedOrders model
# ========================================================
class ClosedOrders(models.Model):
    closure_date =  models.DateField(null=True, blank=True)
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    order_key = models.CharField(max_length=500)
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='closed_order_master_item')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='closed_order_master_plant') 
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='closed_order_master_dept', null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField()
    pre_order_buffer_size = models.IntegerField(null=True, blank=True)
    post_order_buffer_size = models.IntegerField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=20, null=True, blank=True)
    delay_days = models.IntegerField(null=True, blank=True)
    is_rm_released = models.BooleanField(default=False)
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='closed_order_poogi_major_reason', null=True, blank=True)
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='closed_order_poogi_minor_reason', null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    allocated_fg = models.DecimalField(max_digits=13,decimal_places=3,null=True,blank=True)
    route = models.ForeignKey(RouteMaster,on_delete=models.RESTRICT, related_name='closed_order_master_route', null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='closed_order_master_ccr', null=True, blank=True)
    is_line_finished = models.BooleanField(default=False)
    computed_dd = models.DateField(null=True, blank=True)
    can_finish_from_ui = models.BooleanField(default=False)
    is_manual_buffer_assigned = models.BooleanField(default=False)
    expected_due_date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='closed_order_master_customer', null=True, blank=True)
    order_stage = models.ForeignKey(OrderStageMaster, on_delete=models.RESTRICT, related_name='closed_order_master_order_stage', null=True, blank=True)
    vf_order_type = models.CharField(max_length=10)
    market_based_order_type = models.CharField(max_length=250, null=True, blank=True)
    #Export-Urgent/Export-Normal/Domestic-Urgent/Domestic-Normal these types will be used in MarketLeadTimeMaster
    scheduled_on = models.DateField(null=True, blank=True)
    order_clearance_flag = models.CharField(max_length=1, default='N')
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    wh_code = models.CharField(max_length=100, null=True, blank=True)
    mta_po_date = models.DateField(null=True, blank=True)
    order_attributes = models.JSONField(null=True)
    line_order_attributes = models.JSONField(null=True)
    customer_attributes = models.JSONField(null=True)
    item_attributes = models.JSONField(null=True)
    order_type = models.ForeignKey(OrderTypeMaster, on_delete=models.RESTRICT, related_name='closed_orders_master_order_type', null=True, blank=True) # As of now it is nullable, in future it may change to not null based on discussion
    ot_tag = models.BooleanField(null=True)
    if_tag = models.BooleanField(null=True)
    computed_line_attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'ClosedOrders'

        constraints = [
            models.UniqueConstraint(fields=['order_key'], name='Closed_Orders_PK')
        ]
 
    def __str__(self):
        return f'Order {self.order_id}-{self.line_id}'

# ========================================================
# OrderwiseMultiCCRQty model
# ========================================================
class OrderwiseMultiCCRQty(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='orderwise_mulit_ccr_qty_master_ccr', null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, default = Decimal('0.00'), null=True, blank=True)

    class Meta:
        db_table = 'Orderwise_MultiCCRQty'
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_id"], name="Orderwise_MultiCCRQty_PK"
            )
        ]
 
    def __str__(self):
        return f'Order {self.order_id}-{self.line_id}'

# ========================================================
# OrderwiseProcessingCCR model
# ========================================================
class OrderwiseProcessingCCR(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    processing_ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='orderwise_processing_ccr_master_ccr', null=True, blank=True)
    processing_ccr_position = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'Orderwise_ProcessingCCR'
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_id"], name="Orderwise_ProcessingCCR_PK"
            )
        ]
 
    def __str__(self):
        return f'Order {self.order_id}-{self.line_id}'

# ========================================================
# RouteDetails model
# ========================================================
class RouteDetails(models.Model):
    route = models.ForeignKey(RouteMaster,on_delete=models.RESTRICT, related_name='route_details_master_route')
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='route_details_master_ccr')
    ccr_grp = models.ForeignKey(CCRGroupMaster, on_delete=models.RESTRICT, related_name='route_details_master_ccr_group')
    position = models.IntegerField()
    
    class Meta:
        db_table = 'Route_Details'
        constraints = [
            models.UniqueConstraint(
                fields=["route","ccr","ccr_grp","position"], name="Route_Details_PK"
            )
        ]
 
    def __str__(self):
        return f'Order {self.route}-{self.ccr}-{self.position}'

# ========================================================
# POOGIDailyData model
# ========================================================
class POOGIDailyData(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='poogi_daily_data_poogi_major_reason')
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='poogi_daily_data_poogi_minor_reason')
    reason_assign_date = models.DateField()

    class Meta:
        db_table = 'POOGI_DailyData'
         
    def __str__(self):
        return f'POOGIDailyData {self.order_id}-{self.major_reason}-{self.minor_reason}'

# ========================================================
# POOGIMajorReasonChangeLog model
# ========================================================
class POOGIMajorReasonChangeLog(models.Model):
    major_reason_id = models.IntegerField(primary_key=True)
    major_reason_code = models.CharField(max_length=50)
    major_reason_desc = models.CharField(max_length=200)
    plant = models.ForeignKey(PlantMaster,on_delete=models.RESTRICT, related_name='poogi_major_reason_changelog_master_plant')
    ativity_type = models.CharField(max_length=10)
    updated_on = models.DateField()
    updated_by = models.CharField(max_length=200)
    class Meta:
        db_table = 'POOGI_MajorReason_ChangeLog'
 
    def __str__(self):
        return f'POOGIMajorReasonChangeLog {self.major_reason_id}-{self.major_reason_desc}'

# ========================================================
# POOGIMinorReasonChangeLog model
# ========================================================
class POOGIMinorReasonChangeLog(models.Model):
    minor_reason_id = models.IntegerField(primary_key=True)
    minor_reason_code = models.CharField(max_length=50)
    minor_reason_desc = models.CharField(max_length=200)
    major_reason = models.ForeignKey(POOGIMajorReason,on_delete=models.RESTRICT, related_name='poogi_minor_reason_changelog_poogi_major_reason')
    ativity_type = models.CharField(max_length=10)
    updated_on = models.DateField()
    updated_by = models.CharField(max_length=200)
    class Meta:
        db_table = 'POOGI_MinorReason_ChangeLog'
 
    def __str__(self):
        return f'POOGIMinorReasonChangeLog {self.minor_reason_id}-{self.minor_reason_code}'

# ========================================================
# POOGIReasonPareto model
# ========================================================
class POOGIReasonPareto(models.Model):
    pareto_date = models.DateField()
    major_reason = models.ForeignKey(POOGIMajorReason,on_delete=models.RESTRICT, related_name='poogi_reason_pareto_poogi_major_reason')
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='poogi_reason_pareto_poogi_minor_reason')
    order_id = models.CharField(max_length=200)
    class Meta:
        db_table = 'POOGI_ReasonPareto'
 
    def __str__(self):
        return f'POOGIReasonPareto {self.pareto_date}-{self.major_reason}-{self.minor_reason}'

# ========================================================
# HeaderGroupingMaster model
# ========================================================
class HeaderGroupingMaster(models.Model):
    header_name = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = 'Header_Grouping_Master'
        constraints = [
            models.UniqueConstraint(
                fields=["header_name"], name="Header_Grouping_Master_PK"
            )
        ]

    def __str__(self):
        return f'{self.header_name}'

# ========================================================
# UIReportConfigurations model
# ========================================================
class UIReportConfigurations(models.Model):
    report_name = models.CharField(max_length=200)
    col_code = models.CharField(max_length=200)
    col_position = models.IntegerField()
    header = models.CharField(max_length=200)
    visible = models.BooleanField()
    cell_alignment = models.CharField(max_length=50, blank=True, null=True)
    value = models.CharField(max_length=50, blank=True, null=True)
    short_col_code = models.CharField(max_length=10,null=True)
    header_grouping = models.ForeignKey(HeaderGroupingMaster, on_delete=models.RESTRICT, related_name='ui_report_config_header_grouping_master', null=True)
    data_type= models.CharField(max_length=50, null=True)
    is_color = models.BooleanField(default=False)
    class Meta:
        db_table = 'UI_ReportConfigurations'

        constraints = [
            models.UniqueConstraint(
                fields=["report_name", "col_code"], name="ui_report_config_pk"
            )
        ]
 
    def __str__(self):
        return "{}".format(self.report_name)

# ========================================================
# MarkToBeDeleted model
# ========================================================
class MarkToBeDeleted(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    order_key = models.CharField(primary_key=True ,max_length=500)
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_item')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_plant') 
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_dept')
    due_date = models.DateField(null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField()
    pre_order_buffer_size = models.IntegerField(null=True, blank=True)
    post_order_buffer_size = models.IntegerField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    color = models.CharField(max_length=20, null=True, blank=True)
    delay_days = models.IntegerField(null=True, blank=True)
    is_rm_released = models.BooleanField()
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_poogi_major_reason', null=True, blank=True)
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_poogi_minor_reason', null=True, blank=True)
    total_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    route = models.ForeignKey(RouteMaster,on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_route', null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_ccr', null=True, blank=True)
    is_line_finished = models.BooleanField(default=False)
    computed_dd = models.DateField(null=True, blank=True)
    can_finish_from_ui = models.BooleanField(default=False)
    is_manual_buffer_assigned = models.BooleanField(default=False)
    expected_due_date = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_customer', null=True, blank=True)
    order_stage = models.ForeignKey(OrderStageMaster, on_delete=models.RESTRICT, related_name='mark_to_be_deleted_master_order_stage', null=True, blank=True)
    order_type = models.CharField(max_length=10)
    scheduled_on = models.DateField(null=True, blank=True)
    order_clearance_flag = models.CharField(max_length=1)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    deletion_date = models.DateField()
   
    class Meta:
        db_table = 'Mark_To_Be_Deleted'
 
    def __str__(self):
        return {self.order_id}

# ========================================================
# CloseTypeMaster model
# ========================================================
class CloseTypeMaster(models.Model):
    close_type = models.CharField(max_length=100)
    close_type_code = models.CharField(max_length=100) #is it necessary? : future scopes
    is_valid = models.BooleanField(default=True)

    class Meta:
        db_table = 'Master_Close_Type'   

        constraints = [
            models.UniqueConstraint(
                fields=["close_type"], name="master_close_type_PK"
            )
        ]
    def __str__(self):
        return f'{self.close_type}'

# ========================================================
# OverallBMReport model
# ========================================================
class OverallBMReport(models.Model):
    order_key = models.ForeignKey(OrderData, on_delete=models.RESTRICT, related_name='overall_bm_report_order_data')
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250) 
    color = models.CharField(max_length=20, null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    elapsed_days = models.IntegerField(null=True, blank=True)
    plant_id = models.IntegerField(null=True)
    dept_id = models.IntegerField()
    dept_code = models.CharField(max_length=50)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    pending_ccr_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    allocated_qty = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    major_r_id = models.IntegerField(null=True)
    minor_r_id = models.IntegerField(null=True)
    major_r_desc = models.CharField(max_length=125,null=True)
    minor_r_desc = models.CharField(max_length=125,null=True)
    need_confirmation = models.BooleanField()
    route_name = models.CharField(max_length=200, null=True, blank=True)
    ccr_name = models.CharField(max_length=200, null=True, blank=True)
    item_code = models.CharField(max_length=50, null=True, blank=True)
    item_desc = models.CharField(max_length=200, null=True, blank=True)
    item_group = models.CharField(max_length=50, null=True, blank=True)
    order_type = models.CharField(max_length=50, null=True, blank=True)
    can_finish_from_ui = models.BooleanField()
    is_finished = models.BooleanField()
    delay_days = models.IntegerField(null=True, blank=True)
    plant_name = models.CharField(max_length=200, null=True, blank=True)
    buffer_days = models.IntegerField(null=True, blank=True)
    expected_due_date = models.DateField(null=True, blank=True)
    cust_code = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='overall_bm_report_master_customer', null=True, blank=True)
    cust_name = models.CharField(max_length=200, null=True, blank=True)
    actual_released_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField(null=True, blank=True)
    order_value = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    dept_ageing = models.IntegerField()
    trailing_dept = models.CharField(max_length=200, null=True, blank=True)
    order_attributes = models.JSONField(null=True)
    line_order_attributes = models.JSONField(null=True)
    item_attributes = models.JSONField(null=True, blank=True)
    customer_attributes = models.JSONField(null=True, blank=True)
    close_type = models.ForeignKey(CloseTypeMaster, on_delete=models.RESTRICT, related_name='overall_bm_report_master_close_type', null=True, blank=True)
    oc01 = models.CharField(max_length=200, null=True, blank=True)
    oc02 = models.CharField(max_length=200, null=True, blank=True)
    oc03 = models.CharField(max_length=200, null=True, blank=True)
    oc04 = models.CharField(max_length=200, null=True, blank=True)
    oc05 = models.CharField(max_length=200, null=True, blank=True)
    oc06 = models.CharField(max_length=200, null=True, blank=True)
    oc07 = models.CharField(max_length=200, null=True, blank=True)
    oc08 = models.CharField(max_length=200, null=True, blank=True)
    oc09 = models.CharField(max_length=200, null=True, blank=True)
    oc10 = models.CharField(max_length=200, null=True, blank=True)
    oc11 = models.CharField(max_length=200, null=True, blank=True)
    oc12 = models.CharField(max_length=200, null=True, blank=True)
    oc13 = models.CharField(max_length=200, null=True, blank=True)
    oc14 = models.CharField(max_length=200, null=True, blank=True)
    oc15 = models.CharField(max_length=200, null=True, blank=True)
    oc16 = models.CharField(max_length=200, null=True, blank=True)
    oc17 = models.CharField(max_length=200, null=True, blank=True)
    oc18 = models.CharField(max_length=200, null=True, blank=True)
    oc19 = models.CharField(max_length=200, null=True, blank=True)
    oc20 = models.CharField(max_length=200, null=True, blank=True)
    lc01 = models.CharField(max_length=200, null=True, blank=True)
    lc02 = models.CharField(max_length=200, null=True, blank=True)
    lc03 = models.CharField(max_length=200, null=True, blank=True)
    lc04 = models.CharField(max_length=200, null=True, blank=True)
    lc05 = models.CharField(max_length=200, null=True, blank=True)
    lc06 = models.CharField(max_length=200, null=True, blank=True)
    lc07 = models.CharField(max_length=200, null=True, blank=True)
    lc08 = models.CharField(max_length=200, null=True, blank=True)
    lc09 = models.CharField(max_length=200, null=True, blank=True)
    lc10 = models.CharField(max_length=200, null=True, blank=True)
    lc11 = models.CharField(max_length=200, null=True, blank=True)
    lc12 = models.CharField(max_length=200, null=True, blank=True)
    lc13 = models.CharField(max_length=200, null=True, blank=True)
    lc14 = models.CharField(max_length=200, null=True, blank=True)
    lc15 = models.CharField(max_length=200, null=True, blank=True)
    lc16 = models.CharField(max_length=200, null=True, blank=True)
    lc17 = models.CharField(max_length=200, null=True, blank=True)
    lc18 = models.CharField(max_length=200, null=True, blank=True)
    lc19 = models.CharField(max_length=200, null=True, blank=True)
    lc20 = models.CharField(max_length=200, null=True, blank=True)
    computed_line_attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'Overall_BMReport'

        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_id"], name="overall_bm_report_PK"
            )
        ]

 
    def __str__(self):
        return f'Order {self.order_id}'


# ========================================================
# RejectedMaster model
# ========================================================
class RejectedMaster(models.Model):
    order_id = models.CharField(max_length=200, null=True, blank=True)
    line_id = models.CharField(max_length=250, null=True, blank=True)
    rejection_date = models.DateField()
    reason_code = models.IntegerField()
    c01 = models.CharField(max_length=200, null=True, blank=True)
    c02 = models.CharField(max_length=200, null=True, blank=True)
    c03 = models.CharField(max_length=200, null=True, blank=True)
    c04 = models.CharField(max_length=200, null=True, blank=True)
    c05 = models.CharField(max_length=200, null=True, blank=True)
    class Meta:
        db_table = 'Rejected_Master'
 
    def __str__(self):
        return f'RejectedMaster {self.order_id}-{self.reason_code}'

# ========================================================
# RunAbortReasons model
# ========================================================
class RunAbortReasons(models.Model):
    file = models.ForeignKey(InputFiles, on_delete=models.RESTRICT, related_name='run_abort_reason_input_files')
    run_date_time = models.DateTimeField()
    reason = models.CharField(max_length=512)
    class Meta:
        db_table = 'Run_AbortReasons'
 
    def __str__(self):
        return f'RunAbortReasons {self.file}-{self.run_date_time}-{self.reason}'



# ========================================================
# RunDateTime model
# ========================================================
class RunDateTime(models.Model):
    run_date = models.DateField(null=False, primary_key=True)
    dbr_run_time = models.DateTimeField(null=True)
    bom_run_time = models.DateTimeField(null=True)
    run_date_success = models.DateTimeField(null=True)

    class Meta:
        db_table = 'Run_DateTime'
        get_latest_by = ['run_date']
 
    def __str__(self):
            return f'- {self.run_date}'

# ========================================================
# UserwiseUIReportConfiguration model
# ========================================================

class UserwiseUIReportConfigurations(models.Model):
    userwise_ui_report_config_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=200)
    report_name_id = models.IntegerField()
    columns_settings = models.JSONField()
    updated_on = models.DateTimeField()
    class Meta:
        db_table = 'Userwise_UIReportConfigurations'
 
    def __str__(self):
        return {self.user_name}-{self.report_name}-{self.columns_settings}


# ========================================================
# SupplierMaster model
# ========================================================
class SupplierMaster(models.Model):
    supplier_code = models.CharField(max_length=200)
    supplier_name = models.CharField(max_length=250)
    
    class Meta:
        db_table = 'Master_Supplier'
        constraints = [
            models.UniqueConstraint(
                fields=["supplier_code", "supplier_name"], name="Master_Supplier_PK"
            )
        ]
 
    def __str__(self):
        return f'SupplierMaster {self.supplier_code}-{self.supplier_name}'
        
# ========================================================
# OrderSupplierMapping model
# ========================================================
class ItemSupplierMapping(models.Model):
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='item_supplier_mapping_master_item')
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.RESTRICT, related_name='item_supplier_mapping_master_supplier')

    class Meta:
        db_table = 'Map_Order_Supplier'

    def __str__(self):
        return f'{self.order}-{self.supplier}'

# ========================================================
# Batchwise_Production_OrderAllocation model
# ======================================================== 
class BatchwiseProductionOrderAllocation(models.Model):
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50,null=True, blank=True)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
 
    class Meta:
        db_table = "Batchwise_Production_OrderAllocation"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_item"], name="orderallocation_batchwise_production_pkey"
            )
        ]

    def __str__(self):
        return f"{self.order_id} - {self.line_item}"

# ========================================================
# Calculate_Production_BOMRequirement model
# ======================================================== 
class CalculateProductionBOMRequirement(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=50)
    line_item = models.CharField(max_length=50)
    parent_item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    component_item_code = models.CharField(max_length=50)
    component_requirement = models.DecimalField(max_digits=13, decimal_places=3)
    bom_level = models.IntegerField()
    prev_srl_no = models.CharField(max_length=50, null=True, blank=True)
    item_srl_no = models.CharField(max_length=50)

    class Meta:
        db_table = "Calculate_Production_BOMRequirement"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_item", "srl_no"],
                name="calculate_bom_requirement_production_key",
            )
        ]

    def __str__(self):
        return f"{self.order_id} - {self.line_item} - {self.srl_no}"
    
# ========================================================
# Batchwise_Production_ComponentAllocation model
# ======================================================== 
class BatchwiseProductionComponentAllocation(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    parent_code = models.CharField(max_length=50)
    bom_level = models.IntegerField()
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50, null=True, blank=True)
    simulated_qty = models.DecimalField(max_digits=13, decimal_places=3)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
    item_srl_no = models.CharField(max_length=100)

    class Meta:
        db_table = 'Batchwise_Production_ComponentAllocation'
        constraints = [
            models.UniqueConstraint(fields=['srl_no', 'order_id', 'line_item'], 
            name='componentallocation_batchwise_production_pkey')
        ]

    def __str__(self):
        return f'{self.srl_no} - {self.order_id} - {self.line_item}'

# ========================================================
# Free_RM_Stock model
# ========================================================
class FreeRMStock(models.Model):
    item_code = models.CharField(max_length=50)
    stock_on_hand = models.IntegerField(null=True, blank=True)
    stock_in_qc = models.IntegerField(null=True, blank=True)
    stock_in_transit = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=50)

    class Meta:
        db_table = "Free_RMStock"
        constraints = [
            models.UniqueConstraint(fields=['item_code','username'], name='Free_RMStock_PK')
        ]

    def __str__(self):
        return f'{self.item_code} - {self.username}'


# ========================================================
# Excluded_Orders model
# ========================================================
class ExcludedOrders(models.Model):
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    username = models.CharField(max_length=50)

    class Meta:
        db_table = "Excluded_Orders"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_item","username"], name="pk_excluded_orders"
            )
        ]

    def __str__(self):
        return f"{self.order_id} - {self.line_item} - {self.username}"

# ========================================================
# Simulation_Configuration model
# ========================================================
class SimulationConfiguration(models.Model):

    VF_ORDERTYPE_CHOICES = [
        ('MTA', 'MTA'),
        ('MTO', 'MTO'),
    ]

    NORM_CALC_CHOICES = [
        ('VNeqN', 'VNeqN'),
        ('VNgrN', 'VNgrN'),
    ]

    allocation_category = models.CharField(max_length=100, blank=True, null=True)
    vf_ordertype = models.CharField(max_length=10, choices=VF_ORDERTYPE_CHOICES)
    priority = models.IntegerField()
    bpp_min = models.FloatField(null=True, blank=True)
    bpp_max = models.FloatField(null=True, blank=True)
    cbr_min = models.FloatField(null=True, blank=True)
    cbr_max = models.FloatField(null=True, blank=True)
    dispatch_color = models.CharField(max_length=100, blank=True, null=True)
    norm_calc = models.CharField(max_length=10, choices=NORM_CALC_CHOICES, blank=True, null=True)

    class Meta:
        db_table = "Simulation_Configuration"

# ========================================================
# Batchwise_Production_Simulation_ComponentAllocation model
# ========================================================
class BatchwiseProductionSimulationComponentAllocation(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    parent_code = models.CharField(max_length=50)
    bom_level = models.IntegerField()
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50, null=True, blank=True)
    simulated_qty = models.DecimalField(max_digits=13, decimal_places=3)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
    item_srl_no = models.CharField(max_length=100)

    class Meta:
        db_table = "Batchwise_Production_Simulation_ComponentAllocation"
        constraints = [
            models.UniqueConstraint(
                fields=["srl_no", "order_id", "line_item"],
                name="componentallocation_batchwise_production_simulation_pkey",
            )
        ]

    def __str__(self):
        return f"{self.srl_no} - {self.order_id} - {self.line_item}"

# ========================================================
# OrderBufferMappingRaw model
# ======================================================== 
class OrderBufferMappingRaw(models.Model):
    order_id = models.CharField(max_length=500)
    line_id = models.CharField(max_length=500)
    buffer_id = models.IntegerField(null=True)

    class Meta:
        db_table = 'Map_Order_Buffer_Raw'

    def __str__(self):
        return f'{self.order_id} - {self.line_id} - {self.buffer_id}'

# ========================================================
# Additional_Stock model
# ========================================================
class AdditionalStock(models.Model):

    item_code = models.CharField(max_length=50)
    additional_stock = models.DecimalField(max_digits=13, decimal_places=3)

    class Meta:
        db_table = "Additional_Stock"


# ========================================================
# Simulation_History model
# ========================================================
class SimulationHistory(models.Model):

    run_date = models.DateField()
    username = models.CharField(max_length=50)

    class Meta:
        db_table = "Simulation_History"


# ========================================================
# Batchwise_Procurement_ComponentAllocation model
# ========================================================
class BatchwiseProcurementComponentAllocation(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    parent_code = models.CharField(max_length=50)
    bom_level = models.IntegerField()
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    additional_stock = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50, null=True, blank=True)
    simulated_qty = models.DecimalField(max_digits=13, decimal_places=3)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
    item_srl_no = models.CharField(max_length=100)

    class Meta:
        db_table = "Batchwise_Procurement_ComponentAllocation"
        constraints = [
            models.UniqueConstraint(
                fields=["srl_no", "order_id", "line_item"],
                name="componentallocation_batchwise_procurement_pkey",
            )
        ]

    def __str__(self):
        return f"{self.srl_no} - {self.order_id} - {self.line_item}"

# ========================================================
# DaywiseCoverage_History model
# ========================================================
class DaywiseCoverageHistory(models.Model):

    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    kit_status = models.CharField(max_length=5)
    color = models.CharField(max_length=20, null=True, blank=True)
    planned_release_date = models.DateField(null=True, blank=True)
    order_entry_date = models.DateField()
    customer = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='daywise_coverage_history_master_customer', null=True, blank=True)
    item = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='daywise_coverage_history_master_item') #fg
    run_date = models.DateField(null=False)

    class Meta:
        db_table = "DaywiseCoverage_History"

# ========================================================
# DaywiseCoverage_RMDetails model
# ========================================================
class DaywiseCoverageRMDetails(models.Model):

    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=250)
    item_code = models.ForeignKey(ItemMaster, on_delete=models.RESTRICT, related_name='daywise_coverage_rm_details_master_item') #rm
    rm_req_qty = models.DecimalField(max_digits=13, decimal_places=3)
    rm_available_qty = models.DecimalField(max_digits=13, decimal_places=3)
    rm_allocated = models.DecimalField(max_digits=13, decimal_places=3)

    class Meta:
        db_table = "DaywiseCoverage_RMDetails"

# =======================================================
# ReleaseTrend Model
# =======================================================
class ReleaseTrend(models.Model):
    actual_released_date = models.DateField()
    ccr_id = models.IntegerField()
    plant_id = models.IntegerField(null=True, blank=True)
    dept_id = models.IntegerField(null=True, blank=True)
    delayed_order_count = models.IntegerField(null=True, blank=True)
    weighted_avg_of_delay = models.IntegerField(null=True, blank=True)
    order_attributes = models.JSONField(null=True)
    line_order_attributes = models.JSONField(null=True)
    customer_attributes = models.JSONField(null=True)
    item_attributes = models.JSONField(null=True)
    computed_line_attributes = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'Release_Trend'

    def __str__(self):
        return f"{self.actual_released_date}"


# ======================================================= # 
# CCRUtilizationHistory model 
# ======================================================= #
class CCRUtilizationHistory(models.Model): 
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='ccr_utilization_history_master_ccr') 
    entry_on = models.DateField() 
    produced = models.DecimalField(max_digits=13, decimal_places=2) 
    capacity = models.DecimalField(max_digits=13, decimal_places=2) 
    cumulative_wip_limit = models.IntegerField(null=True, blank=True) 
    wip_released_days = models.IntegerField() 

    class Meta: 
        db_table = "CCR_Utilization_History"

# =======================================================
# Failure_Reasons_Trend model
# =======================================================
class FailureReasonsTrend(models.Model):
    date = models.DateField()
    month = models.CharField(max_length=20)
    category = models.CharField(max_length=15) # Increasing , Decreasing , Neutral
    major_reason = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='failure_reasons_trend_poogi_major_reason', null=True, blank=True)
    minor_reason = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='failure_reasons_trend_poogi_minor_reason', null=True, blank=True)
    order_count = models.IntegerField()

    class Meta:
        db_table = "Failure_Reasons_Trend"

# ========================================================
# MasterMapper model
# ========================================================
class MasterMapper(models.Model):
    master_id = models.IntegerField()
    master_name = models.CharField(max_length=100, null= True, blank=True)
    display_name = models.CharField(max_length=100, null= True, blank=True)
    is_valid = models.BooleanField() 
  
    class Meta:
        db_table = 'Master_Mapper'

    def __str__(self):
        return f'{self.vf_table_name}'

# ========================================================
# MasterDataConfiguration model
# ========================================================
class MDMConfiguration(models.Model):
    master_mapper = models.ForeignKey(MasterMapper, on_delete=models.RESTRICT, related_name='mdm_configuration_master_mapper')
    display_name = models.CharField(max_length=50, null= True, blank=True)
    col_code = models.CharField(max_length=50, null= True, blank=True)
    table_field = models.CharField(max_length=50, null= True, blank=True)
    col_position = models.IntegerField(null= True, blank=True)
    visible = models.BooleanField()
    cell_alignment = models.CharField(max_length=10, null= True, blank=True)
    is_valid = models.BooleanField()
    data_type = models.CharField(max_length=50, null=True, blank=True)
    header = models.CharField(max_length=50, null= True, blank=True)
    
    class Meta:
        db_table = 'MDM_Configuration'

    def __str__(self):
        return f'{self.display_name}'

# ========================================================
# TaskActionStatusMaster model
# ========================================================
class TaskActionStatusMaster(models.Model):
    task_status_id = models.IntegerField(primary_key=True)
    task_status_desc = models.CharField(max_length=1000, null= True, blank=True)

    class Meta:
        db_table = 'Task_ActionStatusMaster'

    def __str__(self):
        return f'{self.task_status_id}-{self.task_status_desc}'

# ========================================================
# TaskActionTypeMaster model
# ========================================================
class TaskActionTypeMaster(models.Model):
    action_type_id = models.IntegerField(primary_key=True)
    action_type_desc = models.CharField(max_length=1000, null= True, blank=True)

    class Meta:
        db_table = 'Task_ActionTypeMaster'

    def __str__(self):
        return f'{self.action_type_id}-{self.action_type_desc}'

# ========================================================
# DraftInstances model
# ========================================================
class DraftInstances(models.Model):
    draft_id = models.CharField(primary_key=True, max_length=200)
    action_type = models.ForeignKey(TaskActionTypeMaster, on_delete=models.RESTRICT, related_name='task_action_type_master_draft_instances')
    user_name = models.CharField(max_length=100)
    user_id =  models.CharField(max_length=100)
    created_on = models.DateTimeField()
    master_mapper = models.ForeignKey(MasterMapper, on_delete=models.RESTRICT, related_name='draft_instances_master_mapper') 
    last_modified_on = models.DateTimeField()
    search_keys = models.CharField(max_length=1000, null= True, blank=True)

    class Meta:
        db_table = 'Draft_Instances'

    def __str__(self):
        return f'{self.draft_id}'

# ========================================================
# BufferMasterDraft model
# ========================================================
class BufferMasterDraft(models.Model):
    row_id = models.IntegerField()
    draft_instance = models.ForeignKey(DraftInstances, on_delete=models.RESTRICT, related_name='draft_buffer_master_draft_instances')
    error = models.CharField(max_length=1000, null= True, blank=True)
    buffer_code = models.CharField(max_length=100)
    buffer_desc = models.CharField(max_length=200)
    buffer_size = models.IntegerField()
    slt = models.IntegerField(null= True, blank=True) 
    mlt = models.IntegerField(null= True, blank=True) 
    is_blue = models.BooleanField(default=False)
    buffer_type = models.ForeignKey(BufferTypeMaster, on_delete=models.RESTRICT, related_name='draft_master_buffer_master_buffer_type') 
    buffer = models.ForeignKey(BufferMaster, on_delete=models.RESTRICT, related_name='draft_master_buffer_master_buffer', null=True, blank=True)
    is_active = models.BooleanField(default=False, null=True, blank= True)

    class Meta:
        db_table = 'Draft_BufferMaster'

    def __str__(self):
        return f'{self.draft_instance}'

# ========================================================
# TaskStatus model
# ========================================================
class TaskInstances(models.Model):
    task_id = models.CharField(max_length=200)
    created_on = models.DateTimeField()
    task_name = models.CharField(max_length=200)
    approver_ids = models.CharField(max_length=300)
    requester_id = models.CharField(max_length=100)
    requester_name = models.CharField(max_length=100)
    task_status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_instances')
    master_mapper = models.ForeignKey(MasterMapper, on_delete=models.RESTRICT, related_name='task_instances_masyter_mapper')
    action_type = models.ForeignKey(TaskActionTypeMaster, on_delete=models.RESTRICT, related_name='task_action_type_master_task_instances')

    class Meta:
        db_table = 'Task_Instances'

    def __str__(self):
        return f'{self.task_id}'

# ========================================================
# TaskBufferMaster model
# ========================================================
class TaskBufferMaster(models.Model):
    task_instance = models.ForeignKey(TaskInstances, on_delete=models.RESTRICT, related_name='task_buffer_master_task_instances')
    buffer_code = models.CharField(max_length=100)
    buffer_desc = models.CharField(max_length=200)
    buffer_size = models.IntegerField()
    slt = models.IntegerField(null= True, blank=True) 
    mlt = models.IntegerField(null= True, blank=True) 
    is_blue = models.BooleanField(default=False)
    buffer = models.ForeignKey(BufferMaster, on_delete=models.RESTRICT, related_name='task_buffer_master_buffer_master', null=True, blank=True)
    buffer_type = models.ForeignKey(BufferTypeMaster, on_delete=models.RESTRICT, related_name='task_master_buffer_master_buffer_type')    
    status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_buffer_master')
    is_active = models.BooleanField(default=False, null=True, blank=True)
    comments = models.CharField(max_length=500, null= True, blank=True)
    is_approved = models.BooleanField(default=False)
    approver_id = models.IntegerField(null= True, blank=True)
    approver_name = models.CharField(max_length=100, null= True, blank=True)
    approved_on = models.DateTimeField(null= True, blank=True)  

    class Meta:
        db_table = 'Task_BufferMaster'

    def __str__(self):
        return f'{self.buffer_code}'

# ========================================================
# TaskCCRMaster model
# ======================================================== 
class TaskCCRMaster(models.Model):
    task_instance = models.ForeignKey(TaskInstances, on_delete=models.RESTRICT, related_name='task_ccr_master_task_instances')
    ccr_code = models.CharField(max_length=100)
    ccr_name = models.CharField(max_length=200)    
    capacity_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    working_hrs_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    scheduling_horizon = models.IntegerField()
    fol_horizon = models.IntegerField()
    residual_buffer = models.DecimalField(max_digits=13, decimal_places=2) 
    ccr_attr1 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr2 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr3 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr4 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr5 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr6 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr7 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr8 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr9 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr10 = models.CharField(max_length=200, null= True, blank= True)
    is_valid = models.BooleanField(default=True)
    ccr_group = models.ForeignKey(CCRGroupMaster, on_delete=models.RESTRICT, related_name='ccr_task_master_ccr_group_master')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='ccr_task_master_plant_master')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='ccr_task_master_dept_master')
    cumulative_wip_limit = models.IntegerField(null=True, blank=True)
    status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_ccr_master')
    comments = models.CharField(max_length=500, null= True, blank=True)
    is_approved = models.BooleanField(default=False)
    approver_id = models.IntegerField(null= True, blank=True)
    approver_name = models.CharField(max_length=100, null= True, blank=True)
    approved_on = models.DateTimeField(null= True, blank=True)
    ccr = models.ForeignKey(CCRMaster,on_delete=models.RESTRICT, related_name='task_ccr_master_ccr_master', null=True, blank=True)
    is_active = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        db_table = 'Task_CCRMaster'

    def __str__(self):
        return f'{self.task_instance}'

# ========================================================
# CCRMasterDraft model
# ========================================================
class CCRMasterDraft(models.Model):
    row_id = models.IntegerField()
    draft_instance = models.ForeignKey(DraftInstances, on_delete=models.RESTRICT, related_name='draft_ccr_master_draft_instances')
    error = models.CharField(max_length=1000, null= True, blank=True)
    ccr_code = models.CharField(max_length=100)
    ccr_name = models.CharField(max_length=200)    
    capacity_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    working_hrs_per_day = models.DecimalField(max_digits=13, decimal_places=2)
    scheduling_horizon = models.IntegerField()
    fol_horizon = models.IntegerField()
    residual_buffer = models.DecimalField(max_digits=13, decimal_places=2) 
    ccr_attr1 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr2 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr3 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr4 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr5 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr6 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr7 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr8 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr9 = models.CharField(max_length=200, null= True, blank= True)
    ccr_attr10 = models.CharField(max_length=200, null= True, blank= True)
    ccr_group = models.ForeignKey(CCRGroupMaster, on_delete=models.RESTRICT, related_name='ccr_draft_master_ccr_group_master')
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='ccr_draft_master_plant_master')
    dept = models.ForeignKey(DeptMaster, on_delete=models.RESTRICT, related_name='ccr_draft_master_dept_master')
    cumulative_wip_limit = models.IntegerField(null=True, blank=True)
    ccr = models.ForeignKey(CCRMaster,on_delete=models.RESTRICT, related_name='draft_ccr_master_ccr_master', null=True, blank=True)
    is_active = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        db_table = 'Draft_CCRMaster'

    def __str__(self):
        return f'{self.draft_instance}'


# ========================================================
# TaskPOOGIMajorReason model
# ========================================================
class TaskPoogiMajorReason(models.Model):
    task_instance = models.ForeignKey(TaskInstances, on_delete=models.RESTRICT, related_name='task_poogi_major_reason_task_instances')
    major_reason_code = models.CharField(max_length=50)
    major_reason_desc = models.CharField(max_length=200)
    plant = models.ForeignKey(PlantMaster,on_delete=models.RESTRICT, related_name='task_poogi_major_reason_master_plant', null=True, blank= True)
    status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_poogi_major_reason')
    comments = models.CharField(max_length=500, null= True, blank=True)
    is_approved = models.BooleanField(default=False)
    approver_id = models.IntegerField(null= True, blank=True)
    approver_name = models.CharField(max_length=100, null= True, blank=True)
    approved_on = models.DateTimeField(null= True, blank=True)
    is_existing = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_updated = models.BooleanField(default=False)
    major = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='task_poogi_major_reason_Poogi_major_reason', null=True, blank= True)

    class Meta:
        db_table = 'Task_PoogiMajorReason'
         
    def __str__(self):
        return f'TaskPoogiMajorReason {self.major_reason_desc}'

# ========================================================
# TaskPOOGIMinorReason model
# ========================================================
class TaskPoogiMinorReason(models.Model):
    task_major_reason = models.ForeignKey(TaskPoogiMajorReason, on_delete=models.RESTRICT, related_name='task_poogi_minor_reason_task_poogi_major_reason')
    minor_reason_code = models.CharField(max_length=50)
    minor_reason_desc = models.CharField(max_length=200)
    status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_poogi_minor_reason')
    comments = models.CharField(max_length=500, null= True, blank=True)
    is_approved = models.BooleanField(default=False)
    approver_id = models.IntegerField(null= True, blank=True)
    approver_name = models.CharField(max_length=100, null= True, blank=True)
    approved_on = models.DateTimeField(null= True, blank=True)
    is_deleted = models.BooleanField(default= False)
    is_updated = models.BooleanField(default=False)
    minor = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='task_poogi_minor_reason_Poogi_minor_reason', null=True, blank= True)

    class Meta:
        db_table = 'Task_PoogiMinorReason'
 
    def __str__(self):
        return f'TaskPoogiMinorReason {self.minor_reason_desc}'

# ========================================================
# PoogiMajorReasonDraft model
# ========================================================
class PoogiMajorReasonDraft(models.Model):
    row_id = models.IntegerField()
    draft_instance = models.ForeignKey(DraftInstances, on_delete=models.RESTRICT, related_name='draft_poogi_major_reason_draft_instances')
    error = models.CharField(max_length=1000, null= True, blank=True)
    major_reason_code = models.CharField(max_length=50)
    major_reason_desc = models.CharField(max_length=200)
    plant = models.ForeignKey(PlantMaster,on_delete=models.RESTRICT, related_name='draft_poogi_major_reason_master_plant', null=True, blank= True)
    is_existing = models.BooleanField(default= False)
    is_deleted = models.BooleanField(default= False)
    is_updated = models.BooleanField(default=False)
    major = models.ForeignKey(POOGIMajorReason, on_delete=models.RESTRICT, related_name='draft_poogi_major_reason_Poogi_major_reason', null=True, blank= True)
    
    class Meta:
        db_table = 'Draft_PoogiMajorReason' 

    def __str__(self):
        return f'{self.draft_instance}'

# ========================================================
# PoogiMinorReasonDraft model
# ========================================================
class PoogiMinorReasonDraft(models.Model):
    row_id = models.IntegerField()
    major_reason_draft = models.ForeignKey(PoogiMajorReasonDraft, on_delete=models.RESTRICT, related_name='draft_poogi_minor_reason_draft_poogi_major_reason')
    error = models.CharField(max_length=1000, null= True, blank=True)
    minor_reason_code = models.CharField(max_length=50)
    minor_reason_desc = models.CharField(max_length=200)
    is_deleted = models.BooleanField(default= False)
    is_updated = models.BooleanField(default=False)
    minor = models.ForeignKey(POOGIMinorReason, on_delete=models.RESTRICT, related_name='draft_poogi_minor_reason_Poogi_minor_reason', null=True, blank= True)

    class Meta:
        db_table = 'Draft_PoogiMinorReason'

    def __str__(self):
        return f'{self.major_reason_draft}'

# ========================================================
# TaskCalendarMaster model
# ========================================================
class TaskCalendarMaster(models.Model):
    task_instance = models.ForeignKey(TaskInstances, on_delete=models.RESTRICT, related_name='task_calendar_holiday_task_instances')
    is_week_day = models.BooleanField(default=False)
    day_of_week = models.JSONField(default=list, null=True, blank=True)
    holiday_start_date = models.DateField(null= True, blank= True)
    holiday_end_date = models.DateField(null= True, blank= True)
    is_working_day = models.BooleanField(default= False)    
    description = models.CharField(max_length=200)
    repeatation_bucket = models.CharField(max_length=100, null= True, blank= True)
    repeat_duration_in_weeks = models.IntegerField(null= True, blank= True)    
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='task_calendar_holiday_master_plant')
    ccr_id = ArrayField(models.IntegerField(), default=list)
    status = models.ForeignKey(TaskActionStatusMaster, on_delete=models.RESTRICT, related_name='task_action_status_master_task_calendar_holiday')
    comments = models.CharField(max_length=500, null= True, blank=True)
    is_approved = models.BooleanField(default=False)
    approver_id = models.IntegerField(null= True, blank=True)
    approver_name = models.CharField(max_length=100, null= True, blank=True)
    approved_on = models.DateTimeField(null= True, blank=True)
    is_updated = models.BooleanField(default=False, null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    plant_holiday = models.ForeignKey(PlantHolidayList, on_delete=models.RESTRICT,related_name='task_calendar_master_plant_holiday_list', null=True, blank=True)

    class Meta:
        db_table = 'Task_CalendarMaster'   
 
    def __str__(self):
        return f'{self.task_instance}'

# ========================================================
# CalendarMasterDraft model
# ========================================================
class CalendarMasterDraft(models.Model):
    row_id = models.IntegerField()
    draft_instance = models.ForeignKey(DraftInstances, on_delete=models.RESTRICT, related_name='draft_calendar_master_draft_instances')
    error = models.CharField(max_length=1000, null= True, blank=True)
    is_week_day = models.BooleanField(default=False)
    day_of_week = models.JSONField(default=list, null=True, blank=True)
    holiday_start_date = models.DateField(null= True, blank= True)
    holiday_end_date = models.DateField(null= True, blank= True)
    is_working_day = models.BooleanField(default= False)    
    description = models.CharField(max_length=200)
    repeatation_bucket = models.CharField(max_length=100, null= True, blank= True)
    repeat_duration_in_weeks = models.IntegerField(null= True, blank= True)
    plant = models.ForeignKey(PlantMaster, on_delete=models.RESTRICT, related_name='draft_calendar_master_master_plant')
    ccr_id = ArrayField(models.IntegerField(), null=True, blank=True, default=list)
    is_updated = models.BooleanField(default=False, null=True, blank=True)
    is_deleted = models.BooleanField(default=False, null=True, blank=True)
    plant_holiday = models.ForeignKey(PlantHolidayList, on_delete=models.RESTRICT, related_name='draft_calendar_master_plant_holiday_list', null=True, blank=True)
    
    class Meta:
        db_table = 'Draft_CalendarMaster'

    def __str__(self):
        return f'{self.draft_instance}'

# ==================================================================
# MTOPermissionType model
# ==================================================================
class MTOPermissionType(models.Model):
    type_id = models.IntegerField(primary_key= True)
    type_name = models.CharField(max_length=250)
    sequence = models.IntegerField()
    mapped_attribute_type = models.CharField(max_length=50,null=True,blank = True)

    class Meta:
        db_table = 'MTO_Permission_Type'

    def __str__(self):
        return f'{self.sequence} - {self.type_name}'

# =====================================================================
# MTOPermissionHeader model
# =====================================================================
class MTOPermissionHeader(models.Model):
    header_id = models.IntegerField(primary_key=True)
    mto_permission_type = models.ForeignKey(MTOPermissionType, on_delete=models.RESTRICT, related_name='mto_permission_header_mto_permission_type')
    header_name = models.CharField(max_length=250)
    level = models.IntegerField()
    mapped_attribute = models.CharField(max_length=50,null=True,blank = True)
    
    class Meta:
        db_table = 'MTO_Permission_Header'

    def __str__(self):
        return f'{self.mto_permission_type} - {self.level} - {self.header_name}'

# ==================================================================
# MTOPermissionDetails model
# ==================================================================
class MTOPermissionDetails(models.Model):
    permission_details_id = models.IntegerField(primary_key=True)
    mto_permission_type = models.ForeignKey(MTOPermissionType, on_delete=models.RESTRICT, related_name='mto_permission_details_mto_permission_type')
    level1 = models.CharField(max_length=500)
    level2 = models.CharField(max_length=500, null = True, blank = True)
    level3 = models.CharField(max_length=500, null = True , blank = True)

    class Meta:
        db_table = 'MTO_Permission_Details'
        constraints = [
            models.UniqueConstraint(
                fields=["level1", "level2", "level3"], name="pk_mto_permission_details"
            )
        ]

    def __str__(self):
        return f'{self.permission_details_id} - {self.details}'

# ========================================================
# RunAbortReasonsTable
# ========================================================

class RunAbortReasonsInputTable(models.Model):
    run_date_time = models.DateTimeField()
    reason = models.CharField(max_length=512)
    table = models.ForeignKey(InputTableList,on_delete=models.DO_NOTHING,related_name='abort_reasons_input_table')

    class Meta:
        db_table = 'Run_AbortReasons_InputTable'

    def __str__(self):
        return f'{self.run_date_time} - {self.reason} - {self.table}'

# =======================================================
# BOM Tables
# ======================================================== 

# ========================================================
# Projection_Order model
# ========================================================
class ProjectionOrder(models.Model):
    order_id = models.CharField(max_length=200)
    order_plant_code = models.CharField(max_length=250, primary_key=True)
    cust_code = models.ForeignKey(CustomerMaster, on_delete=models.RESTRICT, related_name='projection_order_master_customer', null=True, blank=True)
    cust_name = models.CharField(max_length=50, null=True, blank=True)
    customer_expected_date = models.DateField()
    order_date = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
 
    class Meta:
        db_table = "Projection_Order"
    def __str__(self):
        return f'BOM {self.order_id}'

# ========================================================
# Projection_OrderDetails model
# ========================================================
class ProjectionOrderDetails(models.Model):
    order_plant_code = models.ForeignKey(ProjectionOrder, on_delete=models.CASCADE, related_name="projection_order_code", related_query_name="projection_order_code", null=False)
    order_line_srl_no = models.CharField(max_length=250, null=False)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=13, decimal_places=3)
    dispatch_quantity = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    balance_order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    order_value = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    vf_order_type = models.CharField(max_length=10)
    due_date = models.DateField(null=True, blank=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=2, null=True, blank=True)
    allocated_fg = models.DecimalField(max_digits=13,decimal_places=3,null=True,blank=True)
    order_id = models.CharField(max_length=250, null=False)
    
    class Meta:
        db_table = "Projection_Order_Details"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "line_item"], name="pk_projectionorderdata"
            )
        ]
    def __str__(self):
        return f"{self.order_id} - {self.line_item}"


# ========================================================
# PendingOrder model
# ========================================================
class PendingOrder(models.Model):
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    identifier = models.CharField(max_length=50, null=True, blank=True)       
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    type = models.CharField(max_length=50) 
 
    class Meta:
        db_table = 'PendingOrder'
        constraints = [
            models.UniqueConstraint(fields=['item_code', 'plant_code', 'type'], name='pending_Order_pkey')
        ]
 
    def __str__(self):
        return f'{self.item_code} - {self.plant_code} - {self.type}'
    

# ========================================================
# BOM_HDR model
# ========================================================
class BOMHeader(models.Model):
    bom_srl_no = models.DecimalField(max_digits=13, decimal_places=0, primary_key=True)
    plant_code = models.CharField(max_length=50)
    parent_item_code = models.CharField(max_length=50)
    parent_uom = models.CharField(max_length=50, null=True, blank=True)
    parent_qty = models.DecimalField(max_digits=13, decimal_places=0)
    is_active = models.BooleanField()
    from_lot_no = models.CharField(max_length=50, null=True, blank=True)
    to_lot_no = models.CharField(max_length=50, null=True, blank=True)
    alternate_bom = models.BooleanField(null=True, blank=True)
    batch_size = models.CharField(max_length=50, null=True, blank=True)
 
    class Meta:
        db_table = 'BOM_HDR'
 
    def __str__(self):
        return f'BOM {self.bom_srl_no}'
    

# ========================================================
# BOM_DTL model
# ======================================================== 
class BOMDetail(models.Model):
    bom_srl_no = models.ForeignKey(BOMHeader, on_delete=models.CASCADE, related_name="bom_headers", related_query_name="bom_header")
    item_srl_no = models.DecimalField(max_digits=13, decimal_places=0)
    component_item_code = models.CharField(max_length=50)
    component_uom = models.CharField(max_length=50, null=True, blank=True)
    conversion = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)
    component_qty = models.DecimalField(max_digits=30, decimal_places=13)
    fixed_multiplier_flag = models.BooleanField(null=False,default = False)

 
    class Meta:
        db_table = 'BOM_DTL'
        constraints = [
            models.UniqueConstraint(fields=['bom_srl_no', 'item_srl_no'], name='PK_BOMSrlNO_ItemSrlNo')
        ]
 
    def __str__(self):
        return f'{self.bom_srl_no} - {self.item_srl_no}'
    
    
# ========================================================
# Batchwise_OrderAllocation model
# ======================================================== 
class BatchwiseOrderAllocation(models.Model):
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
    purchase_gap = models.DecimalField(max_digits=13, decimal_places=3, null = True)
 
    class Meta:
        db_table = 'Batchwise_OrderAllocation'
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'line_item'], name='orderallocation_batchwise_pkey')
        ]
 
    def __str__(self):
        return f'{self.order_id} - {self.line_item}'
            
# ========================================================
# Calculate_BOMRequirement model
# ======================================================== 
class CalculateBOMRequirement(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=50)
    line_item = models.CharField(max_length=50)
    parent_item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    component_item_code = models.CharField(max_length=50)
    component_requirement = models.DecimalField(max_digits=13, decimal_places=3)
    bom_level = models.IntegerField()
    prev_srl_no = models.CharField(max_length=50, null=True, blank=True)
    item_srl_no = models.CharField(max_length=50)

    class Meta:
        db_table = 'Calculate_BOMRequirement'
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'line_item', 'srl_no'], name='calculate_bom_requirement_key')
        ]

    def __str__(self):
        return f'{self.order_id} - {self.line_item} - {self.srl_no}'

# ========================================================
# Batchwise_ComponentAllocation model
# ======================================================== 
class BatchwiseComponentAllocation(models.Model):
    srl_no = models.CharField(max_length=50)
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    parent_code = models.CharField(max_length=50)
    bom_level = models.IntegerField()
    order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3)
    identifier = models.CharField(max_length=50, null=True, blank=True)
    simulated_qty = models.DecimalField(max_digits=13, decimal_places=3)
    open_po = models.DecimalField(max_digits=13, decimal_places=3)
    item_srl_no = models.CharField(max_length=100)
    purchase_gap = models.DecimalField(max_digits=13, decimal_places=3, null=True)

    class Meta:
        db_table = 'Batchwise_ComponentAllocation'
        constraints = [
            models.UniqueConstraint(fields=['srl_no', 'order_id', 'line_item'], name='componentallocation_batchwise_pkey')
        ]

    def __str__(self):
        return f'{self.srl_no} - {self.order_id} - {self.line_item}'

# ========================================================
# EcoStock model
# ========================================================
class EcoStock(models.Model):
    item_code = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name="sku_master", related_query_name="sku_master")
    plant_code = models.ForeignKey(PlantMaster, on_delete=models.CASCADE, related_name="master_plant", related_query_name="master_plant")
    identifier = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.DecimalField(max_digits=13, decimal_places=3)
    type = models.CharField(max_length=50)
    allocated_so_items = models.CharField(max_length=50, null=True, blank=True)
 
    class Meta:
        db_table = 'EcoStock'
        constraints = [
            models.UniqueConstraint(
                fields=["item_code", "plant_code", "type","allocated_so_items","identifier"], name="PK_eco_stock"
            )
        ]
 
    def __str__(self):
        return f'- {self.item_code} - {self.plant_code} - {self.type}'

# ========================================================
# ReportConfiguration model
# ========================================================
class ReportConfiguration(models.Model):
    report_name = models.CharField(max_length=50)
    flag = models.CharField(max_length=50)
    start = models.IntegerField(default=0)
    end = models.IntegerField(default=0)
    desc = models.CharField(max_length=500)
    colors = models.CharField(max_length=200, null=True, blank=True)
    json_value = models.JSONField(null=True)
 
    class Meta:
        db_table = 'Report_Configuration'
 
    def __str__(self):
            return f'- {self.report_name}'

# ========================================================
# AttributeConfiguration model
# ========================================================
class AttributeConfiguration(models.Model):
    attribute_type = models.CharField(max_length=50)
    col_code = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10)
    attribute_name = models.CharField(max_length=50)
    filter_sequence = models.IntegerField()
    is_active = models.BooleanField(default=True)
    is_number = models.BooleanField(default=False)
 
    class Meta:
        db_table = 'Attribute_Config'
        constraints = [
                models.UniqueConstraint(
                fields=["attribute_type", "col_code", "short_name", "attribute_name", "filter_sequence"], name="PK_attr_config"
            )
        ]
 
    def __str__(self):
            return f'- {self.attribute_type}-{self.attribute_name}'

# ========================================================
# Master_ItemLocation model
# ======================================================== 
class Master_ItemLocation(models.Model):
    item_code = models.CharField(max_length=100)
    location_code = models.CharField(max_length=100)
    parent_code = models.CharField(max_length=100)

    class Meta:
        db_table = 'Master_ItemLocation'
        constraints = [
            models.UniqueConstraint(fields=['item_code', 'location_code'], 
            name='Master_Item_Location_pkey')
        ]

    def __str__(self):
        return f'{self.item_code} - {self.location_code} - {self.parent_code}'


# =======================================================
# Master_ItemProductionBatchsize model
# =======================================================
class MasterItemProductionBatchsize(models.Model):
    item_code = models.CharField(max_length=50)
    batch_size = models.DecimalField(max_digits=13, decimal_places=3) 

    class Meta:
        db_table = 'Master_ItemProductionBatchsize'

        constraints = [
            models.UniqueConstraint(fields=['item_code','batch_size'], name='master_item_production_batchsize_pkey')
        ]
    def __str__(self):
        return f'{self.item_code}'

# =======================================================
# Allocation_Sequence Model
# =======================================================
class AllocationSequence(models.Model):
    order_id = models.CharField(max_length=200)
    line_id = models.CharField(max_length=200)
    priority = models.IntegerField()
    sequence = models.IntegerField()

    class Meta:
        db_table = 'Allocation_Sequence'

        constraints = [
            models.UniqueConstraint(fields=['order_id','line_id'],name='allocation_sequence_pkey')
        ]

    def __str__(self):
        return f"{self.order_id} - {self.line_id}"


# =======================================================
# BOMSetting Model
# =======================================================
class BOMSetting(models.Model):
    flag = models.CharField(max_length=200, primary_key=True)
    value = models.IntegerField(null=False)
    description = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'BOM_Setting'

        constraints = [
         models.UniqueConstraint(fields=['flag'],name='bom_setting_pkey')   
        ]

    def __str__(self):
        return f"{self.flag }"


# =======================================================
# MasterItemTransportBatchSize Model
# =======================================================
class MasterItemTransportBatchSize(models.Model):
    item_code = models.CharField(max_length=200)
    batch_transport = models.DecimalField(max_digits=13, decimal_places=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['item_code', 'batch_transport'], name='master_item_transport_batchwise_pkey')
        ]
        db_table = 'Master_ItemTransportBatchSize'

    def __str__(self):
        return f"{self.item_code} - {self.batch_transport}"

# =======================================================
# MasterCategorywiseLocationLevel Model
# =======================================================
class Master_CategorywiseLocationLevel(models.Model):
    location_category_id = models.AutoField(primary_key=True)
    location_type = models.CharField(max_length=100)
    location_level = models.IntegerField()
    stock_netoff_across_level = models.BooleanField(default=False)


    class Meta:
        db_table = 'Master_CategorywiseLocationLevel'

    def __str__(self):
        return f"{self.location_category_id} - {self.location_type}"

# =======================================================
# MasterLocation Model
# =======================================================
class MasterLocation(models.Model):
    location_id = models.IntegerField(primary_key=True)
    location_code = models.CharField(max_length=100)
    location_name = models.CharField(max_length=200)
    location_level = models.IntegerField()

    class Meta:
        db_table = 'Master_Location'

    def __str__(self):
        return f"{self.location_code} - {self.location_name}"

# =======================================================
# ProjectionOrderRaw Model
# =======================================================
class ProjectionOrderRaw(models.Model):
    order_id = models.CharField(max_length=200)
    order_plant_code = models.CharField(max_length=250, primary_key=True)
    cust_name = models.CharField(max_length=50, null=True)
    customer_expected_date = models.DateField()
    order_date = models.CharField(max_length=50)
    plant_code = models.CharField(max_length=50)
    cust_code = models.ForeignKey(CustomerMaster, null=True, on_delete=models.RESTRICT, related_name="projection_order_raw_customer_master")

    class Meta:
        db_table = 'Projection_Order_Raw'

    def __str__(self):
        return f"{self.order_id}"

# =======================================================
# ProjectionOrderDetailsRaw Model
# =======================================================
class ProjectionOrderDetailsRaw(models.Model):
    order_line_srl_no = models.CharField(max_length=250, null=False)
    order_plant_code = models.ForeignKey(ProjectionOrderRaw, on_delete=models.CASCADE, related_name="projection_order_raw", related_query_name="projection_order_raw", null=False)
    line_item = models.CharField(max_length=200)
    item_code = models.CharField(max_length=50)
    quantity =	models.DecimalField(max_digits=13, decimal_places=3)
    dispatch_quantity = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    balance_order_qty = models.DecimalField(max_digits=13, decimal_places=3)
    order_value = models.DecimalField(max_digits=13, decimal_places=3, null=True) 
    order_id = 	models.CharField(max_length=200)
    vf_order_type = models.CharField(max_length=200)
    due_date = models.DateField(null=True)
    bpp = models.DecimalField(max_digits=13, decimal_places=3, null=True) 

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'line_item'], name='projection_order_details_raw_pkey')
        ]
        db_table = 'Projection_Order_Details_Raw'

    def __str__(self):
        return f"{self.order_id}"

# =======================================================
# UnscheduleOrderData Model
# =======================================================
class UnscheduleOrderData(models.Model):
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    bpp = models.DecimalField(max_digits=13, decimal_places=3, null=True)
    due_date = models.DateField(null=True)
    release_date = models.DateField(null=True, blank=True)
    vf_order_type = models.CharField(max_length=200)

    class Meta:
        db_table = 'Unschedule_OrderData'

    def __str__(self):
        return f"{self.order_id}"


# ========================================================
# Closed_Order_WIPDetails
# ========================================================
class Closed_Order_WIPDetails(models.Model):
    order_key = models.CharField(max_length=500)
    item_code = models.CharField(max_length=50)
    wip_on_hand = models.DecimalField(max_digits=13, decimal_places=3,null=True)
    dept = models.ForeignKey(DeptMaster,on_delete=models.RESTRICT,related_name='closed_order_wip_master_dept')
    mfg_balance = models.DecimalField(max_digits=13,decimal_places=3,null=True)
    entered_on = models.DateField()
    exited_on = models.DateField()
    elapsed_days = models.IntegerField(default=0)
    dispatch_balance = models.DecimalField(max_digits=13,decimal_places=3,null=True)

    class Meta:
        db_table = 'Closed_Order_WIPDetails'

    def __str__(self):
        return f'{self.order}'


# ========================================================
# OrderBatchDetails
# ========================================================
class OrderBatchDetails(models.Model):
    order_key = models.CharField(max_length=500)
    item_code = models.CharField(max_length=50,null=True)
    batch_no = models.CharField(max_length=500,null=True,blank=True)
    date_of_posting = models.DateField(null=True)

    class Meta:
        db_table = 'Order_Batch_Details'

        constraints = [
            models.UniqueConstraint(fields=['order_key', 'item_code','batch_no'], name='order_batch_details_pk')
        ]
    
    def __str__(self):
        return f'{self.order_key} - {self.item_code}'


# ========================================================
# MapReportAttributeType
# ========================================================
class MapReportAttributeType(models.Model):
    report_name = models.CharField(max_length=500)
    attribute_types = ArrayField(models.CharField(max_length=50))

    class Meta:
        db_table = 'Map_Report_AttributeType'
        constraints = [
            models.UniqueConstraint(fields=['report_name'], name='map_report_attribute_type')
        ]
    
    def __str__(self):
        return f'{self.report_name}'
    
# ========================================================
# BMReport_Analytics
# ========================================================
class BMReportAnalytics(models.Model):
    type = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    today_count = models.IntegerField(null=True)
    yesterday_count = models.IntegerField(null=True)
    dept_id = models.IntegerField(null=True)
    

    class Meta:
        db_table = 'BMReport_Analytics'
        constraints = [
            models.UniqueConstraint(fields=['type', 'color'], name='bm_report_analytics_pk')
        ]
    
    def __str__(self):
        return f'{self.type} - {self.color}'

# ========================================================
# RuntimeReports
# ========================================================
class RuntimeReports(models.Model):
    reportName = models.CharField(max_length=50)
    query = models.TextField()
    headerList = models.TextField()
    fileName = models.CharField(max_length=50)
    destinationFolder = models.CharField(max_length=500)
    compression = models.BooleanField()
    extension = models.CharField(max_length=10)
    delimiter = models.CharField(max_length=10, null=True)  
    deleteOldFile = models.BooleanField()
    active = models.BooleanField()
    lastGeneratedFileName = models.CharField(max_length=50, null=True)
    module_name =  models.CharField(max_length=50, null= False, blank = False,default='MTO')

    class Meta:
            db_table = 'RuntimeReports'
            
class EmailDetails(models.Model):
    id = models.BigAutoField(primary_key=True)
    email_from = models.TextField(null=False)
    password = models.TextField(null=False)
    email_to = models.TextField(null=False)
    cc = models.TextField(blank=True, null=True) 
    type = models.TextField(null=False)
    active = models.BooleanField(default=True)
    subject = models.TextField(null=False)
    template = models.TextField(null=False)

    class Meta:
        db_table = 'EmailDetails'  

    def __str__(self):
        return f"{self.email_from}  {self.email_to}"


# ========================================================
# BatchwiseAlternateComponentAllocation
# ========================================================
class BatchwiseAlternateComponentAllocation(models.Model):
    id = models.BigAutoField(primary_key=True)
    srl_no = models.CharField(max_length=50, unique=True)  
    order_id = models.CharField(max_length=200, unique=True)  
    line_item = models.CharField(max_length=200, unique=True) 
    item_code = models.CharField(max_length=50, null=False)  
    plant_code = models.CharField(max_length=50, null=False) 
    parent_code = models.CharField(max_length=50, null=False)
    bom_level = models.IntegerField(null=False)  
    order_qty = models.DecimalField(max_digits=13, decimal_places=3, null=False) 
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3, null=False)
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3, null=False) 
    identifier = models.CharField(max_length=50, null=False)  
    simulated_qty = models.DecimalField(max_digits=13, decimal_places=3, null=False)
    open_po = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    item_srl_no = models.CharField(max_length=100, null=False)  

    class Meta:
        db_table = 'Batchwise_Alternate_ComponentAllocation'

    def __str__(self):
        return f'{self.order_id} - {self.line_item}'


# ========================================================
# BatchwiseAlternateOrderAllocation
# ========================================================
class BatchwiseAlternateOrderAllocation(models.Model):
    id = models.BigAutoField(primary_key=True)
    srl_no = models.CharField(max_length=50, unique=True)  
    order_id = models.CharField(max_length=200, unique=True) 
    line_item = models.CharField(max_length=200, unique=True)  
    item_code = models.CharField(max_length=50, null=False)  
    plant_code = models.CharField(max_length=50, null=False)  
    order_qty = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    stock_on_hand = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3, null=False) 
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    order_remaining = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    identifier = models.CharField(max_length=50, null=False) 
    open_po = models.DecimalField(max_digits=13, decimal_places=3, null=False)  

    class Meta:
        db_table = 'Batchwise_Alternate_OrderAllocation'

    def __str__(self):
        return f'{self.order_id} - {self.line_item}'


# ========================================================
# MapAltcodewiseAllocation
# ========================================================
class MapAltcodewiseAllocation(models.Model):
    plant_code = models.CharField(max_length=50, null=False)
    item_codes = ArrayField(models.CharField(max_length=50), null=False)  
    class Meta:
        db_table = 'Map_Altcodewise_Allocation'
        constraints = [
            models.UniqueConstraint(fields=['plant_code', 'item_codes'], name='map_alt_code_wise_allocation_pk')
        ]
    
    def __str__(self):
        return f'{self.plant_code} - {", ".join(self.item_codes)}'

# ========================================================
# MasterParentItemTransportBatchSize
# ========================================================
class MasterParentItemTransportBatchSize(models.Model):
    parent_code = models.CharField(max_length=200, null=False)  
    item_code = models.CharField(max_length=200, null=False)  
    batch_transport = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    location_code = models.CharField(null=True,max_length=100)

    class Meta:
        db_table = 'Master_Parent_ItemTransportBatchSize'
        constraints = [
            models.UniqueConstraint(fields=['parent_code', 'item_code','location_code'], name='master_parent_item_transport_batchwise_pkey')
        ]

    def __str__(self):
        return f'{self.parent_code} - {self.item_code}'


# ========================================================
# ActivateReportModule
# ========================================================
class ActivateReportModule(models.Model):
    report_module = models.CharField(max_length=50, primary_key=True, null=False) 
    active = models.BooleanField(null=False) 

    class Meta:
        db_table = 'Activate_Report_Module'

    def __str__(self):
        return f'{self.report_module} - {self.active}'


# ========================================================
# MasterParentItemProductionBatchSize
# ========================================================
class MasterParentItemProductionBatchSize(models.Model):
    parent_code = models.CharField(max_length=200, null=False)  
    item_code = models.CharField(max_length=200, null=False)  
    batch_size = models.DecimalField(max_digits=13, decimal_places=3, null=False)  
    location_code = models.CharField(null=True,max_length=100)

    class Meta:
        db_table = 'Master_Parent_ItemProductionBatchsize'
        constraints = [
            models.UniqueConstraint(fields=['parent_code', 'item_code','location_code'], name='master_parent_item_production_batchwise_pkey')
        ]

    def __str__(self):
        return f'{self.parent_code} - {self.item_code}'


# ========================================================
# KitAllocation
# ========================================================
class KitAllocation(models.Model):
    order_id = models.CharField(max_length=200)
    line_item = models.CharField(max_length=200)
    plant_code = models.CharField(max_length=50)
    bom_level = models.IntegerField()
    parent = models.CharField(max_length=200)
    allocated_qty = models.DecimalField(max_digits=13, decimal_places=3)
    stock_from_child = models.DecimalField(max_digits=13, decimal_places=3)
    no_of_kits = models.IntegerField()

    class Meta:
        db_table = 'Kit_Allocation'

    def clean(self):
        if not BatchwiseComponentAllocation.objects.filter(col1=self.order_id, col2=self.line_item, col3=self.plant_code).exists():
            raise ValidationError("This group (order_id, line_item, plant_code) is not registered in BatchwiseComponentAllocation.")

# ========================================================
# OrderwiseFolGap
# ========================================================
class OrderwiseFolGap(models.Model):
    order_key = models.ForeignKey(OrderData, on_delete=models.CASCADE, related_name='fol_gap_order_key')
    ccr = models.ForeignKey(CCRMaster, on_delete=models.RESTRICT, related_name='fol_gap_master_ccr')
    fol_gap = models.DecimalField(max_digits=13, decimal_places=2,default = Decimal('0.00'))

    class Meta:
        db_table = 'Orderwise_Fol_Gap'
        constraints = [
            models.UniqueConstraint(fields=['order_key', 'ccr'], name='master_order_ccr_pkey')
        ]


# ========================================================
# OrderItemDetails Model
# ========================================================

class OrderItemDetails(models.Model):
    order = models.ForeignKey(OrderData , on_delete=models.CASCADE,related_name='order_item_details')
    item_code = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='order_item_details_item_code')
    ccr_group = models.ForeignKey(CCRGroupMaster, on_delete=models.CASCADE, related_name='order_item_details_ccr_group', null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = 'Order_Item_Details'
        constraints = [
            models.UniqueConstraint(fields=['order', 'item_code','ccr_group'], name='order_item_details_pkey')
        ]
    def __str__(self):
        return f'{self.order} - {self.item_code} - {self.ccr_group}'

# ========================================================
# IntermediteOrderItemDetails Model
# ========================================================

class IntermediteOrderItemDetails(models.Model):
    order = models.ForeignKey(OrderData , on_delete=models.CASCADE,related_name='intermediate_order_item_details')
    item_code = models.ForeignKey(ItemMaster, on_delete=models.CASCADE, related_name='intermediate_order_item_details_item_code')
    ccr_group = models.ForeignKey(CCRGroupMaster, on_delete=models.CASCADE, related_name='intermediate_order_item_details_ccr_group', null=True, blank=True)
    pending_qty = models.DecimalField(max_digits=13, decimal_places=3, null=True, blank=True)

    class Meta:
        db_table = 'Intermediate_Order_Item_Details'
        constraints = [
            models.UniqueConstraint(fields=['order', 'item_code','ccr_group'], name='intermediate_order_item_details_pkey')
        ]
    def __str__(self):
        return f'{self.order} - {self.item_code} - {self.ccr_group}'

# ========================================================
# BOMHDRRaw Model
# ========================================================
class BOMHDRRaw(models.Model):
    bom_srl_no = models.DecimalField(max_digits=13,decimal_places=0,primary_key=True)
    plant_code = models.CharField(max_length=50)
    parent_item_code = models.CharField(max_length=50)
    parent_uom = models.CharField(max_length=50, blank=True, null=True)
    parent_qty = models.DecimalField(max_digits=13, decimal_places=0)
    is_active = models.BooleanField()
    from_lot_no = models.CharField(max_length=50, blank=True, null=True)
    to_lot_no = models.CharField(max_length=50, blank=True, null=True)
    alternate_bom = models.BooleanField(blank=True, null=True)
    batch_size = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'BOM_HDR_Raw'
    
    def __str__(self):
        return f'{self.bom_srl_no} - {self.plant_code}'

# ========================================================
# BOMDTLRaw Model
# ========================================================
class BOMDTLRaw(models.Model):
    bom_srl_no = models.ForeignKey(BOMHDRRaw,on_delete=models.CASCADE ,related_name = 'bom_dtl_raw_bom_hdr_raw')
    item_srl_no = models.DecimalField(max_digits=13, decimal_places=0)
    component_item_code = models.CharField(max_length=50)
    component_uom = models.CharField(max_length=50, blank=True, null=True)
    conversion = models.DecimalField(max_digits=13, decimal_places=3, blank=True, null=True)
    component_qty = models.DecimalField(max_digits=30, decimal_places=13)
    fixed_multiplier_flag = models.BooleanField()


    class Meta:
        db_table = 'BOM_DTL_Raw'   
        constraints = [
            models.UniqueConstraint(
                fields=['bom_srl_no', 'item_srl_no'],name='bom_dtl_raw_pk'
            )
        ]

# ========================================================
# EcoStockRaw Model
# ========================================================
class EcoStockRaw(models.Model):
    sku_code = models.CharField(max_length=200)
    loc_code = models.CharField(max_length=200)
    stock_in_hand = models.DecimalField(max_digits=13, decimal_places=3, blank=True, null=True)
    stock_in_qc = models.DecimalField(max_digits=13, decimal_places=3, blank=True, null=True)
    stock_in_transit = models.DecimalField(max_digits=13, decimal_places=3, blank=True, null=True)
    uom = models.CharField(max_length=10, blank=True, null=True)
    identifier = models.CharField(max_length=50, blank=True, null=True)
    allocated_so_items = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'EcoStock_Raw'  
        constraints = [
            models.UniqueConstraint(
                fields=['sku_code','loc_code','uom','identifier','allocated_so_items'],
                name='eco_stock_raw_pk'
            )
        ]

    def __str__(self):
        return f'{self.sku_code} - {self.loc_code}'


# ========================================================
# InputFileHDR Model
# ========================================================
class InputFileHDR(models.Model):
    inputid = models.IntegerField(primary_key=True)
    inputname = models.CharField(max_length=100)
    columnterminator = models.TextField(blank=True, null=True)
    rowterminator = models.TextField(blank=True, null=True)
    encoding_type = models.TextField(blank=True, null=True)
    sheet_name = models.TextField(blank=True, null=True)
    storing_schema = models.TextField(blank=True, null=True)
    storing_table = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'InputFileHDR'

    def __str__(self):
        return f'{self.inputname} - {self.inputid}'


# ========================================================
# InputFileDTL Model
# ========================================================
class InputFileDTL(models.Model):
    input = models.ForeignKey(InputFileHDR , on_delete=models.CASCADE , related_name = 'input_file_dtl_input_file_hdr')
    srl_no = models.IntegerField()
    sourcecolumn = models.TextField()
    destination_column = models.TextField()
    datatypeid = models.IntegerField()
    trailingnegativehandling = models.TextField(blank=True, null=True)
    leadingnegativehandling = models.TextField(blank=True, null=True)
    is_mandatory = models.BooleanField(blank=True, null=True)
    dest_col_datatype = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'InputFileDTL'
    
    def __str__(self):
        return f'{self.inputid} - {self.srl_no} - {self.sourcecolumn}'

# ========================================================
# MasterDataType Model
# ========================================================
class MasterDataType(models.Model):
    datatype_id = models.IntegerField(primary_key=True)
    datatype = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'Master_DataType'
    
    def __str__(self):
        return f'{self.datatype_id} - {self.datatype}'


# ========================================================
# ClosedOrderDDQChangesLog Model
# ========================================================
class ClosedOrderDDQChangesLog(models.Model):
    order_id = models.CharField(max_length=500)
    org_due_date = models.DateField()
    is_unscheduled = models.BooleanField(default=False)
    is_due_date_changed = models.BooleanField(default=False)
    user_name = models.CharField(max_length=200)
    updated_on = models.DateTimeField()
    reason = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = 'ClosedOrder_DDQChanges_Log'  
 
    def __str__(self):
        return f'{self.order}'