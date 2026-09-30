from asyncio.log import logger
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.utils.html import strip_tags
import os
from django.conf import settings
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa,padding
import base64
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives, get_connection
import requests
from common.send_mail import mail_ads_expiry_reminder
from api.common.mail_config import is_smtp_enabled
from common.http_status_code import HttpStatusCode
from api.error_code import AuthCode



class ActiveDirectoryUtil:
    """ 
    this class is for azure directory services authentication, which is responsible
    for checking user credentials in ADS, 
    to generate bearer token by inputting client credentials
    use that token to check the user's email for account activity status
    """

    @staticmethod
    def send_ads_email(client_name,AdsCredExpirationDate,expiry_days_left,send_primary_mail,send_secondary_mail):
        """ This function will send alert mail notification, for ads cred expiration
        """
        #adding this inside class to avoid 'AppRegistryNotReady' exception
        from api.models import ADS_Config,AlertEmailCCDetails
        response={
            #setting up empty response dic
        }
        try:
            # fetching email details from AlertEmailCCDetails model
            email_details = AlertEmailCCDetails.objects.filter(event_key='active_dir_expire').values().first()
            if email_details and email_details["is_active"]:
                email_to_raw = email_details.get("email_to")
                cc_raw = email_details.get("cc")
                email_to = [e.strip() for e in (email_to_raw or "").split(",") if e.strip()]
                cc = [e.strip() for e in (cc_raw or "").split(",") if e.strip()]
                #if email_to does not have recipients raise exception
                if not email_to:
                    raise Exception("email recipients  is/are  missing or empty in AlertEmailCCDetails")
            else:
                raise Exception(f"the {email_details['event_key']} email is inactive hence no email sent")
            data = mail_ads_expiry_reminder(
                email_to, #from AlertEmailCCDetails model
                cc,#from AlertEmailCCDetails model
                client_name,
                AdsCredExpirationDate,
                expiry_days_left,
            )
            smtp_available = is_smtp_enabled()
        
            if smtp_available:
                Util.send_html_email(data)
                #update ads_config's primary_email_notify,secondary_email_notify
                for flag, send in [('primary_email_notify', send_primary_mail),('secondary_email_notify', send_secondary_mail)]:
                    if send:
                        logger.info(f"updating {flag} in Ads_Config")
                        ADS_Config.objects.filter(flag=flag).update(value=True)
                        logger.info(f"update of {flag} complete")
            elif not smtp_available:
                logger.info("smtp is not initialized for this client")
                smtp_error_msg = AuthCode.SMTP_NOT_ENABLED_ADS_EXPIRY["msg"]["message"]
                response.update({
                    'smtp_error':f"{smtp_error_msg}{expiry_days_left} days.\n Ensure updated credentials are provided before expiry",
                    'smtp_status':HttpStatusCode.OK
                })
            logger.info(f"send_ads_email execution successfull")
        except Exception as e:
            logger.error(f"Error in Sending mail : {e}",exc_info=True)
            smtp_error_msg = AuthCode.SMTP_NOT_ENABLED_ADS_EXPIRY["msg"]["message"]
            response.update({
                'smtp_error':f"{smtp_error_msg}{expiry_days_left} days.\n Ensure updated credentials are provided before expiry",
                'smtp_status':HttpStatusCode.BAD_REQUEST,
            })
        logger.error("send_ads execution completed...")

        return response
    
    @staticmethod
    def get_ads_token(tenant_id,client_id,client_secret,ads_token_url,scope='https://graph.microsoft.com/.default',grant_type='client_credentials'):
        """ This function will return the bearer token for 
        azure directory services this will take 
        all the parameters as payload and return bearer token with an expiration time
        """
        #adding this inside class to avoid 'AppRegistryNotReady' exception
       
        logger.info("azure directory service's fetch bearer token operation has started")
        #setting up the payload and headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
            }
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": grant_type,
            "scope": scope
            
        }
        response={
            #setting up empty response dic
        }
        try:
            response_req = requests.post(ads_token_url.format(tenant_id=tenant_id), data=payload, headers=headers)
            response_req.raise_for_status() # Raise for HTTP errors
            bearer_token_response = response_req.json()
            response.update({
                "success": True,
                "message": 'ADS token generated',
                "last_bearer_token_access_time": datetime.now().replace(microsecond=0),
                "bearer_token_exp_time": bearer_token_response.get("expires_in"),
                "bearer_token": bearer_token_response.get("access_token"),
                "status":HttpStatusCode.CREATED
            })
            logger.info(f"get_ads_token execution successfull")
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Failed to fetch ADS token: {e}", exc_info=True)
            response.update({
            "success": False,
            "message": "Unable to fetch token key from Azure Directory Service, If the issue persists please contact Administrator",
            "status":HttpStatusCode.BAD_REQUEST
            })

        return response
    
    @staticmethod
    def fetch_UserDetails(user_account_status_url,user_email,bearer_token):
            """ this is a func just to fetch the user activity detail by GET request 
            and will return dynamic response according to the user_details_success_flag
            """
            response={ 
                #empty response dict
            }
            try:
                #setting up headers
                headers = { "Authorization": f"Bearer {bearer_token}", "Accept": "application/json" }
                logger.info("fetching user details from Azure directory services to check for account activity status...") 
                #sending a GET request
                user_data = requests.get(user_account_status_url.format(email=user_email), headers=headers)
                logger.info("GET request completed...")
                user_details=user_data.json()
                #the ADS returns an error dict as response which is used to check for success or no
                user_details_success_flag=not user_details.get('error')

                #updating response dict accoriding to the success flag ie True or False
                response.update({
                "success": user_details_success_flag,
                "message": f"{'user details fetched' if user_details_success_flag else user_details.get('error', {}).get('message')} in Azure Directory Service",
                "id": user_details.get('id') if user_details_success_flag else None,
                "mail": user_details.get('mail') if user_details_success_flag else None,
                "accountEnabled": user_details.get('accountEnabled') if user_details_success_flag else None,
                "status":HttpStatusCode.OK if user_details_success_flag else HttpStatusCode.NOT_FOUND
                })

                logger.info(f"fetch_UserDetails execution successfull")
            except (requests.exceptions.RequestException, ValueError) as e:
                logger.error(f"Failed to fetch user details: {e}",exc_info=True)
                response.update({
                "success": False,
                "message": f"Unable to Fetch {user_email} details from Azure Directory Services, If the issue persists please contact Administrator",
                "status":HttpStatusCode.BAD_REQUEST
                })

            return response
            

    @staticmethod
    def ads_Authentication(user_email):
        #adding this inside class to avoid 'AppRegistryNotReady' exception
        from api.models import ADS_Config
        """ this function will do 3 main operations
        1) to fetch the bearer token from get_ads_token
        2) to return the user activity status ie active or inactive
        3) initiate mail when the credentials are going to expire
        """
        response={
            #setting an empty response dic
                }
        #setting upper limit and lower limit for ad credential's expiry days
        upper_limit_days,lower_limit_days=10,5
        try:
            #fetching the flags and values from ads_config
            logger.info("fetching ADSConfig and converting them into a dictionary")
            ads_details={row['flag']: row['value'] for row in ADS_Config.objects.values('flag', 'value')}
            #fetching all required values 
            logger.info("fetching all required values from ads_details")
            client_name,ads_token_url,user_account_status_url,tenant_id,client_id,client_secret,bearer_token,last_bearer_token_access_time,bearer_token_exp_time,ads_cred_exp_date,primary_email_notify,secondary_email_notify=ads_details.get('client_name'),ads_details.get('ads_token_url'),ads_details.get('user_account_status_url'),ads_details.get('tenant_id'),ads_details.get('client_id'),ads_details.get('client_secret'),ads_details.get('bearer_token'),ads_details.get('last_bearer_token_access_time'),ads_details.get('bearer_token_exp_time'),ads_details.get('ads_cred_exp_date'),ads_details.get('primary_email_notify'),ads_details.get('secondary_email_notify')
            #fetching today's date
            today, now_time = datetime.now().date(), datetime.now().replace(microsecond=0)
            # comapring the time with the ADS cred expiration date
            AdsCredExpirationDate = datetime.strptime(ads_cred_exp_date,"%Y-%m-%d").date()
            #fetching days left until expiry
            expiry_days_left=(AdsCredExpirationDate-today).days
            if not today>AdsCredExpirationDate:
                #taking the last token access time with bearer_exp_time to see if the token has expired or no if yes then new token will be generated
                if (bearer_token and last_bearer_token_access_time and bearer_token_exp_time and (now_time - (datetime.strptime(last_bearer_token_access_time, "%Y-%m-%d %H:%M:%S"))).total_seconds() < int(bearer_token_exp_time)):
                    logger.info("initializing the fetch_user_detail function for user details from ADS")
                    user_detail=ActiveDirectoryUtil.fetch_UserDetails(user_account_status_url,user_email,bearer_token)
                    logger.info("initialization of fetch_user_detail function completed")
                    #updating response
                    response.update({key: user_detail.get(key) for key in ("success", "id", "mail", "accountEnabled", "message", "status")})
                else:
                    logger.info("bearer token is null or the last accessed time is null calling get_ads_token to generate token")
                    fetch_token=ActiveDirectoryUtil.get_ads_token(tenant_id,client_id,client_secret,ads_token_url)
                    logger.info("fetch_token function run complete")
                    if fetch_token.get('success') and fetch_token.get("status") == HttpStatusCode.CREATED:
                        #fetch the bearer token and time stamp
                        ads_details['bearer_token'], ads_details['last_bearer_token_access_time'], ads_details['bearer_token_exp_time'] = (
                        fetch_token.get('bearer_token'),
                        fetch_token.get('last_bearer_token_access_time'),
                        fetch_token.get('bearer_token_exp_time')
                        )
                        values_to_update = []
                        #assigning new token to the variable
                        bearer_token=ads_details['bearer_token']
                        for flag, value in ads_details.items():
                            # Convert datetime to string if column is VARCHAR
                            if isinstance(value, datetime):
                                value = value.strftime('%Y-%m-%d %H:%M:%S')
                            values_to_update.append(ADS_Config(flag=flag, value=value))
                        logger.info("updating ADS_Config model...")
                        ADS_Config.objects.bulk_update(values_to_update, ['value'])
                        logger.info("ADS_Config model updated with new values")
                        #initializing fetch_UserDetails function
                        logger.info("initializing the fetch_user_detail function for user details from ADS")
                        user_detail=ActiveDirectoryUtil.fetch_UserDetails(user_account_status_url,user_email,bearer_token)
                        logger.info("initialization of fetch_user_detail function completed")
                        #update response
                        response.update({key: user_detail.get(key) for key in ("success", "id", "mail", "accountEnabled", "message", "status")})
                    else:
                        logger.error("fetch_token execution failed")
                        response.update({
                            "success": False,
                            "message": fetch_token.get('message'),
                            "status":HttpStatusCode.BAD_REQUEST
                            })
                logger.info(f"finally checking if expiry days are less than {upper_limit_days} or {lower_limit_days}")
                primary_email_notify= primary_email_notify.lower()=='true'
                secondary_email_notify=secondary_email_notify.lower()=='true'
                #setting up a bool value based on expiry days and if mail has been already sent or no
                send_primary_mail = (expiry_days_left <= upper_limit_days and expiry_days_left >lower_limit_days and not primary_email_notify)
                send_secondary_mail = (expiry_days_left <= lower_limit_days and not secondary_email_notify)
                if send_primary_mail or send_secondary_mail:
                    logger.info(f"primary mail flag is {send_primary_mail} or secondary mail flag is {send_secondary_mail} hence calling send_ads_mail function")
                    email_notification=ActiveDirectoryUtil.send_ads_email(client_name,AdsCredExpirationDate,expiry_days_left,send_primary_mail,send_secondary_mail)
                    if email_notification:  # only update if not None
                        logger.error("smtp has failed due to some reason hence the message will be displayed through UI")
                        response.update(email_notification)
            else:
                logger.error("Active Directory Service's Client Credentials have expired, please contact Administrator")
                response.update({
                    "success": False,
                    "message": "Active Directory Service's Client Credentials have expired, please contact Administrator",
                    "status":HttpStatusCode.BAD_REQUEST
                })
            logger.info("ads_Authentication function executed (success or exception)...")
        except Exception as e:
            logger.error(f"ads_authentication function failed to run {e}",exc_info=True)
            response.update({
                    "success": False,
                    "message": "Cannot verify user, please ensure all credentials are provided",
                    "status":HttpStatusCode.BAD_REQUEST
                })

        return response

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            from_email=os.environ.get('EMAIL_FROM'),
            to=[data['to_email']],
            headers={'From': os.environ.get('EMAIL_NAME')},
        )
        email.send()


    @staticmethod
    def rate_limit_validate(self,request):
        from api.models import RateLimitTable
        from apps.settings import API_BLOCKING_TIME, API_BLOCKING_LIMITS
        def is_blocking_time_exceeded(last_req_date, blocking_time):
            current_time = timezone.now()
            blocking_end_time = last_req_date + timedelta(seconds=blocking_time)
            return blocking_end_time > current_time

        def get_client_ip(self, request):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return ip

        ipaddress=get_client_ip(self,request)

        # get user's rate limit row 
        rate_limit_entry = RateLimitTable.objects.filter(ipaddress=ipaddress).first()
        created = False
        if rate_limit_entry is None:
            rate_limit_entry = RateLimitTable.objects.create(ipaddress=ipaddress)
            created=True
        response = False
        if created==True:
            rate_limit_entry.token_used=1
        elif not is_blocking_time_exceeded(rate_limit_entry.last_req,API_BLOCKING_TIME):
            rate_limit_entry.token_used=1
        else:
            if rate_limit_entry.token_used >= API_BLOCKING_LIMITS:
                response=True
            else:
                rate_limit_entry.token_used=rate_limit_entry.token_used+1

        rate_limit_entry.last_req = timezone.now()
        rate_limit_entry.save()
        return response

    
    @staticmethod
    def send_html_email(data):
        text_content = strip_tags(data['html_content'])
        email_kwargs = {
                "subject": data['subject'],
                "body": text_content,
                "from_email": os.environ.get('EMAIL_FROM'),
                "to": data['to_email'],
                "headers": {'From': os.environ.get('EMAIL_NAME')},
            }

        if data.get('cc'):
            email_kwargs["cc"] = data['cc']

        email = EmailMultiAlternatives(**email_kwargs)
        email.attach_alternative(data['html_content'], "text/html")

        dependency_error_zip_file_path = data.get('dependency_error_zip_file_path')
        if dependency_error_zip_file_path != '' and dependency_error_zip_file_path != None:
            with open(dependency_error_zip_file_path, 'rb') as f:
                email.attach('master_dependency_validation_error_files.7z', f.read(), 'application/x-7z-compressed')
        
        email.send()

    @staticmethod
    def send_html_email_bulk(data_list):
        messages = []
        for data in data_list:
            subject = data.get("subject", "No Subject")
            text_content = strip_tags(data['html_content'])
            from_email = os.environ.get("EMAIL_FROM") or settings.EMAIL_HOST_USER
            to_email_raw = data.get("to_email", [])
            
            if isinstance(to_email_raw, str):
                to_email = [to_email_raw]
            elif isinstance(to_email_raw, list):
                to_email = to_email_raw
            else:
                continue 

            message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_email,
            )
            message.attach_alternative(data['html_content'], "text/html")
            messages.append(message)
        
        connection = get_connection()
        try:
            connection.send_messages(messages)
        except Exception as e:
            logger.info("email send failure:", e)

class RSAUtil:
    @staticmethod
    def _key_paths():
        private_pem_path = os.environ.get('USER_SERVICE_RSA_PRIVATE_KEY_PATH', '').strip()
        public_pem_path = os.environ.get('USER_SERVICE_RSA_PUBLIC_KEY_PATH', '').strip()
        if not private_pem_path or not public_pem_path:
            raise RuntimeError(
                'USER_SERVICE_RSA_PRIVATE_KEY_PATH and USER_SERVICE_RSA_PUBLIC_KEY_PATH are required'
            )
        return private_pem_path, public_pem_path

    @staticmethod
    def generate_rsa_keypair():
        private_pem_path, public_pem_path = RSAUtil._key_paths()
        if os.path.exists(private_pem_path) and os.path.exists(public_pem_path):
            with open(private_pem_path, 'rb') as f:
                private_pem =f.read()
            with open(public_pem_path, 'rb') as f:
                public_pem =f.read()
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()

            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(private_pem_path, 'wb') as f:
                f.write(private_pem)
            
            with open(public_pem_path, 'wb') as f:
                f.write(public_pem)

        return private_pem, public_pem

    @staticmethod
    def encrypt_rsa(message, public_key):
        public_key = serialization.load_pem_public_key(public_key)
        ciphertext = public_key.encrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        ciphertext = base64.b64encode(ciphertext).decode('utf-8')
        return ciphertext

    @staticmethod
    def decrypt_rsa(ciphertext):
        if not ciphertext:
            raise RuntimeError('DB_PASSWORD is required')
        private_pem_path, _ = RSAUtil._key_paths()
        with open(private_pem_path, 'rb') as f:
            private_key = f.read()
        ciphertext =  base64.b64decode(ciphertext)
        private_key = serialization.load_pem_private_key(private_key, password=None)
        decrypted = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return decrypted.decode('utf8')
    

        
