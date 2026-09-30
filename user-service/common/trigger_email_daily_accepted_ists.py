from ist.models import ISTStatus, IST
from django.template.loader import render_to_string
from api.utils import Util
from datetime import date, datetime
from api.models import User
from django.db.models import Sum

def email_daily_accepted_ists():
        today = date.today()    

        # get the count of total approved ists in todays data 
        count_approved_ist_ids = len(list(IST.objects.filter(_type='ACCEPTED', created_at__date = today).values_list('vf_ist_id', flat=True)))

        # aggregate quantity to be moved of all approved ists
        total_quantity_to_be_moved = int(sum(list(IST.objects.filter(_type='ACCEPTED', created_at__date = today).values_list('quantity_to_be_moved', flat=True))))

        # get the al the liaison users emailid 
        liaison_users_email_id = User.objects.filter(role_id__code='LIAISON').values_list('email', flat=True)
        to_email = [i for i in liaison_users_email_id]

        # get all the ist accepted today and perform group by on 'product_hierarchy_1','donor_wh_code', 'receiver_wh_code'
        accepted_ist_info = list(IST.objects.filter(_type='ACCEPTED', created_at__date = today).values('product_hierarchy_1','donor_wh_code', 'receiver_wh_code').annotate(quantity_to_be_moved=Sum('quantity_to_be_moved') ).values_list( 'product_hierarchy_1','donor_wh_code', 'donor_wh_name', 'receiver_wh_code', 'receiver_wh_name', 'quantity_to_be_moved'))

        # quantity_to_be_moved column must contain int values
        for i in range(len(accepted_ist_info)): 
            accepted_ist_info[i] = list(accepted_ist_info[i])
            accepted_ist_info[i][5] = int(accepted_ist_info[i][5])
                    
        current_execution_time = datetime.now().strftime('%I:%M %p')
        todays_date = today.strftime('%d-%b-%Y')
        mail_subject = f'Total ISTs accepted as on {todays_date}, {current_execution_time}:'
        html_content = render_to_string("ist_sugg_approved.html", {
            'count_approved_ist_ids': count_approved_ist_ids,
            'total_quantity_to_be_moved': total_quantity_to_be_moved,
            'accepted_ist_info': accepted_ist_info,
        })

        data = {
            'subject': mail_subject,
            'html_content': html_content,
            'to_email': to_email,
        }
        if count_approved_ist_ids > 0:
            Util.send_html_email(data)