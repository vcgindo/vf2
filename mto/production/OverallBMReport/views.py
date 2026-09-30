import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response, CustomExcelExport)
from mto_app.common.commonfunctions import  MTOPagination
from mto_app.utils import   eReportName, eChildName
from ..Common.views import  BomLevelExplosionForExcelExportView
from ..DeptWiseBMReport.views import DeptWiseBMReportView , DepartmentWiseWIPForOrdersView

logger = logging.getLogger(__name__)

class OverAllBMReportView(APIView):
    @swagger_auto_schema(
        operation_description='Get combined department-wise BM report and WIP data',
        manual_parameters=[
            openapi.Parameter('avawip', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Order with full WIP', required=True),
            openapi.Parameter('page', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Page number'),
            openapi.Parameter('page_size', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Page size'),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Set to 1 to export to Excel'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: openapi.Response(description="Bad Request"),
            500: openapi.Response(description="Internal Server Error"),
        }
    )
    def put(self, request):
        try:
            avawip = request.GET.get('avawip')
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else False
            data  = request.data
            page = int(request.GET.get('page'))
            page_size = int(request.GET.get('page_size'))
                       
            if data: 
                headers = data.get('headers',{})
            
            isBomExplosion_param = request.GET.get('isBomExplosion')
            isBomExplosion = bool(int(isBomExplosion_param)) if isBomExplosion_param else False

            report_name = request.GET.get('report_name')
            
            data = request.data
            headers = data.get('headers', {}) if data else {}
            if avawip is None:
                return api_response(msg='avawip parameter is required', status_code=status.HTTP_400_BAD_REQUEST)

            all_data = 1

            bm_report_view = DeptWiseBMReportView()
            bm_report_request = request
            bm_report_request.GET = request.GET.copy()
            bm_report_request.GET['alldata'] = all_data
            bm_report_request.GET['avawip'] = request.GET.get('avawip')
            bm_report_request.GET['analytics'] = request.GET.get('analytics')
            bm_report_request.GET['page'] = page
            bm_report_request.GET['page_size'] = page_size
            bm_report_request.GET['export'] = export
            bm_report_response = bm_report_view.put(request=bm_report_request)

            if bm_report_response.status_code != status.HTTP_200_OK:
                raise Exception("BM report data fetching failed")

            bm_report_data = bm_report_response.data.get('data', [])
            if not bm_report_data:
                return api_response(msg='No record found for the data', status_code=status.HTTP_200_OK)
            order_keys = [order['ok'] for order in bm_report_data.get('result',[])]
            if not order_keys:
                return api_response(msg='No record found for the data', status_code=status.HTTP_200_OK)

            dept_wip_view = DepartmentWiseWIPForOrdersView()
            dept_wip_request = request._request
            dept_wip_request.POST = dept_wip_request.POST.copy()
            dept_wip_request.POST.update({'ok': order_keys})
            dept_wip_response = dept_wip_view.post(request=dept_wip_request)

            if dept_wip_response.status_code != status.HTTP_200_OK:
                raise Exception("WIP data fetching failed")

            dept_wip_data = dept_wip_response.data.get('data', {})
            combined_data = []
            
            for order in bm_report_data.get('result'):
                order_key = order.get('ok')
                wip_info = dept_wip_data.get(order_key, {})
                combined_data.append({
                    **order,
                    'ddtl': wip_info,
                })
            
            if export_param and headers:
                order_ids = []
                line_ids = []
                if isBomExplosion:
                    for item in combined_data:
                        order_id = item.get('oid')
                        line_id = item.get('lid')
                        order_ids.append(order_id)
                        line_ids.append(line_id)
                        # if not order_id or not line_id:
                    bom_explosion_view = BomLevelExplosionForExcelExportView()
                    bom_query_dict  = request
                    bom_query_dict.data['oids'] = order_ids
                    bom_query_dict.data['lids'] = line_ids
                    bom_reponse = bom_explosion_view.post(request=bom_query_dict)
                    if bom_reponse.status_code == status.HTTP_200_OK:
                        bom_explosion_data = bom_reponse.data.get('data',{})
                    else:
                        bom_explosion_data = {}

                    if bom_explosion_data :
                        for item in combined_data:
                            rm_key = (item.get('oid'),item.get('lid'))
                            item['bomexplosion'] = bom_explosion_data.get(rm_key,[])

                
                return CustomExcelExport(
                    combined_data,
                    report_name,
                    headers,
                    isGrouped=True,
                    isChildren=isBomExplosion,
                    child_element=eChildName.bomexplosion.value,
                    name_of_report_parent=eReportName.bm_report.value,
                    name_of_report_child=eReportName.bom_explosion.value
                )

            paginator = MTOPagination()
            paginated_response_data = paginator.create_paginated_response( request , combined_data, bm_report_data.get('nop'), bm_report_data.get('count') )
            return api_response(
                data = paginated_response_data,
                msg="OverAll BM report and WIP data fetched successfully",
                status_code=status.HTTP_200_OK
            )

        except Exception as ex:
            logger.info(f'An Exception has occurred in the overall BM report API due to {str(ex)}')
            return api_response(msg=f'An Exception has occurred: {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)

