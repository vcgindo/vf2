from rest_framework.views import APIView
from rest_framework.response import Response
from common.http_status_code import HttpStatusCode
from rest_framework.permissions import IsAuthenticated

from api.docs.auth import rsa_doc
from api.utils import RSAUtil
from api.serializer.rsa_serializer import RSASerializer, ResponseRSASerializer

class RSAGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    @rsa_doc()
    def post(self, request):
        serializer = RSASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plain_text = serializer.data.get('plain_text').encode('utf-8')
        private_key, public_key = RSAUtil.generate_rsa_keypair()
        encrypted_text =  RSAUtil.encrypt_rsa(plain_text, public_key)
        data = {
            "private_key": private_key,
            "public_key": public_key,
            "encrypted_text": encrypted_text
        }
        data = ResponseRSASerializer(data=data).initial_data
        return Response(data, status=HttpStatusCode.OK)
