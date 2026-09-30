from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from api.serializer.auth import *
from api.serializer.role import *
from api.serializer.profile import *
from api.models import *
from api.core import ResponseUser
from common.http_status_code import HttpStatusCode
from api.docs.auth import *
from api_gateway.service_config.config import service_map

class RolesView(APIView):
    permission_classes = [IsAuthenticated]

    @role_doc()
    def get(self, request, format=None):
        user_data = UserProfileSerializer(request.user)
        resutl = ResponseUser(
            user=user_data.data,
            url_permission=True,
            response_user=False,
            response_data=False,
            role_full=True,
        )
        return Response(
            {"data": resutl.response(msg="Successful")}, status=HttpStatusCode.OK
        )


class GetAllRolesView(APIView):
    # permission_classes = [IsAuthenticated]

    @all_role_doc()
    def get(self, request, format=None):
        from api.serializer.profile import Permission as PermissionSerializer
        from api.serializer.profile import Features as FeatureSerializer

        active_application_ids = [application['application_id'] for application in service_map.values() if application.get('active') == True]
        data = []
        role = Roles.objects.filter(application_id__in = active_application_ids,is_visible = True)
        for item in role:
            serializer = RolesSerializer(item)
            application = ApplicationMaster.objects.get(application_id=serializer.data['application_id'])
            permissions = item.permission_id.all()
            permission_list = []
            features = item.feature_id.all()
            feature_list = []
            for permission in permissions:
                permission_serializer = PermissionSerializer(permission)
                permission_list.append(permission_serializer.data)
            
            for feature in features:
                feature_serializer = FeatureSerializer(feature)
                feature_list.append(feature_serializer.data)

            role_obj = serializer.data.copy()
            role_obj['application_name'] = application.application_name
            role_obj['urls'] = permission_list
            role_obj['features'] = feature_list
            data.append(role_obj)
        return Response(data, status=HttpStatusCode.OK)

class GetAllApplications(APIView):
    # permission_classes = [IsAuthenticated]

    @all_applications_doc()
    def get(self, request, format=None):
        data = []
        applications = ApplicationMaster.objects.all()
    
        for application in applications:
            serializer = ApplicationSerializer(application)
            data.append(serializer.data)
        return Response(data, status=HttpStatusCode.OK)

class GetAllFunctions(APIView):
    # permission_classes = [IsAuthenticated]

    @all_functions_doc()
    def get(self, request, format=None):
        from api.models import Permission as PermissionModel
        from api.serializer.profile import Permission as PermissionSerializer
        data = []
        permissions = PermissionModel.objects.all()
    
        for permission in permissions:
            serializer = PermissionSerializer(permission)
            data.append(serializer.data)
        return Response(data, status=HttpStatusCode.OK)

class AddFunction(APIView):
    # permission_classes = [IsAuthenticated]

    @add_function_doc()
    def post(self, request, format=None):
        # from api.models import Permission as PermissionModel
        from api.serializer.profile import Permission as PermissionSerializer
        permissions_data = request.data['data']
        if not isinstance(permissions_data, list):
            return Response({"error": "Invalid data format. Expected a list of permissions."}, status=status.HTTP_400_BAD_REQUEST)
        
        created_permissions = []
        for permission_data in permissions_data:
            # Check if permission with the same name or code already exists
            if Permission.objects.filter(name=permission_data['url']).exists():
                continue  # Skip this entry if it already exists
            
            # Create a new permission
            total_objects = Permission.objects.count() + 1
            permission_data['id'] = total_objects
            serializer = PermissionSerializer(data=permission_data)
            if serializer.is_valid():
                serializer.save()  # Save the new permission to the database
                created_permissions.append(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(created_permissions, status=HttpStatusCode.OK)

class DeleteFunction(APIView):
    def delete(self, request, id, format=None):
        try:
            # Attempt to retrieve the permission by ID
            permission = Permission.objects.get(id=id)
            permission.delete()  # Delete the permission
            return Response({"message": "Permission deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Permission.DoesNotExist:
            # If permission with the given ID does not exist, return 404
            return Response({"error": "Permission not found."}, status=status.HTTP_404_NOT_FOUND)

class AddRole(APIView):
    # permission_classes = [IsAuthenticated]

    # @add_role_doc()
    def post(self, request, format=None):
        roles = request.data['data']
      
        if not isinstance(roles, list):
            return Response({"error": "Invalid data format. Expected a list of permissions."}, status=status.HTTP_400_BAD_REQUEST)
        
        created_permissions = []
        for role in roles:
            # Check if permission with the same name or code already exists
            if Roles.objects.filter(name=role['name']).exists():
                continue  # Skip this entry if it already exists

            url_ids = [url['id'] for url in role['urls']]
            total_objects = Roles.objects.count() + 1
            role['id'] = total_objects
            serializer = RolesSerializer(data=role)
            if serializer.is_valid():
                serializer.save()  # Save the new permission to the database
                created_permissions.append(serializer.data)
                for id in url_ids:
                    permission = Permission.objects.get(id=id)
                    permission.role_id.add(serializer.data['id'])          
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(created_permissions, status=HttpStatusCode.OK)


class DeleteRole(APIView):
    def delete(self, request, id, format=None):
        try:
            # Attempt to retrieve the role by ID
            role = Roles.objects.get(id=id)
            # Uncomment the following line to delete the role
            role.delete()  
            return Response({"message": "Role deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Roles.DoesNotExist:  # Catch Roles.DoesNotExist specifically
            # If role with the given ID does not exist, return 404
            return Response({"error": "Role not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # General exception handling for any other unexpected errors
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class EditRole(APIView):
    # permission_classes = [IsAuthenticated]

    # @add_role_doc()
    def put(self, request, format=None):
        role_data = request.data
        url_ids = [url['id'] for url in role_data['urls']]
        if Roles.objects.filter(id=role_data['id']).exists():
            role_instance = Roles.objects.get(id=role_data['id'])
            
            if Roles.objects.filter(name=role_data['name']).exclude(id=role_instance.id).exists():
                return Response({"msg":"Role Name Already Exists"}, status=status.HTTP_400_BAD_REQUEST)

            role_instance.name = role_data['name']
            role_instance.application_id = role_data['application_id']
            role_instance.code = role_data['code']
            role_instance.description = role_data['description']
            role_instance.save()
            role_instance.permission_id.clear()
            permissions = Permission.objects.filter(id__in=url_ids)

            role_instance.permission_id.add(*permissions)
            return Response({"msg":"Role Details Updated Successfully"}, status=HttpStatusCode.OK)
        return Response({"msg":"Role Does not Exist"}, status=status.HTTP_400_BAD_REQUEST)
