from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from mto_app.common.commonfunctions import api_response, ExcelExportData, filter_order_data_by_params ,get_arithmetic_operations
from mto_app.models import (RouteDetails,CCRMaster,DailyWorkingCalendar,OrderData, OrderItemDetails,CCRItemTypeMapping, ReportConfiguration)
from datetime import date,datetime
import logging
from mto_app.utils import FutureOrderLoadChartEnum
import pandas as pd
from django.db.models import Q
import numpy as np
from mto_app.utils import DBR_Settings


logger = logging.getLogger(__name__)

class FutureOrderLoadCCRFOLHorizonDateView(APIView):
    @swagger_auto_schema(
    operation_description="Fetch the  Horizon Date for a given CCR.",
    )
    def get(self, request):
        try:
            ccr_horizon_details_map =   CCRMaster.objects.values('ccr_id','fol_horizon')
            ccr_horizon_details_map_df = pd.DataFrame(ccr_horizon_details_map, columns=['ccr_id', 'fol_horizon'])
            logger.info("Fetched the CCR horizon details from CCR Master table")

            working_calender_for_ccr = DailyWorkingCalendar.objects.filter(working_date__gte = date.today()).values('lno','ccr','working_date')
            working_calender_for_ccr_df = pd.DataFrame(working_calender_for_ccr, columns=['lno', 'ccr', 'working_date'])
            logger.info("Fetched the working calendar for all CCRs from today onwards")

            ccr_wise_latest_lno = working_calender_for_ccr.order_by('ccr','working_date').distinct('ccr')
            last_working_day_for_ccr = working_calender_for_ccr.order_by('ccr','-working_date').distinct('ccr')
            last_working_day_for_ccr_df = pd.DataFrame(last_working_day_for_ccr, columns=['lno','ccr', 'working_date'])
            ccr_wise_latest_lno_df = pd.DataFrame(ccr_wise_latest_lno, columns=['lno', 'ccr', 'working_date'])
            logger.info("Fetched the latest lno for all CCRs from working calendar")

            merged_ccr_details_df = pd.merge(ccr_wise_latest_lno_df, ccr_horizon_details_map_df, left_on='ccr', right_on='ccr_id', how='inner')
            merged_ccr_details_df['horizon_date_lno'] = merged_ccr_details_df['lno'] + merged_ccr_details_df['fol_horizon'] 
            merged_ccr_details_df = merged_ccr_details_df[['ccr','horizon_date_lno']]
            merged_ccr_details_df = merged_ccr_details_df.merge(working_calender_for_ccr_df, left_on=['ccr','horizon_date_lno'], right_on=['ccr','lno'], how='inner'
                                    , suffixes=('', '_horizon'))
            merged_ccr_details_df = merged_ccr_details_df[['ccr','working_date']]
            merged_ccr_details_df.rename(columns={'working_date': 'horizon_date'}, inplace=True)
            merged_ccr_details_df['horizon_date'] = merged_ccr_details_df['horizon_date'].fillna(
                merged_ccr_details_df['ccr'].map(
                    last_working_day_for_ccr_df.set_index('ccr')['working_date']
                )
            )
            ccr_horizon_date_details = merged_ccr_details_df.to_dict(orient='records')
            return api_response(data=ccr_horizon_date_details, msg = "Successfully fetched the CCR Horizon Date details", status_code=status.HTTP_200_OK)
        except Exception as e:
            return api_response(msg = f"Some Error has occurred in the Future Order load Chart CCR FOL Horizon Date API View due to {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)


class FutureOrderLoadChartAPIView(APIView):
    @swagger_auto_schema(
    operation_description="Fetch future order load chart data based on provided filters.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'loadwise': openapi.Schema(
                type=openapi.TYPE_INTEGER,
                description='Load wise flag (e.g. 0 or 1)'
            ),
            'view': openapi.Schema(
                type=openapi.TYPE_STRING,
                description='View type (e.g. daily, weekly, monthly)'
            ),
            'filters': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'ccr': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='CCR filter (e.g. specific CCR ID)'
                    ),
                    'orderOption': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Order option filter'
                    ),
                    'horizon_date' : openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format=openapi.FORMAT_DATE,
                        description='Horizon date in YYYY-MM-DD format'
                    ),
                    'from': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format=openapi.FORMAT_DATE,
                        description='Start date in YYYY-MM-DD format'
                    ),
                    'to': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        format=openapi.FORMAT_DATE,
                        description='End date in YYYY-MM-DD format'
                    )
                },
                required=['ccr', 'orderOption', 'from', 'to']
            )
        },
        required=['loadWise', 'view', 'filters']
    ),
    responses={
        200: openapi.Response(description="Successful response"),
        400: openapi.Response(description="Bad Request"),
        404: openapi.Response(description="Not Found"),
    }
)
    def post(self, request):
        try:
            data = request.data
            type =  data.get('loadwise',0) 
            view = data.get('view','daily') 
            filters = data.get('filters', {})
            ccr = None
            orderOption = ''
            from_date = ''
            to_date = ''
            horizon_date = ''
            export = int(request.GET.get('export', '0'))
            report_name = request.GET.get('report_name')
            headers = data.get('headers', [])
            export_param = bool(export)
            if filters is not None:
                ccr = filters.get('ccr',None)
                orderOption = filters.get('orderOption', '')
                from_date = filters.get('from', '')
                to_date = filters.get('to', '')
                horizon_date = filters.get('horizon_date', '')
                
            if ccr is None or from_date == '' or to_date == '' or orderOption == '' or horizon_date == '':
                return api_response(msg ="Please provide all required fields", status_code=status.HTTP_400_BAD_REQUEST)
            
            # converting the date got from the request
            from_date = date.fromisoformat(from_date)
            to_date = date.fromisoformat(to_date)
            horizon_date = date.fromisoformat(horizon_date) if horizon_date != '' else None
            
            # getting the order load operation based on dbr settings
            order_load_operation = get_arithmetic_operations()

            # fetched the route details for ccr informations and route information
            routes_details_list = RouteDetails.objects.filter(ccr=ccr).values_list('route')
            logger.info("Fetched all the route ids where the ccr is used")

            #fetching the ccr master details for getting the ccr whose ddata need to be showed
            ccr_master_details = CCRMaster.objects.prefetch_related('ccr_group').filter(ccr_id = ccr).values('ccr_id','ccr_group','working_hours_per_day',
                                 'fol_horizon','ccr_name').first()
            if not ccr_master_details:
                return api_response(msg = "No CCR details found for the selected CCR", status_code=status.HTTP_400_BAD_REQUEST)
            ccr_group_id = ccr_master_details.get('ccr_group', None)
            fol_horizon = ccr_master_details.get('fol_horizon', 0)
            ccr_name = ccr_master_details.get('ccr_name', '')
            working_hours_per_day = ccr_master_details.get('working_hours_per_day', None)
            
            # getting the working calender for the ccr
            working_calender_for_ccr = DailyWorkingCalendar.objects.filter(ccr=ccr, working_date__gte = from_date , working_date__lte = to_date).values('lno'
                                        ,'ccr','working_date')
            logger.info("Fetched the working calendar for the ccr from today onwards")
            working_calender_for_ccr_df = pd.DataFrame(working_calender_for_ccr, columns=['lno', 'ccr', 'working_date'])

            # function call for the order data to be get from the Order Data model for the order load and pending qty calculation
            order_data = self.get_order_data(routes_details_list,orderOption,from_date,to_date, filter_data = data)
            order_data = order_data.values('order_key', 'due_date', 'expected_due_date', 'route')
            if not order_data:
                return api_response(msg = "No order data found for the selected filters", status_code=status.HTTP_200_OK)
            
            order_keys = order_data.values_list('order_key', flat=True).distinct()

            # getting the order item details on whose pending qty and load need to be calculated
            order_item_details = OrderItemDetails.objects.filter(order__in = order_keys, ccr_group = ccr_group_id).prefetch_related('item_code').values('order'
                                ,'item_code','ccr_group','pending_qty','item_code__item_type')            
            
            touch_time_query = Q()
            for item in order_item_details:
                touch_time_query |= Q(item_type=item['item_code__item_type'], ccr = ccr)
            
            # getting the touch time of the ccr and item type
            touch_time_details = CCRItemTypeMapping.objects.filter(touch_time_query).values('item_type','touch_time_in_mins','batch_size')
            touch_time_details_df = pd.DataFrame(touch_time_details, columns=['item_type', 'touch_time_in_mins', 'batch_size'])
            touch_time_details_df['working_hours_per_day'] = working_hours_per_day
            order_data_df = pd.DataFrame(order_data, columns=['order_key', 'due_date', 'expected_due_date', 'route'])
            order_item_details_df = pd.DataFrame(order_item_details, columns=['order', 'item_code', 'ccr_group', 'pending_qty','item_code__item_type'])
            
            # merging the order data and item details to get the route for each item
            order_item_details_df = order_item_details_df.merge(order_data_df , left_on='order', right_on='order_key', how='left', suffixes=('', '_order'))
            
            # Function to calculate the date wise load based on the type
            date_df  , pastorder_load = self.get_date_wise_load(order_item_details_df , working_calender_for_ccr_df ,touch_time_details_df , from_date , to_date,
                                        orderOption , type,ccr , horizon_date , ccr_name , order_load_operation)
            if date_df is None:
                return api_response(msg = "Error in processing the data", status_code=status.HTTP_400_BAD_REQUEST)
            
            # creating a record for past order load 
            past_order_row = {'date': pd.Timestamp(from_date), 'load': pastorder_load, 'is_holiday': False, 'tag': FutureOrderLoadChartEnum.PastScheduling.value,
                             'ccr': int(ccr),'clr': FutureOrderLoadChartEnum.Red.value , 'ccr_name' : ccr_name}
            
            # appending the past order record into the date df
            date_df = pd.concat([date_df.iloc[:0], pd.DataFrame([past_order_row]), date_df.iloc[0:]]).reset_index(drop=True)
            date_df = date_df[['tag','date','ccr','load','is_holiday','clr','ccr_name']]
            
            # generating the data based on the view type i.e daily , weekly , monthly
            date_df =  self.generate_view_type(date_df , view)
            if isinstance(date_df, str):
                return api_response(msg = date_df, status_code=status.HTTP_400_BAD_REQUEST)

            if date_df is None:
                return api_response(msg = "Error in generating the view type", status_code=status.HTTP_400_BAD_REQUEST)
            
            response = date_df.to_dict(orient='records')

            if export_param:
                return ExcelExportData(response, report_name, name_of_report_parent=report_name ,headers=headers)
            return api_response(data={'pastorder_load':pastorder_load , 'fol_horizon' : fol_horizon , 'data':response}, msg = "Successfully fetched the Future Order Load Chart details", status_code=status.HTTP_200_OK)
            
        except Exception as e:
            return api_response(msg = f"Some Error has occurred in the Future Order load Chart API View due to {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)
    
    def get_date_wise_load(self , order_item_details_df : pd.DataFrame , working_calender_for_ccr_df : pd.DataFrame , touch_time_details_df : pd.DataFrame 
                           ,from_date , to_date, orderOption , type,ccr, horizon_date , ccr_name , order_load_operation):
        try:
            # converting the horizon date into required format
            horizon_date = (pd.to_datetime(horizon_date)
                            if isinstance(horizon_date, str)
                            else pd.Timestamp(horizon_date))  

            # creating all the dates from the start to end date           
            date_range = pd.date_range(start=from_date, end=to_date, freq="D")
            today_ts = pd.Timestamp(date.today())
            date_df = pd.DataFrame({"date": date_range})

            # calculating the load wether pending qty wise or order load wise based on order load operation
            if type == FutureOrderLoadChartEnum.LoadWise.value:
                order_item_details_df = order_item_details_df.merge(touch_time_details_df , left_on='item_code__item_type', right_on='item_type', how='left')
                condition = ((order_item_details_df['touch_time_in_mins'].notnull()) & (order_item_details_df['touch_time_in_mins'] > 0))
                order_item_details_df = order_item_details_df.loc[condition]
                order_item_details_df['batch_size'] = order_item_details_df['batch_size'].fillna(1)
                order_item_details_df['load'] = (order_load_operation((order_item_details_df['pending_qty'] / order_item_details_df['batch_size']) , order_item_details_df['touch_time_in_mins']) / 
                                                (order_item_details_df['working_hours_per_day'] * 60))
            else:
                order_item_details_df['load'] = order_item_details_df['pending_qty']
            
            pastorder_load = 0
            if orderOption == FutureOrderLoadChartEnum.AllNotSchedule.value:
                past_orders = order_item_details_df.loc[order_item_details_df['expected_due_date'] < from_date]
                pastorder_load = past_orders['load'].sum()
            
            # separating the data from the past order and current orders
            order_item_details_df = order_item_details_df.loc[order_item_details_df['expected_due_date'] >= from_date]
            
            # aggregating the load based on the expected due date of the orders
            order_item_details_df = order_item_details_df.groupby('expected_due_date').agg({'load':'sum'}).reset_index()
            order_item_details_df['expected_due_date'] = pd.to_datetime(order_item_details_df['expected_due_date'])
            date_df = date_df.merge(order_item_details_df , left_on='date', right_on='expected_due_date', how='left')
            date_df['load'] = date_df['load'].fillna(0).astype(float)
            date_df['load'] = np.round(date_df['load'], 4)
            working_calender_for_ccr_df['working_date'] = pd.to_datetime(working_calender_for_ccr_df['working_date'])
            date_df = date_df.merge(working_calender_for_ccr_df , left_on='date', right_on='working_date', how='left')
            
            # adding the is holiday variable wether the particular day is holiday or not
            date_df['is_holiday'] = date_df['working_date'].isna()
            tag_conditions  = [date_df['date'] > horizon_date , (date_df['date'] <= horizon_date) & (date_df['date']>=today_ts)]
            tag_values = [FutureOrderLoadChartEnum.BeyondScheduling.value , FutureOrderLoadChartEnum.WithinScheduling.value]
            date_df['tag'] = np.select(tag_conditions, tag_values, default=FutureOrderLoadChartEnum.PastScheduling.value)

            color_conditions = [date_df['tag'] == FutureOrderLoadChartEnum.PastScheduling.value ,date_df['tag'] == FutureOrderLoadChartEnum.WithinScheduling.value ,
                                date_df['tag'] == FutureOrderLoadChartEnum.BeyondScheduling.value]
            color_values = [FutureOrderLoadChartEnum.Red.value , FutureOrderLoadChartEnum.Grey.value , FutureOrderLoadChartEnum.White.value]
            
            # attaching the tags to the rows that wether the day is within or beyond schedule horizon
            date_df['clr'] = np.select(color_conditions, color_values, default=FutureOrderLoadChartEnum.White.value)
            date_df['ccr'] = date_df['ccr'].fillna(ccr)
            date_df['ccr'] = date_df['ccr'].astype(int)
            date_df['ccr_name'] = ccr_name
            return date_df , pastorder_load
        except Exception as e:
            return None , None

    def get_order_data(self,routes_details_list,orderOption,from_date,to_date,filter_data):
        try:
            # fetching the condition based on the orderOption
            order_condition = self.get_order_condition(orderOption, from_date, to_date )
            if order_condition is None:
                return None
            order_data = OrderData.objects.filter(route__in=routes_details_list, **order_condition).values('order_id', 'line_id', 'order_key', 'item__attributes', 'item__item_code',
                'item__item_description', 'item__item_type__item_type','item__item_type__item_type_id', 'total_qty',
                'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                'computed_dd','order_attributes','line_order_attributes','vf_order_type','due_date')
            order_data = filter_order_data_by_params(order_data, filter_data)
            return order_data
        except Exception as e:
            logger.info("Error in fetching order data due to %s", str(e))
            return None

    def get_order_condition(self , orderOption, from_date, to_date ):
        try:
            # condition of the two types of view
            conditional_map={
                FutureOrderLoadChartEnum.NotScheduleBeyondFOLHorizon.value : {'expected_due_date__gt' : from_date,'expected_due_date__lte': to_date , 
                                                                            'due_date__isnull': True},
                FutureOrderLoadChartEnum.AllNotSchedule.value : {'expected_due_date__lte': to_date , 'due_date__isnull': True},
                }
            return conditional_map.get(orderOption,None)
        except Exception as e:
            logger.info("Error in fetching order condition due to %s", str(e))
            return None

    def ordinal(self,n):
        if 11 <= n % 100 <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"

    def generate_view_type(self , date_df : pd.DataFrame,view):
        try:
            report_configuration = ReportConfiguration.objects.filter(report_name=FutureOrderLoadChartEnum.FutureOrderLoadWeekEndDay.value).first()
            if report_configuration and report_configuration.flag:
                week_end = report_configuration.flag
            else:
                return "Please configure the week end day in Report Configuration for Future Order Load Week"
            df = pd.DataFrame()
            date_df['load'] = date_df['load'].astype(float)
            if view == FutureOrderLoadChartEnum.daily.value:
                date_df['date'] = date_df['date'].dt.date
                date_df = date_df[['tag','date','ccr','load','ccr_name']]
                date_df.drop(columns=['ccr'], inplace=True)
                date_df.rename(columns={'ccr_name':'ccr'}, inplace=True)
                return date_df
            elif view == FutureOrderLoadChartEnum.weekly.value:
                df = (
                    date_df
                    .groupby(
                        [
                            "ccr",
                            pd.Grouper(key="date", freq=f"W-{week_end}") 
                        ],
                        as_index=False
                    ).agg({
                        "load": "sum",
                        "tag":  lambda s: list(set(s)),   # unique tags as list
                        'ccr_name': 'first'
                    })
                )
                
                df.rename(columns={"date": "week_end"}, inplace=True)
                df["week_start"] = (df["week_end"] - pd.Timedelta(days=6)).dt.date
                df["week_end"] = df["week_end"].dt.date

                df['week_start_str'] = df["week_start"].apply(
                    lambda d: f"{self.ordinal(d.day)} {d.strftime('%b')}"
                )
                df['week_end_str'] = df["week_end"].apply(
                    lambda d: f"{self.ordinal(d.day)} {d.strftime('%b')}"
                )
                df['date'] = df['week_start_str'] + ' - ' + df['week_end_str']

            elif view == FutureOrderLoadChartEnum.monthly.value:
                df = (
                    date_df
                    .groupby(
                        [
                            "ccr",
                            pd.Grouper(key="date", freq="MS")  
                        ],
                        as_index=False
                    ).agg({
                            "load": "sum",
                            "tag":  lambda s: list(set(s)),      # unique tags as list
                            'ccr_name': 'first'
                        })
                )
                df.rename(columns={"date": "month_start"}, inplace=True)
                df["month_end"] = df["month_start"] + pd.offsets.MonthEnd(0)
                df["month_end"]   = df["month_end"].dt.date
                df['date'] = df['month_start'].dt.strftime('%b %y')
            if not df.empty:    
                df = df[['tag','date','ccr','load','ccr_name']]
                df.drop(columns=['ccr'], inplace=True)
                df.rename(columns={'ccr_name':'ccr'}, inplace=True)
                return df            
            return None 
        except Exception as e:
            return None