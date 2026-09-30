import calendar
from datetime import date, datetime, timedelta, timezone
import decimal
from enum import Enum
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status
import math
from mto_app.models import *
import logging
import re
import numpy as np
from django.db.models import Q, JSONField, F
from dateutil.relativedelta import relativedelta
from django.core.exceptions import FieldError
import pandas as pd
from io import BytesIO
from django.http import FileResponse
from mto_app.utils import OTIFTags,PermissionLevel, Attribute_types_column_mapping
from xlsxwriter.utility import xl_rowcol_to_cell
from mto_app.utils import DBR_Settings, OTIFTags, eColors, ePageName, eVFOrderType, FutureOrderLoadChartEnum
from django.http import JsonResponse
from rest_framework.utils.urls import remove_query_param,replace_query_param
import polars as pl
from collections import defaultdict
from django.db.models import Sum
import operator
import uuid
from django.utils.timezone import now
import polars as pl
logger = logging.getLogger(__name__)

conditional_operators = {
        'lt': 'lt',
        'lte': 'lte',
        'gt': 'gt',
        'gte': 'gte',
        'sw': 'istartswith',
        'ew': 'iendswith',
        'et': 'exact',
        'cn': 'icontains'
    }
class CustomPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100000

    def get_paginated_response(self, data, msg, status_code):
        total_pages = math.ceil(self.page.paginator.count / self.page.paginator.per_page)

        return api_response(
            data={
                'links': {
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link()
                },
                'count': self.page.paginator.count,
                'nop': total_pages,  # 'nop' refers to number of pages
                'results': data
            },
            msg=msg,
            status_code=status_code
        )


def api_response(data=None, msg=None, error=None, status_code=status.HTTP_200_OK):
    response_content = {}
    if error:
        response_content = {"msg": error, "data": data}
    else:
        response_content = {"msg": msg, "data": data if data is not None else []}
    
    return Response(response_content, status=status_code)

# Temp fetch_leaf_nodes function for testing
def fetch_leaf_nodes_with_plant(polars=False):
    bom_header = BOMHeader.objects.values('parent_item_code','plant_code','bom_srl_no')
    bom_header_df = pd.DataFrame(
        list(bom_header),
        columns=['parent_item_code', 'plant_code', 'bom_srl_no'],
    )
    bom_detail = BOMDetail.objects.values('component_item_code','bom_srl_no','bom_srl_no__plant_code')
    bom_detail_plant_df = pd.DataFrame(
        list(bom_detail),
        columns=['component_item_code', 'bom_srl_no', 'bom_srl_no__plant_code'],
    )
    filtered_bom_details = pd.merge(bom_detail_plant_df, bom_header_df[['parent_item_code','plant_code']], how='left', left_on=['component_item_code','bom_srl_no__plant_code'], right_on = ['parent_item_code','plant_code'], indicator=True)
    filtered_bom_details = filtered_bom_details.query('_merge=="left_only"')[['component_item_code','bom_srl_no__plant_code']].rename(columns={'bom_srl_no__plant_code':'plant_code'}).drop_duplicates().reset_index(drop=True)
    logger.info("Fetched leaf nodes from BOMDetail")
    if not filtered_bom_details.empty:
        if polars:
            return pl.from_pandas(filtered_bom_details)
        return filtered_bom_details
    if polars:
        schema = {'component_item_code': pl.String, 'plant_code': pl.String}
        return pl.DataFrame({}, schema=schema)
    return pd.DataFrame(columns=['component_item_code','plant_code'])

#common function to fetch leaf nodes from BOMDetail
def fetch_leaf_nodes(order_item_code = None):
    parent_item_codes = BOMHeader.objects.values_list('parent_item_code', flat=True)
    filtered_bom_details = BOMDetail.objects.exclude(component_item_code__in=parent_item_codes)
    filtered_bom_details_list = list(filtered_bom_details.values())
    component_item_codes = {detail['component_item_code'] for detail in filtered_bom_details_list}
    logger.info("Fetched leaf nodes from BOMDetail")
    return component_item_codes

# Sort the data based on "rmc": item_code in alphabetical order
def sort_key(s):                 
    return [int(text) if text.isdigit() else text.lower() for text in re.split('(\d+)', s)] 

# Color mapping for API's to avoid bigger json structure and get color initials
def color_mapping():
    color_map = {'Black':'B',"Blue":'Bl','Yellow':'Y','Red':'R','Green':'G','White':'W'}
    return color_map

def get_filters_for_data(filters, conditional_operators=conditional_operators):
    q_filters = Q()
    for field_name, filter_data in filters.items():
        try:
            if isinstance(filter_data, list) and filter_data:
                q_filters &= Q(**{f'{field_name}__in': filter_data})

            elif isinstance(filter_data, dict) and filter_data:
                op = filter_data.get('op')
                val = filter_data.get('val')
                if op == 'net':
                    q_filters &= ~Q(**{f'{field_name}__exact': val})
                elif op == 'dnc':
                    q_filters &= ~Q(**{f'{field_name}__icontains': val})
                elif op == 'dsw':
                    q_filters &= ~Q(**{f'{field_name}__istartswith': val})
                elif op == 'dnew':
                    q_filters &= ~Q(**{f'{field_name}__iendswith': val})
                elif op == 'hv':
                    q_filters &= Q(**{f'{field_name}__isnull': False})
                elif op == 'et':
                    if isinstance(val, (Decimal, int)):
                        q_filters &= Q(**{f'{field_name}__exact': val})
                    elif isinstance(val, str):
                        q_filters &= Q(**{f'{field_name}__iexact': val.lower()})
                else:
                    lookup = conditional_operators.get(op)
                    if lookup and val is not None:
                        q_filters &= Q(**{f'{field_name}__{lookup}': val})
        except FieldError:
            pass
    return q_filters

def filter_data_by_params(queryset, filters, conditional_operators=conditional_operators):
    q_filters = get_filters_for_data(filters, conditional_operators)
    return queryset.filter(q_filters)

def attribute_data_generation(filters):
    attribute_data = {}
    attributes = filters.get('attributes', None)
    if attributes:
        attribute_filters_list = [key for key , value in attributes.items()]
    if filters and attributes:
        attribute_config_data = AttributeConfiguration.objects.filter(short_name__in = attribute_filters_list, is_active = True).values('short_name','attribute_type','is_number')
        attribute_type_map = {}
        for data in attribute_config_data:
            if data['attribute_type'] not in attribute_type_map:
                attribute_type_map[data['attribute_type']] = []
            attribute_type_map[data['attribute_type']].append(data['short_name'])
        for attr_data,col_codes in attribute_type_map.items():
            for col_code in col_codes:
                attribute_data[f'{Attribute_types_column_mapping[attr_data].value}__{col_code}'] = attributes.get(col_code)
        return attribute_data
    return {}

def filter_order_data_by_params(queryset, filters):
    if filters:
        prod_buff_query = filters.get('pbsz',{})
        proc_buff_query = filters.get('pcbsz',{})
        orders_based_on_buffers = set()
        order_buffer_data = OrderBufferMapping.objects.values('order__order_id','buffer','buffer__buffer_size','buffer__buffer_type__buffer_type')
        
        if prod_buff_query:
            prod_q = get_filters_for_data({'buffer__buffer_size': prod_buff_query})
            orders_based_on_buffers.update(
                data['order__order_id']
                for data in order_buffer_data.filter(prod_q)
            )

        if proc_buff_query:
            proc_q = get_filters_for_data({'buffer__buffer_size': proc_buff_query})
            orders_based_on_buffers.update(
                data['order__order_id']
                for data in order_buffer_data.filter(proc_q)
            )
                
        order_ids = filters.get('id',[])
        if orders_based_on_buffers:
            order_ids.extend(orders_based_on_buffers)
           
        attr_data = attribute_data_generation(filters)
        order_filters = {
            'order_id': order_ids,  # List-based filter
            'line_id': filters.get('lid', []),  # List-based filter
            'ccr__ccr_id': filters.get('ccrid', []),  # List-based filter
            'customer__cust_code': filters.get('cc', []),  # List-based filter
            'customer__cust_name': filters.get('cn', []),  # List-based filter
            'plant__plant_name': filters.get('pn', []),  # List-based filter
            'item__item_description': filters.get('ide', {}),  # Text comparator filter  item__item_description
            'dept__dept_id' : filters.get('deptid',[]),
            'order_value' : filters.get('ov',{}),
            'vf_order_type' : filters.get('ms',[]),
            'item__item_code' : filters.get('ic',[])
        }
        if attr_data:
            order_filters.update(attr_data)
    if filters:
        return filter_data_by_params(queryset, order_filters)
    else:
        return queryset

def filter_overall_bm_report_data_by_params(queryset, filters):
    if filters:
        dept_ids = filters.get('deptid',[])
        dept_code = list(DeptMaster.objects.filter(dept_id__in = dept_ids).values_list('dept_code', flat=True))
        ccr_ids = filters.get('ccrid',[])
        ccr_names = list(CCRMaster.objects.filter(ccr_id__in = ccr_ids).values_list('ccr_name', flat=True))
        prod_buff_query = filters.get('pbsz',{})
        proc_buff_query = filters.get('pcbsz',{})
        orders_based_on_buffers = set()
        order_buffer_data = OrderBufferMapping.objects.values('order','buffer','buffer__buffer_size','buffer__buffer_type__buffer_type')
        if prod_buff_query:
            prod_q = get_filters_for_data({'buffer__buffer_size': prod_buff_query})
            orders_based_on_buffers.update(
                data['order']
                for data in order_buffer_data.filter(prod_q)
            )
        if proc_buff_query:
            proc_q = get_filters_for_data({'buffer__buffer_size': proc_buff_query})
            orders_based_on_buffers.update(
                data['order']
                for data in order_buffer_data.filter(proc_q)
            )
        order_ids = filters.get('id',[])
        if orders_based_on_buffers:
            order_ids.extend(orders_based_on_buffers)

        attr_data = attribute_data_generation(filters)
        order_filters = {
            'order_id': order_ids,  # List-based filter
            'line_id': filters.get('lid', []),  # List-based filter
            'ccr_name': ccr_names,  # List-based filter
            'cust_code': filters.get('cc', []),  # List-based filter
            'cust_name': filters.get('cn', []),  # List-based filter
            'plant_name': filters.get('pn', []),  # List-based filter
            'item_desc': filters.get('ide', {}),  # Text comparator filter
            'dept_code' : dept_code,
            'order_value' : filters.get('ov',{}),
            'order_type' : filters.get('ms',[]),
            'item_code' : filters.get('ic',[]),
            'dept_id': filters.get('deptid',[]),
            'major_r_id' : filters.get('majid',[]),
            'minor_r_id' : filters.get('minid',[]),
            'route_name' : filters.get('ro',[]),
        }
        if attr_data:
            order_filters.update(attr_data)
    if filters:
        return filter_data_by_params(queryset, order_filters)
    else:
        return queryset

def filer_order_wip_by_params(queryset,filters):
    if filters:
        order_filters = {
            'dept__dept_id': filters.get('deptid',[]),
            'item_code' : filters.get('ic',[]) # Text comparator filter
        }
    if filters:
        return filter_data_by_params(queryset, order_filters)
    else:
        return queryset

def get_weeks_in_month_till_date(to_date):
    year = to_date.year
    month = to_date.month
    day =  to_date.day

    # List to hold the weeks
    weeks = []
    
    # Loop through the days and create weeks until the given day
    week_start = 1
    week_horizon = 7
    while week_start <= day:
        week_end = min(week_start + week_horizon - 1, day)
        start_date = datetime(year, month, week_start)
        end_date = datetime(year, month, week_end)
        weeks.append((start_date, end_date))
        week_start += week_horizon

    if len(weeks) > 4:
        del weeks[-1]
    return weeks

def calculate_quartiles_and_whiskers(data):
    if data:
        sorted_data = np.sort(data)
        Q1 = np.percentile(sorted_data, 25)
        Q2 = np.median(sorted_data)
        Q3 = np.percentile(sorted_data, 75)
        IQR = Q3 - Q1
        lower_whisker = max(min(sorted_data), Q1 - 1.5 * IQR)
        upper_whisker = min(max(sorted_data), Q3 + 1.5 * IQR)
        return Q1, Q2, Q3, lower_whisker, upper_whisker
    else:
        None,None,None,None,None
        

def get_OTIF_status_of_order(pending_qty, order_close_date, order_due_date):

    flags = [DBR_Settings.delivery_tolerance, DBR_Settings.mfg_tolerance, DBR_Settings.unit_of_measurement]
    dbr_settings = DBRSettings.objects.filter(flag__in = flags).values('flag', 'value')

    delivery_tolerance = 0
    mfg_tolerance = 0

    for dbr_setting in dbr_settings:
        if dbr_setting['flag'] == DBR_Settings.delivery_tolerance:
            delivery_tolerance = int(dbr_setting['value'])
        elif dbr_setting['flag'] == DBR_Settings.mfg_tolerance:
            mfg_tolerance = int(dbr_setting['value'])

    pending_qty_as_per_mfg_tolerance = get_pending_qty_as_per_mfg_tolerance(mfg_tolerance, pending_qty)
    extend_of_delay = (order_close_date - order_due_date).days
    tag = 0
    # calculate tag value
    if extend_of_delay > delivery_tolerance and pending_qty > pending_qty_as_per_mfg_tolerance:
        tag = OTIFTags.OT_False_IF_False
    elif extend_of_delay <= delivery_tolerance and pending_qty <= pending_qty_as_per_mfg_tolerance:
        tag = OTIFTags.OT_True_IF_True
    elif extend_of_delay <= delivery_tolerance and pending_qty > pending_qty_as_per_mfg_tolerance:
        tag = OTIFTags.OT_True_IF_False
    elif extend_of_delay > delivery_tolerance and pending_qty <= pending_qty_as_per_mfg_tolerance:
        tag = OTIFTags.OT_False_IF_True
    else:
        tag = 0
    return tag

def get_pending_qty_as_per_mfg_tolerance(mfg_tolerance, pending_qty):
    pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * pending_qty
    return pending_qty_as_per_mfg_tolerance

def get_past_month_date(given_date):
    # Subtract one month using relativedelta
    past_month_date = given_date - relativedelta(months=1)
    return past_month_date

    
def get_item_batchsize(item_codes):
    batch_size_map = {}
    if item_codes:
        filter_condition = {'item_code__in' : item_codes}
    else:
        filter_condition= {}
    batchsize_itemcode_map = MasterItemProductionBatchsize.objects.filter(**filter_condition).values('item_code','batch_size')
    for data in batchsize_itemcode_map:
        if data['item_code'] not in batch_size_map:
            batch_size_map[data['item_code']] = data['batch_size']
    return batch_size_map

def filter_buffer_data_by_params(queryset, filters):
    conditional_operators = {
        'lt': 'lt',
        'lte': 'lte',
        'gt': 'gt',
        'gte': 'gte',
        'et': 'exact',
        'sw': 'istartswith',
        'ew': 'iendswith',
        'icontains': 'icontains',
    }
    filter_applied = False
    if filters:
        pbsz_data = filters.get('pbsz', None)
        pcbsz_data = filters.get('pcbsz', None)

        def build_filter_condition(buffer_type, data):
            op = data['op']
            val = data['val']
            lookup = conditional_operators.get(op)
            if lookup:
                return Q(
                    **{
                        f'buffer__buffer_type__buffer_type': buffer_type,
                        f'buffer__buffer_size__{lookup}': val,
                    }
                )
            return Q()

        if pbsz_data and not pcbsz_data:
            queryset = queryset.filter(build_filter_condition('prod', pbsz_data))
            filter_applied = True
        elif pcbsz_data and not pbsz_data:
            queryset = queryset.filter(build_filter_condition('proc', pcbsz_data))
            filter_applied = True
        elif pbsz_data and pcbsz_data:
            queryset = queryset.filter(
                build_filter_condition('prod', pbsz_data) |
                build_filter_condition('proc', pcbsz_data)
            )
            filter_applied = True
    return queryset,filter_applied

def get_daywise_coverage_history_orders_details(daywise_coverage_orders):
    daywise_order_ids = daywise_coverage_orders.values_list('order_id').distinct()
    daywise_line_ids = daywise_coverage_orders.values_list('line_id').distinct()

    # Query OrderData using the order_id and line_id from daywise_coverage_orders
    orders = OrderData.objects.filter(
    order_id__in=daywise_order_ids, line_id__in=daywise_line_ids
    ).values('order_id', 'line_id', 'total_qty', 'due_date', 'color', 'plant')

    # Query OrderData using the order_id and line_id from daywise_coverage_orders
    closed_orders = ClosedOrders.objects.filter(
    order_id__in=daywise_order_ids, line_id__in=daywise_line_ids
    ).values('order_id', 'line_id', 'total_qty', 'due_date', 'color', 'plant')

    # Combine results from OrderData and ClosedOrders into a QuerySet
    all_orders_with_details = orders.union(closed_orders)
    daywise_coverage_orders_dict = {f"{item['order_id']},{item['line_id']}": item for item in all_orders_with_details}

    for order in daywise_coverage_orders:
        okey = (order['order_id'], order['line_id'])
        if okey in daywise_coverage_orders_dict:
            order_details = daywise_coverage_orders_dict[okey]
            order['total_qty'] = order_details['total_qty']
            order['due_date'] = order_details['due_date']
            order['color'] = order_details['color']
            order['plant'] = order_details['plant']
    daywise_coverage_orders_with_updated_details = daywise_coverage_orders
    return daywise_coverage_orders_with_updated_details

# Function to handle "Prod_DDQ"
def get_orders_for_prod_ddq_data():
    return OrderData.objects.filter(vf_order_type=eVFOrderType.MTO.value)

# Function to handle "Proc_Material_Requirement"
def get_orders_for_proc_material_requirement_data(release_date):
    result = None
    if release_date:
        result = OrderData.objects.filter(planned_release_date__lte=release_date)
    return result

# Function to handle "Proc_Procurement_Planning"
def get_orders_for_proc_procurement_planning_data(release_date):
    filters = Q(vf_order_type=eVFOrderType.MTA.value)
    if release_date:
        filters |= Q(
            vf_order_type=eVFOrderType.MTO.value,
            actual_released_date__lte=release_date
        )
    result   =  OrderData.objects.filter(filters)
    return result

# Function to handle "Proc_Material_Coverage_For_OpenSO"
def get_orders_for_proc_material_coverage_for_openso_data():
    return OrderData.objects.filter(color__isnull=False)

# Function to handle "Proc_RM_PM_OrderWise"
def get_orders_for_proc_rm_pm_orderwise_data():
    return OrderData.objects.filter(
        is_rm_released=False,
        planned_release_date__lte=date.today() + timedelta(days=90)
    )

# Function to handle "Prod_Dynamic_Release_Management"
def get_orders_for_prod_dynamic_release_management_data(all_orders_flag):
    filters = {
        'is_rm_released': False,
        'due_date__isnull': False,
        'vf_order_type': eVFOrderType.MTO.value
    }

    filter_condition = {}
    
    if not all_orders_flag:
        excluded_order = ExcludedOrders.objects.values('order_id', 'line_item')
        excluded_oid = [data['order_id'] for data in excluded_order]
        excluded_lid = [data['line_item'] for data in excluded_order]
        filter_condition = {'order_id__in': excluded_oid, 'line_id__in': excluded_lid}
    
    return OrderData.objects.filter(**filters).exclude(**filter_condition)

# Function to handle "Open_SO_Details - Material_Coverage_for_Open_Sales_Order"
def get_orders_for_open_so_details_data(colors, s, e):
    today = timezone.now().date()
    start_date = today + timedelta(days=s)
    end_date = today + timedelta(days=e)

    queryset = OrderData.objects.filter(color__in=colors)
    
    # Apply additional filtering if White or Blue is in colors
    if eColors.WHITE.value in colors or eColors.BLUE.value in colors:
        queryset = queryset.filter(due_date__range=[start_date, end_date])

    return queryset

# Function to handle "Proc_Day_Wise_Coverage"
def get_orders_for_proc_day_wise_coverage_data(filter_for_daywise_coverage, filter_for_order_data):
    try:
        daywise_coverage_orders = None
        order_data_orders = None

        if filter_for_daywise_coverage:
            daywise_coverage_queryset = DaywiseCoverageHistory.objects.filter(planned_release_date__range=filter_for_daywise_coverage).values('order_id', 'line_id')

            daywise_order_ids = [order['order_id'] for order in daywise_coverage_queryset]
            daywise_line_ids = [order['line_id'] for order in daywise_coverage_queryset]

            order_data_from_daywise = OrderData.objects.filter(
                order_id__in=daywise_order_ids, line_id__in=daywise_line_ids
            ).values('order_id', 'line_id', 'item', 'plant', 'route', 'order_value', 'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type', 'order_key', 'order_attributes', 'line_order_attributes')

            closed_orders_from_daywise = ClosedOrders.objects.filter(
                order_id__in=daywise_order_ids, line_id__in=daywise_line_ids
            ).values('order_id', 'line_id', 'item', 'plant', 'route', 'order_value', 'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type', 'order_key', 'order_attributes', 'line_order_attributes')

            daywise_coverage_orders = order_data_from_daywise.union(closed_orders_from_daywise)

        if filter_for_order_data:
            order_data_orders = OrderData.objects.filter(planned_release_date__range=filter_for_order_data).values('order_id', 'line_id', 'item', 'plant', 'route', 'order_value', 'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type', 'order_key', 'order_attributes', 'line_order_attributes')

        # Combine the two QuerySets if both exist
        if order_data_orders and daywise_coverage_orders:
            all_orders = daywise_coverage_orders.union(order_data_orders)
        elif order_data_orders and not daywise_coverage_orders:
            all_orders = order_data_orders
        else:
            all_orders = daywise_coverage_orders

        return all_orders
    
    except Exception as e:
        print(str(e))

def get_colors_and_range(request):
    colors = request.GET.get('Color', '').split(',') if request.GET.get('Color') else []
    s = int(request.GET.get('S', 0))
    e = int(request.GET.get('E', 0))
    return colors, s, e

# Function to get the all_orders_flag from the request
def get_all_orders_flag(request):
    all_orders_flag = request.GET.get('ao')
    
    if all_orders_flag is not None and all_orders_flag.isdigit():
        all_orders_flag = bool(int(all_orders_flag))
    else:
        all_orders_flag = False
    
    return all_orders_flag

#function to handle "Prod_FullKit_Assignment"
def get_fullkit_assignment_data():
    return OrderData.objects.filter(is_rm_released=False, route__isnull = False)

def get_filter_condition_toapply(request):
    isAssigned = request.GET.get('isAssigned') 

    if not bool(int(isAssigned)):
        filter_condition = {'major_reason__isnull': True}
        filter_history_condition = {'major_reason__isnull' : True}
    else:
        filter_condition = {} 
        filter_history_condition = {}

    return filter_condition, filter_history_condition

def get_horizon_date(request):
    rm_horizon = request.GET.get('rm_horizon')
    rm_flag = False
    if rm_horizon:
        rm_flag = True
    sup_horizon = request.GET.get('supplier_horizon')
    horizon_date = date.today() + timedelta(days=int(rm_horizon if rm_flag else sup_horizon))
    return horizon_date

def get_expiditing_rm_supplier_data(horizon_date):
    result = None
    if horizon_date:
        result = OrderData.objects.filter(planned_release_date__lte=horizon_date, planned_release_date__gte=date.today(), is_rm_released=False)
    return result

def get_prod_overall_bm_report():
    order_data = None
    overall_bm_report_order_keys = OverallBMReport.objects.values_list('order_key', flat=True)
    order_data = OrderData.objects.filter(order_key__in=overall_bm_report_order_keys)
    return order_data

def get_prod_stpl_and_fullkits():
    stpl_orders = OrderData.objects.filter(is_rm_released = True)
    return stpl_orders

def get_prod_order_at_risk():
    order_data = OrderData.objects.filter(color__in = [eColors.RED.value, eColors.BLACK.value]).exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True)
    return order_data

def get_prod_order_balance():
    order_data = OrderData.objects.filter(is_line_finished = False, is_rm_released = True, trailing_dept__isnull=False)
    return order_data

def get_poogi_lead_time():
    closed_orders = None
    today = date.today()
    three_months_ago_date = today - relativedelta(months=3)
    three_months_ago_date = three_months_ago_date.replace(day=1)
    closed_orders = ClosedOrders.objects.filter(
        actual_released_date__isnull=False,
        closure_date__range=[three_months_ago_date, today])
    return closed_orders

def get_poogi_otif_analysis():
    closed_orders = None
    todays_date = datetime.now().date()
    # Get the first day of the current month
    first_day_of_current_month = todays_date.replace(day=1)
    from_date = ''
    to_date = ''
    # calculate from which month to which month data need to be collected
    if first_day_of_current_month == todays_date:
        from_month = todays_date - relativedelta(months=3)
        from_date = from_month.replace(day=1)
        to_date = todays_date + relativedelta(months=-1, day=31)
    elif todays_date > first_day_of_current_month:
        from_month = todays_date - relativedelta(months=2)
        from_date = from_month.replace(day=1)
        to_date = todays_date

    closed_orders = ClosedOrders.objects.filter(closure_date__range=[from_date, to_date])
    return closed_orders

def get_poogi_trend_of_failure_reasons():
    closed_orders = []
    todays_date = datetime.now().date()
    first_day_of_current_month = todays_date.replace(day=1)
    first_day_of_initial_past_month = first_day_of_current_month - relativedelta(months=4)
    closed_orders = ClosedOrders.objects.filter(closure_date__range = [first_day_of_initial_past_month, todays_date]).exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True)
    return closed_orders

def get_poogi_top_failure_reasons():
    closed_orders = []
    closed_orders = ClosedOrders.objects.exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True)
    return closed_orders

def get_poogi_reason_for_delayed_orders(order_filter_conditions, closed_order_filter_conditions):
    order_color = [eColors.BLACK.value]
    order_data  = OrderData.objects.filter(**order_filter_conditions,color__in = order_color).values(
            'order_id', 'line_id', 'item', 'plant', 'route', 'order_value',
            'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type',
            'order_key', 'order_attributes', 'line_order_attributes', 'order_type'
        )
    closed_order_data = ClosedOrders.objects.filter(**closed_order_filter_conditions,color__in = order_color).values(
            'order_id', 'line_id', 'item', 'plant', 'route', 'order_value',
            'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type',
            'order_key', 'order_attributes', 'line_order_attributes', 'order_type'
        )
    
    order_data_list = list(order_data)
    closed_order_data_list = list(closed_order_data)
    order_data_list.extend(closed_order_data_list)
    return order_data_list
    
def get_date_range_for_proc_day_wise_coverage(request):
    from_date = None
    to_date = None
    filter_for_order_data = []
    filter_for_daywise_coverage = []

    if request.GET.get('FromDate') and request.GET.get('ToDate'):
        from_date = datetime.strptime(request.GET.get('FromDate'), "%Y-%m-%d").date()
        to_date = datetime.strptime(request.GET.get('ToDate'), "%Y-%m-%d").date()

        todays_date = datetime.now().date()
        next_day = (todays_date + timedelta(days=1)).strftime("%Y-%m-%d")

        if from_date < todays_date and to_date < todays_date: # past-past
            filter_for_daywise_coverage = [from_date,to_date]
            filter_for_order_data = None  
        elif from_date == todays_date and to_date > todays_date: # present-future
            filter_for_daywise_coverage = [from_date,todays_date]
            filter_for_order_data = [next_day, to_date]
        elif from_date < todays_date and to_date == todays_date: # past-present
            filter_for_daywise_coverage = [from_date, to_date]
            filter_for_order_data = None  
        elif from_date > todays_date and to_date > todays_date: # future-future
            filter_for_daywise_coverage = None
            filter_for_order_data = [from_date, to_date]
        elif from_date < todays_date and to_date > todays_date: # past-future
            filter_for_daywise_coverage = [from_date,todays_date]
            filter_for_order_data = [next_day, to_date]
    
    return filter_for_daywise_coverage, filter_for_order_data

def get_future_order_load_data(request):
    data = request.data
    filters = data.get('filters', {})
    if filters is not None:
        ccr = filters.get('ccr',None)
        orderOption = filters.get('orderOption', '')
        from_date = filters.get('from', '')
        to_date = filters.get('to', '')
        horizon_date = filters.get('horizon_date', '')
    else:
        return None
    routes_details_list = RouteDetails.objects.filter(ccr=ccr).values_list('route')
    from_date = date.fromisoformat(from_date)
    to_date = date.fromisoformat(to_date)
    horizon_date = date.fromisoformat(horizon_date) if horizon_date != '' else None
    conditional_map={
                FutureOrderLoadChartEnum.NotScheduleBeyondFOLHorizon.value : {'expected_due_date__gt' : from_date,'expected_due_date__lte': to_date , 
                                                                            'due_date__isnull': True},
                FutureOrderLoadChartEnum.AllNotSchedule.value : {'expected_due_date__lte': to_date , 'due_date__isnull': True},
                }
    order_condition = conditional_map.get(orderOption)
    if order_condition is None:
        return None
    order_data = OrderData.objects.filter(route__in=routes_details_list, **order_condition)
    return order_data


# Main function to get order data based on page_name
def get_order_data(page_name, request, release_date=None):

    colors, s, e = None, None, None
    all_orders_flag = None
    horizon_date = None
    order_filter_conditions = None
    closed_order_filter_conditions = None

    # Map page_name to corresponding function
    page_name_func_mapping = {
        ePageName.PROD_DDQ.value: get_orders_for_prod_ddq_data,
        ePageName.PROC_MATERIAL_REQUIREMENT.value: lambda: get_orders_for_proc_material_requirement_data(release_date),
        ePageName.PROC_PROCUREMENT_PLANNING.value: lambda: get_orders_for_proc_procurement_planning_data(release_date),
        ePageName.PROC_MATERIAL_COVERAGE_FOR_OPENSO.value: get_orders_for_proc_material_coverage_for_openso_data,
        ePageName.PROC_RM_PM_ORDERWISE.value: get_orders_for_proc_rm_pm_orderwise_data,
        ePageName.PROD_DYNAMIC_RELEASE_MANAGEMENT.value: lambda: get_orders_for_prod_dynamic_release_management_data(all_orders_flag),
        ePageName.MATERIAL_COVERAGE_FOR_OPEN_SO.value: lambda: get_orders_for_open_so_details_data(colors, s, e),
        ePageName.PROD_FULLKIT_ASSIGNMENT.value: get_fullkit_assignment_data,
        ePageName.PROC_EXPEDITING_RM_AND_SUPPLIERS.value: lambda: get_expiditing_rm_supplier_data(horizon_date),
        ePageName.PROD_OVERALL_BMREPORT.value: get_prod_overall_bm_report,
        ePageName.PROD_STPL_AND_FULLKITS.value: get_prod_stpl_and_fullkits,
        ePageName.PROD_ORDER_AT_RISK.value: get_prod_order_at_risk,
        ePageName.PROD_ORDER_BALANCE.value: get_prod_order_balance,
        ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value: lambda: get_poogi_reason_for_delayed_orders(order_filter_conditions, closed_order_filter_conditions),
        ePageName.POOGI_LEAD_TIME.value: get_poogi_lead_time,
        ePageName.POOGI_OTIF_ANALYSIS.value: get_poogi_otif_analysis,
        ePageName.POOGI_OTandIF_ANALYSIS.value: get_poogi_otif_analysis,
        ePageName.PROD_DEPT_WISE_BM_REPORT.value: get_prod_overall_bm_report,
        ePageName.POOGI_TREND_OF_FAILURE_REASONS.value: get_poogi_trend_of_failure_reasons,
        ePageName.POOGI_TOP_FAILURE_REASONS.value: get_poogi_top_failure_reasons,
        ePageName.FUTURE_ORDER_LOAD_CHART.value: lambda: get_future_order_load_data(request),
        # ePageName.PROC_DAY_WISE_COVERAGE.value: lambda: get_orders_for_proc_day_wise_coverage_data(filter_for_daywise_coverage, filter_for_order_data)
    }

    # Fetch colors, s, e values from request
    if page_name == ePageName.MATERIAL_COVERAGE_FOR_OPEN_SO.value:
        colors, s, e = get_colors_and_range(request)
    
    # Fetch all_orders
    if page_name == ePageName.PROD_DYNAMIC_RELEASE_MANAGEMENT.value:
        all_orders_flag = get_all_orders_flag(request)

    # Fetch sup_horizon and rm_horizon
    if page_name == ePageName.PROC_EXPEDITING_RM_AND_SUPPLIERS.value:
        horizon_date = get_horizon_date(request)

    if page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value:
        order_filter_conditions, closed_order_filter_conditions = get_filter_condition_toapply(request)

    # Initialize date variables for "Proc_Day_Wise_Coverage"
    # filter_for_daywise_coverage, filter_for_order_data = get_date_range_for_proc_day_wise_coverage(request) if page_name == "Proc_Day_Wise_Coverage" else (None, None)

    # Fetch the function based on page_name
    order_data_func = page_name_func_mapping.get(page_name)

    if order_data_func:
        orders = order_data_func()
    else:
        orders = OrderData.objects.all()

    # Return data based on page_name
    if page_name in {ePageName.PROC_DAY_WISE_COVERAGE.value, ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value}:
        return orders

    return orders.values(
        'order_id', 'line_id', 'item', 'plant', 'route', 'order_value',
        'customer', 'major_reason', 'minor_reason', 'dept', 'vf_order_type',
        'order_key', 'order_attributes', 'line_order_attributes', 'order_type'
    )


def filter_closed_orders_data_by_params(queryset, filters):
    if filters:
        prod_buff_query = filters.get('pbsz',{})
        proc_buff_query = filters.get('pcbsz',{})
        orders_based_on_buffers = set()
        order_buffer_data = OrderBufferMapping.objects.values('order__order_id','buffer','buffer__buffer_size','buffer__buffer_type__buffer_type')
        if prod_buff_query:
            prod_q = get_filters_for_data({'buffer__buffer_size': prod_buff_query})
            orders_based_on_buffers.update(
                data['order__order_id']
                for data in order_buffer_data.filter(prod_q)
            )
        if proc_buff_query:
            proc_q = get_filters_for_data({'buffer__buffer_size': proc_buff_query})
            orders_based_on_buffers.update(
                data['order__order_id']
                for data in order_buffer_data.filter(proc_q)
            )
                
        order_ids = filters.get('id',[])
        if orders_based_on_buffers:
            order_ids.extend(orders_based_on_buffers)

        attr_data = attribute_data_generation(filters)
        order_filters = {
            'oid': order_ids,  # List-based filter
            'lid': filters.get('lid', []),  # List-based filter
            'ccr': filters.get('ccrid', []),  # List-based filter
            'cc': filters.get('cc', []),  # List-based filter
            'cn': filters.get('cn', []),  # List-based filter
            'plnt': filters.get('pn', []),  # List-based filter
            'id': filters.get('ide', {}),  # Text comparator filter
            'dept' : filters.get('deptid',[]),
            'ov' : filters.get('ov',{}),
            'ot' : filters.get('ms',[]),
            'ic' : filters.get('ic',[])
        }
        if attr_data:
            order_filters.update(attr_data)
    if filters:
        return filter_data_by_params(queryset, order_filters, conditional_operators)
    else:
        return queryset

def clean_color_priority(val):
        if isinstance(val, list) and isinstance(val[0], dict):
            if all(percent == 0 for percent in val[0].values()):
                return ""
        return val

COLOR_MAP = {
    'R': 'red',
    'G': 'green',
    'B': 'black',
    'Y': 'yellow',
    'W': 'gray',
    'Bl': 'blue'
}

# Function to write a cell with conditional coloring logic (Used in CustomExcelExport)
def write_colored_cell(worksheet, row_idx, col_idx, val, header_name, row_data, color_header_map, workbook, normal_format):
    if header_name in color_header_map:
        # Try to extract color value from row_data fields
        color_value = next((row_data.get(k) for k in ['cp', 'cl', 'clr'] if row_data.get(k) is not None), None)

        # Case 1: color is specified as a breakdown of percentages (dict inside a list)
        if isinstance(color_value, list) and len(color_value) > 0 and isinstance(color_value[0], dict):
            color_dict = color_value[0]
            total_blocks = 10
            blocks = []
            for color_key, percent in color_dict.items():
                if color_key in COLOR_MAP and percent > 0:
                    num_blocks = round((percent / 100) * total_blocks)
                    fmt = workbook.add_format({'font_color': COLOR_MAP[color_key], 'bold': True})
                    blocks.extend([fmt, '█'] * num_blocks)
            if blocks:
                worksheet.write_rich_string(row_idx, col_idx, *blocks)
            else:
                worksheet.write(row_idx, col_idx, "")
        
        # Case 2: color is a simple string (e.g. 'r', 'b', 'g')
        elif isinstance(color_value, str):
            try:
                bg_color = color_value.lower()
                if bg_color == 'w':
                    bg_color = eColors.gray.value
                font_color = eColors.white.value if bg_color in [eColors.black.value, eColors.blue.value, eColors.red.value] else eColors.black.value
                cell_format = workbook.add_format({'bg_color': bg_color, 'font_color': font_color, 'align': 'center'})
                worksheet.write(row_idx, col_idx, val, cell_format)
            except Exception:
                worksheet.write(row_idx, col_idx, val)

        # Default: write without format if nothing matched
        else:
            worksheet.write(row_idx, col_idx, val)

    # If the header is not marked for color
    else:
        worksheet.write(row_idx, col_idx, val, normal_format)

# Recursive function to write BOM child rows with indentation and collapsibility(Used in CustomExcelExport)
def write_bom_level(worksheet, workbook, normal_format, bold_center, bom_rows, bom_headers, bom_short_cc, bom_color_headers, row_index_ref, path_prefix, level):
    row_index = row_index_ref[0]
    hierarchy_key = next(iter(bom_rows[0]), None)

    # Filter children based on the path prefix (hierarchical nesting)
    if hierarchy_key and all(isinstance(b.get(hierarchy_key), list) for b in bom_rows):
        children = [b for b in bom_rows if tuple(b[hierarchy_key][:-1]) == path_prefix]
    else:
        children = bom_rows

    # If children exist, write BOM headers
    if children:
        indent = len(children[0].get(hierarchy_key, [])) - 1 if isinstance(children[0].get(hierarchy_key), list) else 0
        worksheet.write_row(row_index, 2 + indent, bom_headers, bold_center)
        worksheet.set_row(row_index, None, bold_center, {'level': level, 'hidden': True})
        row_index += 1

    for child in children:
        indent = len(child.get(hierarchy_key, [])) - 1 if isinstance(child.get(hierarchy_key), list) else 0
        for col_offset, short_code in enumerate(bom_short_cc):
            val = child.get(short_code, "")

            # Show only the last item
            if short_code == hierarchy_key and isinstance(val, list) and val:
                val = val[-1]

            # Convert lists and decimals for display
            if isinstance(val, list):
                val = ", ".join(map(str, val))
            elif isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, (float, int)) and (math.isnan(val) or math.isinf(val)):
                val = ""
            write_colored_cell(worksheet, row_index, 2 + indent + col_offset, val, bom_headers[col_offset], child, bom_color_headers, workbook, normal_format)

        # Check for nested children
        has_nested = any(
            isinstance(r.get(hierarchy_key), list) and tuple(r[hierarchy_key][:-1]) == tuple(child[hierarchy_key])
            for r in bom_rows
        ) if hierarchy_key and isinstance(child.get(hierarchy_key), list) else False

        worksheet.set_row(row_index, None, normal_format, {'level': level, 'hidden': True, 'collapsed': has_nested})
        row_index += 1

        # Recursively write nested BOM levels
        if has_nested:
            row_index_ref[0] = row_index
            write_bom_level(worksheet, workbook, normal_format, bold_center, bom_rows, bom_headers, bom_short_cc, bom_color_headers, row_index_ref, tuple(child[hierarchy_key]), level + 1)
            row_index = row_index_ref[0]

    row_index_ref[0] = row_index

# Main Excel Export Function
def CustomExcelExport(
    data,
    report_name='report',
    headers=None,
    isGrouped=False,
    isChildren=False,
    child_element='children',
    name_of_report_parent=None,     # Used to get the parent data
    name_of_report_child=None       # Used to get the child data (if present)
):
    output = BytesIO()
    report_name = report_name[:31]  # Excel sheet name max length
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    worksheet = workbook.add_worksheet(report_name)
    writer.sheets[report_name] = worksheet

    # Define commonly used formats
    bold_center = workbook.add_format({'bold': True, 'align': 'center'})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'center'})
    normal_format = workbook.add_format({'text_wrap': True})
    worksheet.outline_settings(True, False, False, True)

    row_index = 0
    column_headers = []
    flat_headers = []

    # Flatten headers structure depending on whether grouped or not  
    if headers and isinstance(headers, list) and 'cc' in headers[0] and 'ch' in headers[0]:
        for group in headers:
            group_name = group.get('cc')
            for col in group.get('ch', []):
                column_headers.append((group_name, col['hd'], col['scc']))
                flat_headers.append(col)
    elif headers and isinstance(headers, list):
        for col in headers:
            column_headers.append(("", col['hd'], col['scc']))
        flat_headers = headers

    # Fetch color configuration for headers from DB
    db_headers = UIReportConfigurations.objects.filter(
        report_name=name_of_report_parent
    ).values('header', 'short_col_code', 'col_position', 'is_color')

    color_headers = {
        entry['header']: entry
        for entry in db_headers
        if entry.get('is_color')
    }

    # Write grouped header rows if applicable
    if isGrouped:
        group_col = 0
        while group_col < len(column_headers):
            group_name = column_headers[group_col][0]
            span = 1
            while group_col + span < len(column_headers) and column_headers[group_col + span][0] == group_name:
                span += 1
            if span > 1:
                worksheet.merge_range(row_index, group_col, row_index, group_col + span - 1, group_name, bold_center)
            else:
                worksheet.write(row_index, group_col, group_name, bold_center)
            group_col += span
        row_index += 1
        for i, (_, header_name, _) in enumerate(column_headers):
            worksheet.write(row_index, i, header_name, bold_center)
        row_index += 1
    else:
        worksheet.write_row(row_index, 0, list(data[0].keys()), bold_center)
        column_headers = [(None, key, key) for key in data[0].keys()]
        row_index += 1

    bom_config = UIReportConfigurations.objects.filter(
                report_name=name_of_report_child
            ).values('header', 'short_col_code', 'col_position', 'is_color', 'visible').order_by('col_position')

    visible_bom_config = [entry for entry in bom_config if entry.get('visible', True)]
    
    bom_headers = [entry['header'] for entry in visible_bom_config]
    bom_short_cc = [entry['short_col_code'] for entry in visible_bom_config]

    bom_color_headers = {
        entry['header']: entry
        for entry in visible_bom_config
        if entry.get('is_color') is True
    }
    
    # Write parent rows
    for item in data:
        for col_idx, (_, hd, scc) in enumerate(column_headers):
            val = item.get(scc, "")
            if isinstance(val, list):
                val = ", ".join(map(str, val))
            elif isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, (float, int)) and (math.isnan(val) or math.isinf(val)):
                val = ""
            elif isinstance(val, (date, datetime)):
                worksheet.write_datetime(row_index, col_idx, val, date_format)
                continue
            write_colored_cell(worksheet, row_index, col_idx, val, hd, item, color_headers, workbook, normal_format)
        row_index += 1

        # If BOM children exist, write them
        if isChildren and item.get(child_element):
            bom_rows = item[child_element]

            # Fetch child BOM column config

            worksheet.set_row(row_index, None, bold_center, {'level': 1, 'hidden': True})
            row_index += 1

            row_index_ref = [row_index]
            write_bom_level(
                worksheet, workbook, normal_format, bold_center, bom_rows, bom_headers,
                bom_short_cc, bom_color_headers, row_index_ref, (), 2
            )
            row_index = row_index_ref[0]

    # Auto-size all columns
    for col in range(len(column_headers)):
        worksheet.set_column(col, col, 20)

    writer.close()
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=f"{report_name}.xlsx")

def ExcelExportData(data, report_name, name_of_report_parent=None ,headers=None):
    engine_value = 'xlsxwriter'
    df = pd.DataFrame()
    
    # Extract header names correctly
    header_names = [header['hd'] for header in headers] if headers else []

    db_headers = UIReportConfigurations.objects.filter(
        report_name=name_of_report_parent,
        header__in=header_names
    ).values('header', 'short_col_code', 'col_position', 'is_color')
    
    color_headers = {
        entry['header']: {
            'scc': entry['short_col_code'],
            'is_color': entry['is_color'],
            'col_position': entry['col_position']
        }
        for entry in db_headers
        if entry.get('is_color')
    }

    if headers:
        for header in headers:
            scc = header['scc']
            hd = header['hd']
            df[hd] = [', '.join(row_data.get(scc,"")) if isinstance(row_data.get(scc),list) and not isinstance(row_data.get(scc)[0], dict) else row_data.get(scc, "") for row_data in data]

    for hd in color_headers.keys():
        if hd in df.columns:
            df[hd] = df[hd].apply(clean_color_priority)

    output = BytesIO()
    report_name = report_name[:31]
    writer = pd.ExcelWriter(output, engine=engine_value)
    df.to_excel(writer, sheet_name=report_name, index=False)

    workbook = writer.book
    worksheet = writer.sheets[report_name]

    COLOR_MAP = {
        'R': 'red',
        'G': 'green',
        'B': 'black',
        'Y': 'yellow',
        'W': 'gray',
        'Bl': 'blue',
        "Gr" : 'gray'
    }

    for hd, header in color_headers.items():
        col_index = df.columns.get_loc(hd)

        for row_idx, row_data in enumerate(data, start=1):
            color_value = next((row_data.get(key) for key in ['cp', 'cl', 'clr'] if row_data.get(key) is not None), None)
            display_value = ', '.join(row_data.get(header['scc'],"")) if isinstance(row_data.get(header['scc']),list) and not isinstance(row_data.get(header['scc'])[0], dict) else row_data.get(header['scc'], "")

            if isinstance(color_value, list) and len(color_value) > 0 and isinstance(color_value[0], dict):
                color_dict = color_value[0]

                total_blocks = 10
                blocks = []

                for color_key, percent in color_dict.items():
                    if color_key in COLOR_MAP and percent > 0:
                        num_blocks = round((percent / 100) * total_blocks)
                        fmt = workbook.add_format({
                            'font_color': COLOR_MAP[color_key],
                            'bold': True
                        })
                        blocks.extend([fmt, '█'] * num_blocks)

                if blocks:
                    worksheet.write_rich_string(row_idx, col_index, *blocks)
                else:
                    worksheet.write(row_idx, col_index, "")
            elif isinstance(color_value, str):
                try:
                    bg_color = color_value.lower()
                    if bg_color in ['w','white']:
                        bg_color = 'gray'
                    font_color = 'white' if bg_color in ['black', 'blue', 'red'] else 'black'
                    cell_format = workbook.add_format({
                        'bg_color': bg_color,
                        'font_color': font_color,
                        'align': 'center'
                    })
                    worksheet.write(row_idx, col_index, display_value, cell_format)
                except Exception:
                    worksheet.write(row_idx, col_index, display_value)
            else:
                worksheet.write(row_idx, col_index, display_value)

    writer.close()
    output.seek(0)
    response = FileResponse(output, as_attachment=True, filename=f"{report_name}.xlsx")
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response['Content-Disposition'] = f'attachment; filename="{report_name}.xlsx"'
    return response
  
def comparater_for_numeric_field(field_value,val,filtered_data,record,op):
    if op == 'et':
        if field_value == val:
            filtered_data.append(record)
    elif op == 'lt':  
        if field_value < val:
            filtered_data.append(record)
    elif op == 'lte':  # Less than or equal to
        if field_value <= val:
            filtered_data.append(record)
    elif op == 'gt':  # Greater than
        if field_value > val:
            filtered_data.append(record)
    elif op == 'gte':  # Greater than or equal to
        if field_value >= val:
            filtered_data.append(record)  
    return filtered_data              

def apply_filter_condtion_to_dict_data(data, attribute_name, attribute_condtion):
    op = attribute_condtion.get('op')
    val = attribute_condtion.get('val')
    lookup = conditional_operators.get(op)
    numeric_comparator = ['et','lt','gt','gte','lte']
    if not attribute_condtion:
        return data

    filtered_data = []

    if lookup and val is not None:
        for record in data:
            if attribute_name not in record:
                continue
            
            field_value = record.get(attribute_name, None)

            if field_value is not None:
                is_field_value_numeric = str(field_value).replace('.', '', 1).isdigit()
                is_val_numeric = str(val).replace('.', '', 1).isdigit()
                if op == 'net':  
                    if field_value != val:
                        filtered_data.append(record)
                elif op == 'dnc':  
                    if val.lower() not in str(field_value).lower():
                        filtered_data.append(record)
                elif op == 'dsw':  
                    if not str(field_value).lower().startswith(val.lower()):
                        filtered_data.append(record)
                elif op == 'dew':  
                    if not str(field_value).lower().endswith(val.lower()):
                        filtered_data.append(record)
                elif op == 'hv':  
                    if field_value is not None:
                        filtered_data.append(record)
                elif is_field_value_numeric or is_val_numeric and lookup in numeric_comparator:
                    field_value = float(field_value) if '.' in str(field_value) else int(field_value)
                    val = float(val) if '.' in str(val) else int(val)
                    filtered_data = comparater_for_numeric_field(field_value,val,filtered_data,record,op)
                else:
                    field_value = str(field_value)
                    if lookup == 'exact' and field_value.lower() == val.lower():
                        filtered_data.append(record)
                    elif lookup == 'icontains' and val.lower() in field_value.lower():
                        filtered_data.append(record)
                    elif lookup == 'istartswith' and field_value.lower().startswith(val.lower()):
                        filtered_data.append(record)
                    elif lookup == 'iendswith' and field_value.lower().endswith(val.lower()):
                        filtered_data.append(record)
    return filtered_data

def filter_attribute_data_by_params(data , filters):
    active_attributes = set(AttributeConfiguration.objects.filter(is_active = True).values_list('short_name', flat= True))
    if filters:
            for key,value in filters.items():
                if key in active_attributes:
                    data = apply_filter_condtion_to_dict_data(data, key, value)
    return data

def getOTIFStatusValue(tag):
    match tag:
        case OTIFTags.OT_False_IF_False:
            return "OT Fail and IF Fail"
        case OTIFTags.OT_True_IF_True:
            return "OT Pass and IF Pass"
        case OTIFTags.OT_True_IF_False:
            return "OT Pass and IF Fail"
        case OTIFTags.OT_False_IF_True:
            return "OT Fail and IF Pass"
        case _:
            return "Invalid tag value"

def GetUserDetails(data):
    product_permissions = data.get('product_permissions',[])
    location_permissions = data.get('location_permissions',[])
    is_admin = data.get('user',{}).get('is_admin',False)
    return product_permissions,location_permissions,is_admin

def filter_data_with_attached_permissions(queryset, filter_conditions):
    if filter_conditions:
        logger.debug("Applying attached permissions filter with conditions")
        model_fields = {f.name: f for f in queryset.model._meta.get_fields()}
        for column_name, column_data in filter_conditions.items():
            if column_name in model_fields and isinstance(model_fields[column_name], JSONField):
                for key, value_list in column_data.items():
                    if isinstance(value_list, list):
                        queryset = queryset.filter(**{f'{column_name}__{key}__in': value_list})
                    else:
                        queryset = queryset.filter(**{f'{column_name}__{key}': value_list})
            elif column_name not in model_fields:
                for key, value_list in column_data.items():
                    if isinstance(value_list, list) and key in model_fields:
                        queryset = queryset.filter(**{f'{key}__in': value_list})
        
        if queryset.exists():
            logger.debug("Filtered queryset exists")
            return queryset
        else:
            logger.debug("Filtered queryset does not exist")
            return queryset.none()
    else:
        logger.debug("No filter conditions provided")
        return queryset.none()

def DataPermissionFilter(queryset, product_permission, location_permission, is_admin=False):
    data_permission_enabled_flag = DBRSettings.objects.get(flag = DBR_Settings.is_data_permission_enabled)
    if not data_permission_enabled_flag:
        return queryset

    if data_permission_enabled_flag.value == '1' or data_permission_enabled_flag.value == 'True':
        logger.debug("Data permission is enabled for this site.")
        data_permission_enabled_flag = True
    else:
        logger.debug("Data permission is not enabled for this site.")
        data_permission_enabled_flag = False

    if is_admin or not data_permission_enabled_flag:
        logger.info("Skipping permission filter for admin user or for the site where data permission is not enabled.")
        return queryset

    generated_permissions = DataPermissionGenerator(product_permission, location_permission)

    if generated_permissions:
        queryset = filter_data_with_attached_permissions(queryset, generated_permissions)
        return queryset
    else:
        logger.warning("No permissions generated.")
        return None


def DataPermissionGenerator(product_permission, location_permission):
    permission_levels = {
        1: PermissionLevel.Level1,
        2: PermissionLevel.Level2,
        3: PermissionLevel.Level3
    }
    all_permissions_id = []
    
    if isinstance(product_permission, list) and isinstance(location_permission, list):
        all_permissions_id = product_permission + location_permission
    logger.debug("Permission ids for product and location")
    
    permission_details = MTOPermissionDetails.objects.filter(permission_details_id__in=list(all_permissions_id)).values()
    permission_type = permission_details.values_list('mto_permission_type_id', flat=True).distinct()
    
    logger.debug("mto permission details has been fetched")
    
    permissionn_type_master_data = MTOPermissionType.objects.values()
    permission_type_map_master_map = {data['type_id']: data for data in permissionn_type_master_data}
    permission_details_with_type_map = {}

    logger.debug("mto permission type details has been fetched")

    for permission in permission_details:
        if permission['mto_permission_type_id'] not in permission_details_with_type_map:
            permission_details_with_type_map[permission['mto_permission_type_id']] = []
        permission_details_with_type_map[permission['mto_permission_type_id']].append(permission)
    
    if permission_type:
        permission_headers = MTOPermissionHeader.objects.filter(mto_permission_type__in=permission_type).values(
            'mto_permission_type_id', 'header_name', 'mapped_attribute', 'level').order_by('level')
        permission_header_map = {}
        
        for header in permission_headers:
            if header['mto_permission_type_id'] not in permission_header_map:
                permission_header_map[header['mto_permission_type_id']] = []
            permission_header_map[header['mto_permission_type_id']].append(header['mapped_attribute'])
        
        permission_header_with_data_list = {}
        
        for permission_id, permission_headers in permission_header_map.items():
            attribute_type = permission_type_map_master_map.get(permission_id).get('mapped_attribute_type')
            if attribute_type not in permission_header_with_data_list:
                permission_header_with_data_list[attribute_type] = {}
            for index, header in enumerate(permission_headers):
                if header not in permission_header_with_data_list[attribute_type]:
                    permission_header_with_data_list[attribute_type][header] = []
                permission_details_data_list = permission_details_with_type_map.get(permission_id)
                data_set = set()
                for data in permission_details_data_list:
                    if data[permission_levels.get(index + 1).value] is not None:
                        if data[permission_levels.get(index + 1).value].isdigit():
                            data_set.add(int(data[permission_levels.get(index + 1).value]))
                        elif check_floating(data[permission_levels.get(index + 1).value]):
                            data_set.add(float(data[permission_levels.get(index + 1).value]))
                        elif data[permission_levels.get(index + 1).value].lower() == 'true':
                            data_set.add(True)
                        elif data[permission_levels.get(index + 1).value].lower() == 'false':
                            data_set.add(False)
                        else:
                            data_set.add(data[permission_levels.get(index + 1).value])
                permission_header_with_data_list[attribute_type][header] = list(data_set)
        
        logger.info("Generated permission  details with header and its  data for filtering")
        return permission_header_with_data_list
    else:
        logger.warning("No permission types found.")
        return {}

def check_floating(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def sort_color_priority(entry):
    cp_dict = entry["cp"][0]  # Extract color percentages
    color_order = ["B", "R", "Y", "G", "W", "Bl"]  # Define priority order

    # Step 1: Determine the highest priority color present
    color_priority = next((i for i, color in enumerate(color_order) if cp_dict.get(color, 0) > 0), len(color_order))

    # Step 2: Sort by color priority, then by percentage within the same priority
    color_values = tuple(-cp_dict.get(color, 0) for color in color_order)

    return (color_priority, color_values)


def DataPermissionFilterForOrderData(queryset,product_permission,location_permission, is_admin=False , closed_order=False):
    data_permission_enabled_flag = DBRSettings.objects.get(flag = DBR_Settings.is_data_permission_enabled)
    if not data_permission_enabled_flag:
        return queryset
        
    if data_permission_enabled_flag.value == '1' or data_permission_enabled_flag.value == 'True':
        logger.debug("Data permission is enabled for this site.")
        data_permission_enabled_flag = True
    else:
        logger.debug("Data permission is not enabled for this site.")
        data_permission_enabled_flag = False

    if is_admin or not data_permission_enabled_flag:
        logger.info("Skipping permission filter for admin user or for the site where data permission is not enabled.")
        return queryset
    
    generated_permissions = DataPermissionGenerator(product_permission, location_permission)
    
    if generated_permissions and not closed_order:
        queryset = filter_order_data_with_attached_permissions(queryset, generated_permissions)
        return queryset
    elif generated_permissions and closed_order:
        queryset = filter_closed_order_data_with_attached_permissions(queryset, generated_permissions)
        return queryset
    else:
        logger.warning("No permissions generated.")
        return None

def filter_order_data_with_attached_permissions(queryset, filter_conditions):
    if filter_conditions:
        logger.debug("Applying attached permissions filter with conditions")
        model_fields = {f.name: f for f in queryset.model._meta.get_fields()}
        for column_name, column_data in filter_conditions.items():
            if column_name in model_fields and isinstance(model_fields[column_name], JSONField):
                for key, value_list in column_data.items():
                    if isinstance(value_list, list):
                        queryset = queryset.filter(**{f'{column_name}__{key}__in': value_list})
                    else:
                        queryset = queryset.filter(**{f'{column_name}__{key}': value_list})
            else:
                dept_ids = []
                if 'dept_code' in column_data:
                    dept_codes = column_data.get('dept_code',None)
                    if dept_codes:
                        dept_ids = DeptMaster.objects.filter(dept_code__in  = dept_codes).values_list('dept_id',flat=True)
                        dept_ids = list(dept_ids)
                order_filters = {
                    'order_id': column_data.get('order_id',[]),  # List-based filter
                    'line_id': column_data.get('line_id', []),  # List-based filter
                    'ccr__ccr_name': column_data.get('ccr_name', []),  # List-based filter
                    'customer__cust_name': column_data.get('cust_name', []),
                    'customer__cust_code' : column_data.get('cust_code',[]),  # List-based filter
                    'plant__plant_name': column_data.get('plant_name', []),  # List-based filter
                    'item__item_description': column_data.get('item_desc', {}),  # Text comparator filter
                    'dept__dept_id' : dept_ids,
                    'order_value' : column_data.get('order_value',{}),
                    'item__item_code' : column_data.get('item_code',[])
                }
                if order_filters:
                    queryset = filter_data_by_params(queryset , order_filters)
        if queryset.exists():
            logger.debug("Filtered queryset exists")
            return queryset
        else:
            logger.debug("Filtered queryset does not exist")
            return queryset.none()
    else:
        logger.debug("No filter conditions provided")
        return queryset.none()

def filter_closed_order_data_with_attached_permissions(queryset, filter_conditions):
    if filter_conditions:
        logger.debug("Applying attached permissions filter with conditions")
        model_fields = {f.name: f for f in queryset.model._meta.get_fields()}
        for column_name, column_data in filter_conditions.items():
            if column_name in model_fields and isinstance(model_fields[column_name], JSONField):
                for key, value_list in column_data.items():
                    if isinstance(value_list, list):
                        queryset = queryset.filter(**{f'{column_name}__{key}__in': value_list})
                    else:
                        queryset = queryset.filter(**{f'{column_name}__{key}': value_list})
            else:
                dept_ids = []
                if 'dept_code' in column_data:
                    dept_codes = column_data.get('dept_code',None)
                    if dept_codes:
                        dept_ids = DeptMaster.objects.filter(dept_code__in  = dept_codes).values_list('dept_id',flat=True)
                        dept_ids = list(dept_ids)
                order_filters = {
                    'oid': column_data.get('order_id',[]),  # List-based filter
                    'lid': column_data.get('line_id', []),  # List-based filter
                    'ccr': column_data.get('ccr_name', []),  # List-based filter
                    'cc': column_data.get('cust_code',[]),  # List-based filter
                    'cn': column_data.get('cust_name', []),  # List-based filter
                    'plnt': column_data.get('plant_name', []),  # List-based filter
                    'id': column_data.get('item_desc', {}), # Text comparator filter
                    'dept' : dept_ids,
                    'ov' : column_data.get('order_value',{}),
                    'ic' : column_data.get('item_code',[])
                }
                if order_filters:
                    queryset = filter_data_by_params(queryset , order_filters)
        if queryset.exists():
            logger.debug("Filtered queryset exists")
            return queryset
        else:
            logger.debug("Filtered queryset does not exist")
            return queryset.none()
    else:
        logger.debug("No filter conditions provided")
        return queryset.none()

def get_color_mapping():
    color_mapping = {"Black":"B", "Red": "R", "Yellow": "Y", "Green": "G","White": "W", "Blue":"Bl"}
    return color_mapping


def get_OTIF_status_of_order(ot_tag, if_tag):
    tag = OTIFTags.OTIFNone
    if ot_tag == False and if_tag == False:
        tag = OTIFTags.OT_False_IF_False
    elif ot_tag == True and if_tag == True:
        tag = OTIFTags.OT_True_IF_True
    elif ot_tag == True and if_tag == False:
        tag = OTIFTags.OT_True_IF_False
    elif ot_tag == False and if_tag == True:
        tag = OTIFTags.OT_False_IF_True
    return tag

def get_range_index(value, ranges):
    for idx, (key, range_value) in enumerate(ranges.items(), start=1):
        if range_value['low'] <= value <= range_value['high']:
            return key
    return None

def is_batchwise_allocation():
    dbr_setting = DBRSettings.objects.filter(flag = DBR_Settings.bom_component_allocation_type).values_list('value', flat=True).first()
    is_batchwise_allocation = False if dbr_setting == '0' else True
    return is_batchwise_allocation
    
def get_kit_allocation_data(query):
    kit_allocation_data = KitAllocation.objects.filter(query).values('order_id', 'line_item', 'plant_code', 'bom_level', 'no_of_kits')
    if kit_allocation_data:
        kit_allocation_data_dict = {(kit_data['order_id'], kit_data['line_item'], kit_data['plant_code'], kit_data['bom_level']): kit_data for kit_data in kit_allocation_data}
    return kit_allocation_data_dict

def get_order_fullkit_value(kit_allocation_data,order_id,line_id,plant_code):
    bom_level = 0
    order_fullkit_value = 0
    fg_fullkit_details = kit_allocation_data.get((order_id,line_id,plant_code,bom_level))
    if fg_fullkit_details:
        order_fullkit_value = fg_fullkit_details.get("no_of_kits")
    return order_fullkit_value


class MTOPagination():
    def create_next_link(self, request, page_number , nop):
        query_params = request.GET.copy()
        query_params['page'] = page_number
        return request.build_absolute_uri(f"?{query_params.urlencode()}") if page_number <= nop else None
    
    def create_previous_link(self, request, page_number):
        query_params = request.GET.copy()
        query_params['page'] = page_number
        return request.build_absolute_uri(f"?{query_params.urlencode()}") if page_number>=1 else  None
    
    def create_paginated_response(self , request , data  , nop , count):
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 15))
        response_data = {
            'nop': nop,
            'count': count,
            'links' : {
                'next' : None,
                'previous' : None
            },
            'results': data
        }
        
        if page < nop:
            response_data['links']['next'] = remove_query_param(self.create_next_link(request, page + 1 , nop),'alldata')
        if page > 1:
            response_data['links']['previous'] = remove_query_param(self.create_previous_link(request, page - 1 ),'alldata')

        return response_data

def get_order_information(order , page , page_size):
    if isinstance(order,pd.DataFrame) or isinstance(order,pl.DataFrame):
        record_count = len(order)
    else:
        record_count = order.count()
    nop = int(math.ceil(record_count / page_size)) if page_size > 0 else 1
    return record_count , nop

def get_pagewise_data(order , page , page_size):
    try:
        if page < 1:
            page = 1
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_data = order[start_index:end_index]
        return paginated_data
    except Exception as e:
        logger.error(f"Error in getting page wise data: {e}")
        return []

def filter_order_history_data_by_params(queryset, filters):
    if filters:
        order_ids = filters.get('id',[])
        dept_ids = filters.get('deptid',[])
        dept_code = list(DeptMaster.objects.filter(dept_id__in = dept_ids).values_list('dept_code', flat=True))
        attr_data = attribute_data_generation(filters)
        order_filters = {
            'order_id': order_ids,  # List-based filter
            'line_id': filters.get('lid', []),  # List-based filter
            'ccr__ccr_id': filters.get('ccrid', []),  # List-based filter
            'cust_code__cust_code': filters.get('cc', []),  # List-based filter
            'cust_code__cust_name': filters.get('cn', []),  # List-based filter
            'plant__plant_name': filters.get('pn', []),  # List-based filter
            'item__item_description': filters.get('ide', {}),  # Text comparator filter  item__item_description
            'dept' : dept_code,
            'order_value' : filters.get('ov',{}),
            'vf_order_type' : filters.get('ms',[]),
            'item__item_code' : filters.get('ic',[]),
            'ccr__ccr_group':filters.get('grpid',[])
        }
        if attr_data:
            order_filters.update(attr_data)
        return filter_data_by_params(queryset, order_filters)
    else:
        return queryset  

def from_queryset_to_polars_df( queryset, fields: list[str]) -> pl.DataFrame:
        """
        Creates a Polars DataFrame from a Django queryset using .values(),
        ensuring field names exist even if queryset is empty.
        """
        data = list(queryset)

        if not data:
            # Create empty DataFrame with specified columns and nulls
            return pl.DataFrame({field: [] for field in fields})

        # Normalize all dicts to have all fields
        normalized = []
        for row in data:
            normalized.append({field: row.get(field, None) for field in fields})

        return pl.DataFrame(normalized, infer_schema_length=len(normalized))

'''   

def validate_ccr_mappings(ccrids, item_id, ccr_details):
    errors = []
    valid_ccr_objects = {}
    # valid_touch_time = {}
    # Check if item_type exists
    try:
        item_type_obj = ItemTypeMaster.objects.get(item_type_id=item_id)
    except ItemTypeMaster.DoesNotExist:
        errors.append({'item_id': item_id, 'error': 'ItemTypeMaster not found'})
        return errors  # Early exit if item_type is missing

    # Loop through each CCR detail
    for ccrid in ccrids:
        try:
            ccr_obj = CCRMaster.objects.get(ccr_id=ccrid)
        except CCRMaster.DoesNotExist:
            errors.append({'ccrid': ccrid, 'item_id': item_id, 'error': 'CCR not found in CCRMaster'})
            continue
        mapping = CCRItemTypeMapping.objects.filter(ccr=ccr_obj, item_type=item_type_obj).first()
        if not mapping:
            errors.append({'ccrid': ccrid, 'item_id': item_id, 'error': 'CCR-ItemType mapping not found'})
        elif mapping.touch_time_in_mins is None:
            errors.append({'ccrid': ccrid, 'item_id': item_id, 'error': 'Touch time not defined'})
        else:
            valid_ccr_objects[ccrid] = ccr_obj
            ccr_details[ccrid]['tt'] = mapping.touch_time_in_mins if mapping.touch_time_in_mins is not None else 0
            ccr_details[ccrid]['working_hrs_per_day'] = ccr_obj.working_hours_per_day
            ccr_details[ccrid]['ccrn'] = ccr_obj.ccr_name
            ccr_details[ccrid]['res_buff'] = ccr_obj.residual_buffer
            ccr_details[ccrid]['folh'] = ccr_obj.fol_horizon
    return errors, valid_ccr_objects, ccr_details


def get_fol_data_by_ccrids(ccrids):
    fol_data = {}
    errors = []

    fol_records = FOL_Data.objects.filter(ccr__ccr_id__in=ccrids)

    # Create a lookup map for quick access
    fol_map = {record.ccr.ccr_id: record for record in fol_records}

    for ccrid in ccrids:
        record = fol_map.get(ccrid)

        if not record:
            errors.append({'ccrid': ccrid, 'error': 'FOL_Data not found'})
            continue

        fol_in_days = record.fol_in_days
        occupied_qty_in_mins = record.occupied_qty_in_mins

        if fol_in_days is None or occupied_qty_in_mins is None:
            errors.append({
                'ccrid': ccrid,
                'error': 'FOL data incomplete: fol_in_days or occupied_qty_in_mins missing'
            })
        else:
            fol_data[ccrid] = {
                'fol_in_days': fol_in_days,
                'occupied_qty_in_mins': occupied_qty_in_mins
            }

    return errors, fol_data

def ccr_processing_errors(ccr_errors, fol_data_errors):
    combined_errors = []

    if ccr_errors:
        combined_errors.extend(ccr_errors)

    if fol_data_errors:
        combined_errors.extend(fol_data_errors)

    return combined_errors


def get_latest_working_day_lno(ccr_id, plant_id):
    today = date.today()
    errors = []

    # Lookup DailyWorkingCalendar entry
    entry = DailyWorkingCalendar.objects.filter(
        working_date__gte=today,
        ccr__ccr_id=ccr_id,
        plant__plant_id=plant_id
    ).order_by('working_date').first()

    if not entry or entry.lno is None:
        errors.append({
            'ccrid': ccr_id,
            'plant_id': plant_id,
            'error': 'Missing working day or lno not defined in DailyWorkingCalendar'
        })

    return errors, entry.lno

def get_order_buffer_data(order_key):
    buffer_data = OrderBufferMapping.objects.filter(order__order_key=order_key).values(
        'order__order_key',
        'buffer__buffer_size',
        'buffer__buffer_type__buffer_type',
        'buffer_date'
    )

    buffer_summary = {'proc': None, 'prod': None, 'bdate':None}
    errors = []

    for record in buffer_data:
        buffer_type = record['buffer__buffer_type__buffer_type'].lower()
        buffer_size = record['buffer__buffer_size']
        buffer_date = record['buffer_date']

        if buffer_size is None:
            errors.append({
                'order_key': order_key,
                'buffer_type': buffer_type,
                'error': 'Missing buffer_size value'
            })
            continue

        if buffer_type == 'proc':
            buffer_summary['proc'] = buffer_size
            buffer_summary['bdate'] = buffer_date
        elif buffer_type == 'prod':
            buffer_summary['prod'] = buffer_size
            buffer_summary['bdate'] = buffer_date

    return errors, buffer_summary

def is_order_eligible_for_FOL(orderwise_mfhd):
    # MTO orders to be considered for FOL - orders whose release date is within Fol Horizon are to be considered for FOL calculations
    mto_orders_to_be_considered_for_FOL = []
    for key,value in orderwise_mfhd.items():
        if value['mfhd'] and value['pbd']:
            if value['mfhd'] >= value['pbd']:
                mto_orders_to_be_considered_for_FOL.append(key)
    if mto_orders_to_be_considered_for_FOL:
        eligible = True
    else:
        eligible = False
    return eligible

def get_ccr_order_loads(new_ccr_details):
    aggregated_load = defaultdict(Decimal)
    for ccr_id, details in new_ccr_details.items():
        aggregated_load[ccr_id] += Decimal(details.get('ol', 0))
    sorted_ccr_load = dict(sorted(aggregated_load.items()))

def get_ccr_wise_working_calendar_data(ccr_ids):
    #Get today's date
    todays_date = date.today()
    logger.info('todays date from date.today()')

    # Daily working calender data
    working_details = DailyWorkingCalendar.objects.filter(ccr__in = ccr_ids,working_date__gte=todays_date).values('lno','ccr','plant','working_date').order_by('working_date')
    logger.info('Fetched daily working data for the CCRs')

    #create ccrId - WorkingDate map
    ccr_next_working_date_map = {}
    for data in working_details:
            ccr_id = data['ccr']
            working_date = data['working_date']
            if ccr_id not in ccr_next_working_date_map or working_date < ccr_next_working_date_map[ccr_id]['wd']:
                ccr_next_working_date_map[ccr_id] = {
                    'lno' : data['lno'],
                    'wd' : working_date
                }
    return working_details, ccr_next_working_date_map

def get_ccr_fol_data(ccr_details, ccr_next_working_date_map, ccr_working_details):
    ccr_fol_data = {}
    for ccr_id, ccr_data in ccr_details.items():
        next_wd_lno = ccr_next_working_date_map.get(ccr_id,{})
        if ccr_id not in ccr_fol_data:
            horizon_date_qs = ccr_working_details.filter(lno = (ccr_data['folh']  + next_wd_lno.get('lno',0))).values('working_date')
            horizon_date = horizon_date_qs[0]['working_date'] if horizon_date_qs else next_wd_lno.get('wd',date.today())
            ccr_fol_data[ccr_id] = {
                'fhd' : horizon_date ,
                'wd' : next_wd_lno.get('wd',None),
                'cdI' : next_wd_lno.get('lno') if next_wd_lno.get('lno') else 0,
                'mtofol' : 0,
                'mtostpl' : 0,
                'mtafol': 0 ,
                'mtastpl' : 0
            }
    return ccr_fol_data

def get_fol_data(order_data, ccr_details, order_buffer_data, valid_ccrs):
    ccr_ids = list(ccr_details.keys())
    ccr_working_details, ccr_next_working_date_map = get_ccr_wise_working_calendar_data(ccr_ids)

    # Assuming ccr_ids is a list of CCR IDs to be filtered
    # ccr_details = CCRMaster.objects.filter(ccr_id__in=ccr_ids).annotate(capacity=F('working_hours_per_day') * 60).values('ccr_id', 'plant', 'capacity', 'fol_horizon')
    # logger.info('Fetched CCR master data and capacity for specific CCRs based on working hours per day')

    #create dict of ccrId - CCr_details
    # ccr_details_mapping = {ccr['ccr_id'] : ccr for ccr in ccr_details}
    
    ccr_fol_data = get_ccr_fol_data(ccr_details, ccr_next_working_date_map, ccr_working_details)

    line_ccr_details = LineCCRDetails.objects.filter(ccr__isnull=False,order__in=order_data.order_key).values('order', 'ccr', 'pending_ccr_qty', 'order_load')
    logger.info('Fetched the Line CCR details for specified orders')

    # max fol horizon for mto orders - get orderwise max FOL horizon date
    # from multiple ccrs in route get max FOL horizon date by comparing FOlHOrizon date of each ccr in route
    orderwise_mfhd = defaultdict(lambda: {'mfhd': None, 'pbd': None})

    for ccr_id, data in ccr_details.items():
        order = order_data.order_key  # Or extract per entry if it's different per CCR
        fol_data = ccr_fol_data.get(ccr_id, {})
        prod_buffer_date = order_buffer_data['bdate']

        if orderwise_mfhd[order]['pbd'] is None and prod_buffer_date:
            orderwise_mfhd[order]['pbd'] = prod_buffer_date

        mfhd = orderwise_mfhd[order].get('mfhd', None)
        fhd = fol_data.get('fhd', None)

        if mfhd and fhd:
            max_fol_horizon_date = max(mfhd, fhd)
        elif fhd and not mfhd:
            max_fol_horizon_date = fhd
        else:
            max_fol_horizon_date = mfhd

        orderwise_mfhd[order]['mfhd'] = max_fol_horizon_date

    mto_fol_in_days = {}
    mto_stpl_in_days = {}

    if is_order_eligible_for_FOL(orderwise_mfhd):
        ccr_order_loads = get_ccr_order_loads(ccr_details)
        for ccr_id, total_order_load in ccr_order_loads.items():
            if (ccr_id not in mto_fol_in_days) or (ccr_id not in mto_stpl_in_days):
                ccr_detail = ccr_details.get(ccr_id, {})
                capacity = Decimal(ccr_detail.get('capacity', 0))
                mto_fol_in_days[ccr_id] = (total_order_load / capacity) if capacity > 0 else total_order_load
                mto_stpl_in_days[ccr_id] = (total_order_load / capacity) if capacity > 0 else total_order_load


    is_mta_capacity_reserved = DBRSettings.objects.get(flag = 'IsMTACapacityReserved').value
    logger.info('Fetched DBR setting value for flag IsMTACapacityReserved')
    mta_fol_in_days = {}
    mta_stpl_in_days = {}

    if int(is_mta_capacity_reserved) == 0 or is_mta_capacity_reserved == 'False':
        #MTA orders FOL and STPL
        if order_data.vf_order_type == 'MTA':
            ccr_order_loads = defaultdict(Decimal)
            for ccr_id, detail in ccr_details.items():
                ccr_order_loads[ccr_id] += Decimal(detail.get('ol', 0))
            mta_ccr_order_loads = sorted(
                [{'ccr': ccr_id, 'total_order_load': total_load} for ccr_id, total_load in ccr_order_loads.items()],
                key=lambda x: x['ccr']
            )

            if  order_data.bpp >= 0:
                mta_stpl_ccr_order_load = sorted(
                [{'ccr': ccr_id, 'total_order_load': total_load} for ccr_id, total_load in ccr_order_loads.items()],
                key=lambda x: x['ccr']
                )

            for data in mta_ccr_order_loads:
                ccr_id = data.get('ccr')
                if (ccr_id not in mta_fol_in_days) and (ccr_id is not None) or (data['ccr'] not in mta_stpl_in_days):
                    ccr_detail = ccr_details.get(ccr_id, {})
                    capacity = Decimal(ccr_detail.get('capacity', 0))
                    # Ensure total_order_load has a safe fallback
                    total_order_load = Decimal(data.get('total_order_load') or 0)
                    mta_fol_in_days[ccr_id] = (total_order_load / capacity if capacity > 0 else total_order_load)
                    mta_stpl_in_days[ccr_id] = (total_order_load / capacity if capacity > 0 else total_order_load)

    fol_data_instance = FOL_Data.objects.filter(ccr__in = ccr_ids)
    logger.info('Fetched FOL Data')

    #get ccr ids from FOL Data
    ccr_ids = [data.ccr for data in fol_data_instance]
    logger.info('collected ccr ids from FOL data')

    fol_data_instance_mapping = {data.ccr.ccr_id : data for data in fol_data_instance}
    fol_data_to_be_created = []
    fol_data_to_be_updated = []
    for ccr in ccr_ids:
        mto_fol = mto_fol_in_days.get(ccr,0)
        mta_fol = mta_fol_in_days.get(ccr,0)
        mto_stpl = mto_stpl_in_days.get(ccr,0)
        mta_stpl = mta_stpl_in_days.get(ccr,0)
        fol_in_days = round((mto_fol + mta_fol) if mto_fol and mta_fol else (mto_fol if  mto_fol else mta_fol),2)
        fol_in_days_for_fol_end_date = round(fol_in_days,0)
        stpl_in_days = (mto_stpl + mta_stpl) if mto_stpl and mta_stpl else (mto_stpl if  mto_stpl else mta_stpl)
        todays_lno = ccr_next_working_date_map.get(ccr,None)
        todays_lno_date = 0
        if todays_lno:
            todays_lno_date = todays_lno.get('lno',0)
        fol_end_date_qs = ccr_working_details.filter(lno =  todays_lno_date + fol_in_days_for_fol_end_date).values('working_date')
        fol_end_date =  fol_end_date_qs[0]['working_date'] if fol_end_date_qs else None
        if fol_end_date is not None:
            if ccr in fol_data_instance_mapping:
                fol_instance = fol_data_instance_mapping.get(ccr)
                fol_instance.fol_in_days = fol_in_days
                fol_instance.fol_end_date = fol_end_date
                fol_instance.stpl_in_days = stpl_in_days
                fol_data_to_be_updated.append(fol_instance)
            else:
                fol_data_to_be_created.append(
                    FOL_Data(
                    fol_end_date = fol_end_date,
                    fol_in_days = fol_in_days,
                    stpl_in_days = stpl_in_days,
                    ccr = valid_ccrs[ccr],
                    occupied_qty_in_units = 0,
                    occupied_qty_in_mins = 0,
                ))
    return fol_data_to_be_created

'''

def compare_ccr_routes(prev_details, new_details):

    def normalize(details):
        normalized = {}
        for ccr in details:
            try:
                pos = int(ccr.get('pos', 0))
                normalized[pos] = ccr
            except (TypeError, ValueError):
                continue
        return normalized

    prev_map = normalize(prev_details)
    new_map = normalize(new_details)

    all_positions = sorted(set(prev_map.keys()) | set(new_map.keys()))

    added = []
    removed = []
    replaced = []
    unchanged = []

    for pos in all_positions:
        old = prev_map.get(pos)
        new = new_map.get(pos)

        if old is None and new is not None:
            added.append(new)
        elif new is None and old is not None:
            removed.append(old)
        elif (
            old.get('ccrid') != new.get('ccrid') or
            old.get('ccrgrp') != new.get('ccrgrp')
        ):
            replaced.append((pos, old, new))
        else:
            unchanged.append(new)


    return {
        'added': added,
        'removed': removed,
        'replaced': replaced,
        'unchanged': unchanged,
    }

def get_ccr_details_for_route(route_id,order_key):
    # Step 1: Fetch RouteDetails efficiently
    route_details_qs = RouteDetails.objects.filter(route_id=route_id).values(
        "ccr_id", "ccr_grp_id", "position"
    )

    # Step 2: Fetch LineCCRDetails for this route
    line_ccr_qs = LineCCRDetails.objects.filter(
        route_id=route_id, order_id=order_key
    ).values("ccr_id", "pending_ccr_qty", "order_load")

    # Step 3: Build a lookup for LineCCRDetails by CCR ID
    line_ccr_map = {lcd["ccr_id"]: lcd for lcd in line_ccr_qs}

    # Step 4: Construct the output
    ccrdetails = []
    for rd in route_details_qs:
        lcd = line_ccr_map.get(rd["ccr_id"], {})
        ccrdetails.append({
            "ccrid": rd["ccr_id"],
            "ccrgrp": rd["ccr_grp_id"],
            "pcQty": float(lcd.get("pending_ccr_qty") or 0),
            "pos": str(rd["position"]),
            "ol": float(lcd.get("order_load") or 0)
        })
    return ccrdetails


def adjust_order_loads_and_fol(old_ccrs, new_ccrs):
    old_ccr_fol_gaps = []
    new_ccr_order_load = []

    # Collect all ccr_ids we need
    old_ccr_ids = [ccr['ccrid'] for ccr in old_ccrs]
    new_ccr_ids = [ccr['ccrid'] for ccr in new_ccrs]
    all_ccr_ids = set(old_ccr_ids + new_ccr_ids)

    # Fetch masters and fol_data in bulk
    ccrs_data = CCRMaster.objects.filter(ccr_id__in=all_ccr_ids)
    fol_data = FOL_Data.objects.filter(ccr_id__in=all_ccr_ids).select_related("ccr")

    ccrs_map = {ccr.ccr_id: ccr for ccr in ccrs_data}
    fol_map = {fol.ccr_id: fol for fol in fol_data}

    # Handle old CCRs
    for ccr in old_ccrs:
        ccr_id = ccr['ccrid']
        ccr_data = ccrs_map.get(ccr_id)
        fol_data = fol_map.get(ccr_id)

        if not ccr_data or not fol_data:
            continue

        ol = ccr.get('ol')
        whpd = ccr_data.working_hours_per_day * 60
        if ol is not None and whpd not in (None, 0):
            fol_gap = Decimal(str(ol)) / whpd
            old_ccr_fol_gaps.append({
                'ccrname': ccr_data.ccr_name,
                'ccrid': ccr_data.ccr_id,
                'fol_gap': round(fol_gap, 2)
            })

    # Handle new CCRs
    for ccr in new_ccrs:
        ccr_id = ccr['ccrid']
        fol_data = fol_map.get(ccr_id)

        if not fol_data:
            continue

        increase = Decimal(str(ccr.get('ol', 0)))
        new_ccr_order_load.append({
            'ccrname' : fol_data.ccr.ccr_name,
            'ccrid' : fol_data.ccr.ccr_id,
            'order_load' :  round(increase, 2)
        }) 

    return old_ccr_fol_gaps, new_ccr_order_load


def get_ccr_fol_gap(route_id, new_ccr_details, order_key):
    prev_ccr_details = get_ccr_details_for_route(route_id,order_key)
    update_route_ccr_details = compare_ccr_routes(prev_ccr_details, new_ccr_details)
    replaced_ccr = update_route_ccr_details['replaced']
    old_ccrs = [old for _, old, _ in replaced_ccr]
    new_ccrs = [new for _, _, new in replaced_ccr]

    removed_ccr_fol_gap, added_ccr_order_load = adjust_order_loads_and_fol(old_ccrs, new_ccrs)
    return removed_ccr_fol_gap, added_ccr_order_load


def get_ccr_fol_gap_mapping():
    overall_bm_report_data_ids = (
        OverallBMReport.objects
        .filter(close_type_id__isnull=False)
        .values_list('order_key_id', flat=True)
    )

    # Get fol_gap summed by CCR 
    ccr_fol_gap_data = (
        OrderwiseFolGap.objects
        .exclude(order_key_id__in=overall_bm_report_data_ids)
        .values('ccr_id')
        .annotate(total_fol_gap=Sum('fol_gap'))
    )

    ccr_fol_gap_mapping = {
        row['ccr_id']: row['total_fol_gap'] for row in ccr_fol_gap_data
    }

    return ccr_fol_gap_mapping


def get_arithmetic_operations():
    order_load_operater = DBRSettings.objects.filter(flag =DBR_Settings.order_load_operator.value).values('value').first()
    if order_load_operater:
        op_code = order_load_operater.get('value','')
    else:
        op_code = '0'
    op_code = int(op_code)
    ops = {
        0: operator.mul,
        1: operator.truediv,
    }
    return ops.get(op_code,operator.mul)

def generate_scheduler_run_id(user_id):
    timestamp = now().strftime('%Y%m%d%H%M%S%f')  # precise timestamp
    unique_part = uuid.uuid4().hex[:6]  # short random string
    return f"RUN-{user_id}-{timestamp}-{unique_part}"

def get_last_successful_run_date():
    date = RunDateTime.objects.order_by('-run_date_success').first()
    if date and date.run_date_success:
        return date.run_date_success.date() # get only date and remove time stamp
    elif date and date.run_date:
        return date.run_date
    else:
        return datetime.today().date()
