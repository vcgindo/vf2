from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializer.issue_report_serializer import IssueReportSerializer, IssueReportComponent, IssueReportType
from api.error_code import AuthCode
from api.docs.auth import *
from common.http_status_code import HttpStatusCode

class IssueReportView(APIView):
    permission_classes = [IsAuthenticated]

    @issue_report_doc()
    def post(self, request, *args, **kwargs):
        serializer = IssueReportSerializer(data=request.data, context=request.user)
        if serializer.is_valid():
            serializer.save()
            return Response(AuthCode.REPORT_SUCCESS, status=HttpStatusCode.OK)
        return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)

    @get_issue_report_doc()
    def get(self, request, *args, **kwargs):
        data = {
            'issue_component': IssueReportComponent.get_component(),
            'issue_type': IssueReportType.get_choices()
        }
        return Response(data, status=HttpStatusCode.OK)
