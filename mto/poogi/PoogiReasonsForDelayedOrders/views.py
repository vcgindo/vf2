
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import CustomPagination, ExcelExportData, api_response, filter_order_data_by_params,  GetUserDetails, DataPermissionFilterForOrderData
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Count
from mto_app.models import OrderData,POOGIMajorReason,POOGIMinorReason,ClosedOrders
import logging
from datetime import date
from django.db.models import IntegerField, Case, When
from django.db import transaction
from mto_app.utils import  eReportName

# Create your views here.


logger = logging.getLogger(__name__)

class GetDelayedOrdersForPoogiReasonAssignmentView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description='Get delayed orders for POOGI reason assignment',
        manual_parameters=[
            openapi.Parameter('isAssigned', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='get orders based on POOGI reason assigned or not', required=True),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'),
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        return self.getdelayedOrderForPoogiReasondata(request)

    def put(self, request):
        return self.getdelayedOrderForPoogiReasondata(request, method='PUT')

    def getdelayedOrderForPoogiReasondata(self, request, method='GET'):
        try:
            headers = None
            if method == 'PUT':
                data = request.data
                headers = data.get('headers', {}) if data else None
            else:
                data = None
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None
            report_name = request.GET.get('report_name')

            isAssigned = request.GET.get('isAssigned')
            if isAssigned is None:
                return api_response(msg='isAssigned parameter is required', status_code=status.HTTP_400_BAD_REQUEST)

            filter_condition = {'major_reason__isnull': True} if not bool(int(isAssigned)) else {}
            filter_history_condition = {'major_reason__isnull': True} if not bool(int(isAssigned)) else {}

            filter_data = request.data
            colors_of_orders = ['Black']
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            order_data = OrderData.objects.filter(**filter_condition, color__in=colors_of_orders).values(
                'order_id', 'line_id', 'order_key', 'item', 'ccr__ccr_id', 'item__item_description',
                'item__item_code', 'plant', 'plant__plant_name', 'due_date', 'planned_release_date',
                'actual_released_date', 'bpp', 'total_qty', 'customer__cust_name', 'customer__cust_code',
                'major_reason', 'minor_reason', 'allocated_fg', 'vf_order_type', 'color', 'dept__dept_id',
                'order_attributes', 'line_order_attributes', 'computed_line_attributes'
            )
            logger.info('Fetched the data for the delayed orders')
            order_data = DataPermissionFilterForOrderData(order_data, product_permissions, location_permissions, is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            order_data = filter_order_data_by_params(order_data, filter_data)

            closed_order_data = ClosedOrders.objects.filter(**filter_history_condition, color__in=colors_of_orders).values(
                'order_id', 'line_id', 'order_key', 'item', 'ccr__ccr_id', 'item__item_description',
                'item__item_code', 'plant', 'plant__plant_name', 'due_date', 'planned_release_date',
                'actual_released_date', 'bpp', 'total_qty', 'customer__cust_name', 'customer__cust_code',
                'major_reason', 'minor_reason', 'allocated_fg', 'closure_date', 'vf_order_type', 'color', 'dept__dept_id',
                'order_attributes', 'line_order_attributes', 'computed_line_attributes'
            )
            logger.info('Fetched the order history data')
            closed_order_data = DataPermissionFilterForOrderData(closed_order_data, product_permissions, location_permissions, is_admin)
            logger.info('Filtered the closed order data based on the permissions of the user')

            closed_order_data = filter_order_data_by_params(closed_order_data, filter_data)

            # Combine order data
            result = [self.create_combined_data(data, order_status="Open") for data in order_data]
            result.extend([self.create_combined_data(data, order_status="Close") for data in closed_order_data])

            # Sort the result by BPP
            sorted_data = sorted(result, key=lambda x: x['bpp'], reverse=True)

            if export_param:
                if report_name and headers:
                    return ExcelExportData(sorted_data, report_name, eReportName.reasonForDelayedOrder.value, headers)
                else:
                    return api_response(msg='Report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(sorted_data, request)
            return paginator.get_paginated_response(paginated_response_data, msg='Data fetched successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.info(f'An exception occurred in the POOGI delayed orders view due to: {str(ex)}')
            return api_response(msg=f'An exception occurred in the POOGI delayed orders view due to: {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)

    def create_combined_data(self, data, order_status="Open"):
        combined_data = {
            'oid': data['order_id'],
            'lid': data['line_id'],
            'ok': data['order_key'],
            'cl': data['color'],
            'it': data['item'],
            'ic': data['item__item_code'],
            'ot': data['vf_order_type'],
            'pid': data['plant'],
            'pln': data['plant__plant_name'],
            'dd': data['due_date'],
            'prd': data['planned_release_date'],
            'bpp': data['bpp'] if data['bpp'] is not None else 0,
            'os': order_status,
            'afg': data['allocated_fg'] if data['allocated_fg'] else 'NA',
            'ed': (data['closure_date'] - data['actual_released_date']).days if order_status == "Close" and data.get('closure_date') else abs((date.today() - data['actual_released_date']).days) if data['actual_released_date'] else 0,
            'rdd': (data['actual_released_date'] - data['planned_release_date']).days if data['actual_released_date'] and data['planned_release_date'] else 0,
            'qdd': (data['closure_date'] - data['due_date']).days if order_status == "Close" and data.get('closure_date') else (date.today() - data['due_date']).days if data['due_date'] else 0,
            'tq': data['total_qty'],
            'cn': data['customer__cust_name'],
            'cc': data['customer__cust_code'],
            'maj': data['major_reason'],
            'min': data['minor_reason'],
            'r': []
        }
        line_attr = data['line_order_attributes']
        if line_attr:
            combined_data.update(line_attr)
        
        # Update combined_data with order_attributes
        order_attr = data['order_attributes']
        if order_attr:
            combined_data.update(order_attr)
        
        comp_line_attr = data['computed_line_attributes']
        if comp_line_attr:
            combined_data.update(comp_line_attr)

        return combined_data

#get Analytics data for the Delayed orders for poogi reason assignment
class GetPoogiReasonsForDelayedOrdersAnalyticsDataView(APIView):
    @swagger_auto_schema(
        operation_description='Get the analytics data for the delayed order for poogi reason assignment',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            order_counts = OrderData.objects.aggregate(
            total_count = Count('order_id'),
            unassigned=Count(Case(When(major_reason__isnull=True, then=1), output_field=IntegerField())),
            assigned=Count(Case(When(major_reason__isnull=False, then=1), output_field=IntegerField()))
            )
            logger.info('Data for unassigned poogi reasons from order data is fetched')

            closed_order_counts = ClosedOrders.objects.aggregate(
            total_count = Count('order_id'),
            unassigned=Count(Case(When(major_reason__isnull=True, then=1), output_field=IntegerField())),
            assigned=Count(Case(When(major_reason__isnull=False, then=1), output_field=IntegerField()))
            )
            logger.info('Data for unassigned poogi reasons from closed orders is fetched')
            result = {}
            if order_counts:
                result['open'] = order_counts
            if closed_order_counts:
                result['closed'] = closed_order_counts
            return api_response(data=result,msg='The data has been fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the get analytics view due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the get analytics view due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)


class AssignPoogiReasonForOrdersView(APIView):
    @swagger_auto_schema(
        operation_description='Assign the poogi reasons for the selected orders',
        request_body=openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                            'ok' : openapi.Schema(type=openapi.TYPE_STRING,description='order key'),
                            'majid' : openapi.Schema(type=openapi.TYPE_INTEGER,description='major reason id'),
                            'minid' : openapi.Schema(type=openapi.TYPE_INTEGER,description='minor reason id')
                    }
                )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self,request):
        try:
            data = request.data.get('data')
            order_keys = [order['ok'] for order in data]
            major_reasons_ids = [order['majid'] for order in data]
            min_reasons_ids = [order['minid'] for order in data]
            order_data_instances = OrderData.objects.filter(order_key__in = order_keys)
            order_data_dictionary = {order.order_key : order for order in order_data_instances}
            logger.info('Fetched order data instances')

            closed_order_data_instances = ClosedOrders.objects.filter(order_key__in = order_keys)
            closed_order_dictionary = {order.order_key : order for order in closed_order_data_instances}
            logger.info('Fetched order history instances')

            major_reasons_instance_dictionary = {data.major_reason_id : data for data in POOGIMajorReason.objects.filter(major_reason_id__in = major_reasons_ids)}
            minor_reasons_instance_dictionary = {data.minor_reason_id : data for data in POOGIMinorReason.objects.filter(minor_reason_id__in = min_reasons_ids)}
            
            order_data_to_be_updated = []
            closed_order_to_be_updated = []

            for data in data:
                order_key = data['ok']
                order_instance = order_data_dictionary.get(order_key,{})
                closed_order_instance = closed_order_dictionary.get(order_key,{})
                if order_instance:
                    order_instance.major_reason = major_reasons_instance_dictionary.get(data['majid'])
                    order_instance.minor_reason = minor_reasons_instance_dictionary.get(data['minid'])
                    order_data_to_be_updated.append(order_instance)
                elif closed_order_instance:
                    closed_order_instance.major_reason = major_reasons_instance_dictionary.get(data['majid'])
                    closed_order_instance.minor_reason = minor_reasons_instance_dictionary.get(data['minid'])
                    closed_order_to_be_updated.append(closed_order_instance)
            
            fields_for_data = {
                'major_reason',
                'minor_reason'
            }
            
            with transaction.atomic():
                if order_data_to_be_updated:
                    OrderData.objects.bulk_update(order_data_to_be_updated,fields_for_data)
                if closed_order_to_be_updated:
                    ClosedOrders.objects.bulk_update(closed_order_to_be_updated,fields_for_data)

            return api_response(msg="Poogi Reason has been saved successfully",status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An exception has occurred while saving the poogi reasons due to following exception {str(ex)}')
            return api_response(msg=f'An exception has occurred while saving the poogi reasons due to following exception {str(ex)}',status_code=status.HTTP_200_OK)

class PoogiMajorMinorReasonMasterView(APIView):
    @swagger_auto_schema(
        operation_description='Get all the major minor reason for poogi',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            poogi_major_reasons = POOGIMajorReason.objects.prefetch_related('poogi_minor_reason_poogi_major_reason').values('major_reason_id','major_reason_code','major_reason_desc','plant',
            'poogi_minor_reason_poogi_major_reason__minor_reason_id', 'poogi_minor_reason_poogi_major_reason__minor_reason_code', 'poogi_minor_reason_poogi_major_reason__minor_reason_desc')
            logger.info('All the major and minor reasons fetched for the plants')

            response = {}
            for data in poogi_major_reasons:
                if data['plant'] not in response:
                    response[data['plant']] = {}
                if data['major_reason_id'] not in response[data['plant']]:
                    response[data['plant']][data['major_reason_id']] = {
                        'majid' : data['major_reason_id'],
                        'majd' : data['major_reason_desc'],
                        'min' : []
                    }
                response[data['plant']][data['major_reason_id']]['min'].append({
                    'minid' : data['poogi_minor_reason_poogi_major_reason__minor_reason_id'],
                    'minc' : data['poogi_minor_reason_poogi_major_reason__minor_reason_code'],
                    'mind' : data['poogi_minor_reason_poogi_major_reason__minor_reason_desc']
                })
            return api_response(data=response,msg="Poogi reason data has been fetched successfully",status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An exception has ouccured in get poogi reasons api due to {str(ex)}')
            return api_response(msg=f'An exception has ouccured in get poogi reasons api due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

      