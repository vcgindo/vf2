import os
from django.utils import timezone
from rest_framework import serializers
from api.models import IssueReport
from api.utils import Util
from api.error_code import AuthCode
from common.send_mail import mail_issue_report 


class IssueReportComponent:
    INTER_STORE_TRANSFER = [
        'Manual Upload',
        'Pending IST Request',
        'IST Status',
        'IST Forced Closure',
        'Store Status',
        'Availablity Comparison'
    ]
    @classmethod
    def get_component(cls):
        return {
            'Inter Store Transfer': cls.INTER_STORE_TRANSFER
        }

    @classmethod
    def get_choices(cls):
        choices = []
        for key, value in cls.get_component().items():
          choices += [f'{key} - {item}' for item in value]
        return choices

class IssueReportType:
    UI_ISSUE = 'UI Issue'
    FUNCTIONALITY_BUG = 'Functionality Bug'
    LOGICAL_CALCULATION_ISSUE = 'Logical Calculation Issue'
    OTHERS = 'Others'

    @classmethod
    def get_choices(cls):
        return [
            cls.UI_ISSUE,
            cls.FUNCTIONALITY_BUG,
            cls.LOGICAL_CALCULATION_ISSUE,
            cls.OTHERS
        ]
def generate_name(name, user_id):
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    new_filename = f"{user_id}_{timestamp}{name}"
    return new_filename

class IssueReportSerializer(serializers.ModelSerializer):
    component = serializers.ChoiceField(choices=IssueReportComponent.get_choices(), required=True)
    _type = serializers.ChoiceField(choices=IssueReportType.get_choices(), required=True)
    attachment = serializers.ListField(child=serializers.ImageField(), required=False)

    class Meta:
        model = IssueReport
        fields = ['component', '_type', 'description', 'attachment']

    def validate(self, attrs):
        super().validate(attrs)
        attachment = attrs.get('attachment')
        if attachment:
            if len(attachment)>5:
                raise serializers.ValidationError(AuthCode.ERROR_RANGE_IMAGE)
            size = 4 * 1024 * 1024
            for img in attachment:
                if img.size > size:
                    raise serializers.ValidationError(AuthCode.ERROR_SIZE_IMAGE)
        return attrs
    
    def create(self, validated_data):
        attachment_images = validated_data.pop('attachment', [])  
        issue_report = IssueReport.objects.create(user= self.context,**validated_data) 

        temp = []
        for image in attachment_images:
            filename = generate_name(image.name, self.context.id)
            folder_path = 'public/issue/images/'
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            file_path = folder_path + filename
            with open(file_path, 'wb') as f:
                f.write(image.read())
            image_url = f"{os.environ.get('BASE_CLIENT_URL')}/{file_path}"
            temp.append(image_url)
        
        issue_report.attachment = temp

        # Send mail to admin
        try:
            data = mail_issue_report(issue_report)
            Util.send_html_email(data)
        except Exception as e:
            pass
        issue_report.save() 
        return issue_report
