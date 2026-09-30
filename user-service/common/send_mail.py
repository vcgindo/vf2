from django.conf import settings
import os

from django.template.loader import render_to_string

def mail_ads_expiry_reminder(email_to,cc,client_name,AdsCredExpirationDate,expiry_days_left):
    """this will run when the active directory credentials are about to expire"""
    subject=f'{client_name} - Active Directory Services client credentials expiring in {expiry_days_left} days'
    html_content=render_to_string("ads_expiry_notify.html",{
        'base_client_url': os.environ.get('BASE_CLIENT_URL'),
        'expiry_date':AdsCredExpirationDate,
        'site_name':client_name,
        'title': subject,
        'text': 'Active directory credentials will expire soon'
    })
    data={
        'subject':subject,
        'html_content':html_content,
        'to_email':email_to,
        'cc':cc
    }
    return data
def mail_create_user(email, username, password):
    subject = 'Vector Flow - Create account'
    html_content = render_to_string("create_account.html",
                                    {
                                        'email': email, 
                                        'password': password,
                                        'username': username,
                                        'base_client_url': os.environ.get('BASE_CLIENT_URL'),
                                        'title': 'Welcome to VectorFLOW',
                                        'text': 'Your registration was successful'
                                    })
    data = {
        'subject': subject,
        'html_content': html_content,
        'to_email': [email],
    }
    return data
def mail_update_user(email, password, username):
    subject = 'Vector Flow - Change account information'
    html_content = render_to_string("create_account.html",
                                    {
                                        'email': email, 
                                        'password': password,
                                        'username': username,
                                        'base_client_url': os.environ.get('BASE_CLIENT_URL'),
                                        'title': 'VectorFLOW',
                                        'text': 'Your password is changed'
                                    })
    data = {
        'subject': subject,
        'html_content': html_content,
        'to_email': [email],
    }
    return data
def mail_forgot_password(email, username, url):
    subject = 'Vector Flow - Reset your password'
    html_content = render_to_string("password_reset.html",
                                    {
                                        'url': url, 
                                        'username': username,
                                        'base_client_url': os.environ.get('BASE_CLIENT_URL')
                                    })
    data = {
        'subject': subject,
        'html_content': html_content,
        'to_email': [email],
    }
    return data

def mail_issue_report(issue_report):
    subject = 'Vector Flow - Issue Report'
    html_content = render_to_string('issue_report.html',
                                    {
                                        'username':issue_report.user.name,
                                        'issue_component': issue_report.component,
                                        'issue_type': issue_report._type,
                                        'issue_description': issue_report.description,
                                        'issue_attachment': issue_report.attachment,
                                        'base_client_url': os.environ.get('BASE_CLIENT_URL')
                                    })

    data = {
        'subject': subject,
        'html_content': html_content,
        'to_email': os.environ.get('EMAIL_ADMIN').split()
    }
    return data

