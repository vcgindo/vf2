import os 
import datetime 
from apps.settings import USER_STORIES_STORAGE, FTP_ZIP_FILE_STORE, DEFAULT_URL_CSV, HORIZON_FOR_STOCK_COMPARISON, STOCK_VARIATION_PERCENTAGE
from api.utils import Util
import pandas as pd
from django.template.loader import render_to_string 
from api.models import Roles, User
from datetime import date
from functools import reduce
import numpy as np

######################################################################################
# email ids of liaison and governor code 
def get_user_emails(): 
    liaison_users_email_id = User.objects.filter(role_id__code='LIAISON').values_list('email', flat=True)
    governor_users_email_id = User.objects.filter(role_id__code='GOVERNOR').values_list('email', flat=True)
    to_email = [i for i in liaison_users_email_id] + [i for i in governor_users_email_id]
    return to_email

# Check if final reports are available 
def check_final_output_availability():
    is_fashion_rationed_requirement_present = os.path.isfile(f'{USER_STORIES_STORAGE}/Fashion-RationedRequirement.7z')
    is_ist_output_present = os.path.isfile(f'{USER_STORIES_STORAGE}/IST_Output.7z')
    file_presence = []
    qty_values = [-1,-1]
    if is_fashion_rationed_requirement_present:
        message =  "Ok"
        if is_file_generated_today("Fashion-RationedRequirement.7z") == False:
            message = 'File Not Generated'
        else: 
            frr_df = pd.read_csv(f'{USER_STORIES_STORAGE}/Fashion-RationedRequirement.csv', usecols=['final_allocation_qty_child'], low_memory=False)
            final_allocation_qty_child = frr_df['final_allocation_qty_child'].sum()
            qty_values[0] = int(final_allocation_qty_child)
        file_presence.append(message)
    else: 
        message = 'File Not Generated'
        file_presence.append(message)
    
    if is_ist_output_present:
        message = "Ok"
        if is_file_generated_today("IST_Output.7z") == False:
            message = 'File Not Generated'
        
        else: 
            ist_df = pd.read_csv(f'{USER_STORIES_STORAGE}/IST_Output.csv', low_memory=False)
            quantity_to_be_moved = ist_df['quantity_to_be_moved'].sum()
            qty_values[1] = int(quantity_to_be_moved)            
        file_presence.append(message)
    else: 
        message = "File Not Generated"
        file_presence.append(message)
    
    return file_presence, qty_values

# check if reports present are generated today
def is_file_generated_today(file_name):
    todays_date = datetime.date.today()
    file_modification_timestamp = os.path.getmtime(f'{USER_STORIES_STORAGE}/{file_name}')
    return datetime.datetime.fromtimestamp(file_modification_timestamp).date() == todays_date

######################################################################################

def email_uncertain_stock_consumption():

    # A: Finding unique stores in deployment master with movt status as True
    # read LocationMaster
    loc_master = pd.read_csv(f'{DEFAULT_URL_CSV}/master/LocationMaster.csv', low_memory=False)
    
    # read DeploymentMaster and remove duplicate wh_codes
    cols = ['sku_code', 'wh_code']
    deploy_master = pd.read_csv(f'{DEFAULT_URL_CSV}/master/DeploymentMaster.csv', low_memory=False)[cols]
    deploy_master.drop_duplicates(subset=['wh_code'], inplace=True)

    # merge loc and deploy master. Find all the wh_codes that are present in both masters, with movement status True.
    loc_deploy_master = pd.merge(loc_master, deploy_master, on=['wh_code'], how='outer', indicator=True)

    deploy_master_wh_code_mvmt_st_True = loc_deploy_master[(loc_deploy_master['_merge'] == 'both') & (loc_deploy_master['movement_status'] == True)][['wh_code', 'wh_name', 'sku_code', 'movement_status', 'specific_sales']]

    # classifiy above resulted wh_codes under product hierarchy categories (specific_sales)
    deploy_master_wh_code_mvmt_st_True_groupby_ph1 = deploy_master_wh_code_mvmt_st_True.groupby(['specific_sales'])
    classified_ph1_mvmt_st_True = deploy_master_wh_code_mvmt_st_True_groupby_ph1.first()
    classified_ph1_mvmt_st_True.reset_index(inplace=True)

    # storing the count of wh_codes under each ph1 category in wh_code_count column
    classified_ph1_mvmt_st_True['wh_code_count'] = list(deploy_master_wh_code_mvmt_st_True_groupby_ph1.size())

    # unique Stores in Deployment Master With Movt Status as True
    sheet_01_col_01 = classified_ph1_mvmt_st_True[['specific_sales', 'wh_code_count']].round(2)
    sheet_02 = deploy_master_wh_code_mvmt_st_True[['wh_code', 'wh_name', 'specific_sales']].round(2)

    
    #######################################################################

    # B: Finding stores missing in today's data (wh_missing)
    cols = ['sku_code', 'wh_code', 'stock', 'git', 'consumption', 'report_date', 'product_hierarchy_1']
    last_60_days = pd.read_csv(f'{USER_STORIES_STORAGE}/last_60_days_added_cols.csv', low_memory=False)[cols]

    # sepration of today data from earlier data 
    days_date = sorted(last_60_days['report_date'].dropna().unique(), reverse=True)
    present_day = days_date[0]
    todays_data = last_60_days[last_60_days['report_date'].isin([present_day])]

    # we dont want any how wh_codes with 0 stock
    todays_data = todays_data[(todays_data['stock'] + todays_data['git']) > 0]

    # remove duplicate wh_codes from todays data
    todays_data_no_duplicate_wh_code = todays_data.drop_duplicates(subset=['wh_code'])

    # merge wh_code with movement status true, todays data. Find wh_codes missing in todays data. 
    deploy_todays_merged = pd.merge(deploy_master_wh_code_mvmt_st_True, todays_data_no_duplicate_wh_code, on='wh_code', how='outer', indicator=True)[['wh_code', 'wh_name', 'specific_sales', 'product_hierarchy_1', 'movement_status', 'report_date', '_merge']]

    # 0 means all the wh_codes stores from deployment master with movemnt status true are presnt in todays data
    wh_code_missing_todays_data = deploy_todays_merged[deploy_todays_merged['_merge'] == 'left_only']

    # classifiy the resulted missing wh_codes above into product hierarchy categories (specific_sales)
    wh_code_missing_todays_data_groupby_ph1 = wh_code_missing_todays_data.groupby(['specific_sales'])

    classified_ph1_wh_code_missing_todays_data = wh_code_missing_todays_data_groupby_ph1.first()
    classified_ph1_wh_code_missing_todays_data.reset_index(inplace=True)
    classified_ph1_wh_code_missing_todays_data['wh_code_count'] = list(wh_code_missing_todays_data_groupby_ph1.size())

    sheet_01_col_02 = classified_ph1_wh_code_missing_todays_data[['specific_sales', 'wh_code_count']].round(2)
    sheet_03 = wh_code_missing_todays_data[['wh_code', 'wh_name', 'specific_sales', 'movement_status']].round(2)

    #######################################################################

    # merge wh_codes with movemnt status true and last 60 days data 
    deploy_last60days_mvmt_true_merged = pd.merge(deploy_master_wh_code_mvmt_st_True, last_60_days, on=['wh_code'], how='outer', indicator=True)

    # take only those wh_codes from last 60 days which have movement status true and are presnt in deployment master 
    last_60_days = deploy_last60days_mvmt_true_merged[deploy_last60days_mvmt_true_merged['_merge'] == 'both']
    last_60_days.drop('_merge', inplace=True, axis=1)

    #######################################

    # C: Finding duplicates in last_60_days for skucode, wh_code, report date as combined 

    duplicates_skucode_whcode_comb_in_current_day = last_60_days[last_60_days.duplicated(subset=['sku_code_y', 'wh_code', 'report_date'])]
    
    # classify resulted duplicated wh_codes into categories of product_hirerarchy 
    duplicates_skucode_whcode_comb_in_current_day_groupby_ph1 = duplicates_skucode_whcode_comb_in_current_day.groupby(['specific_sales'])
    classified_duplicates_skucode_whcode_comb_in_current_day_groupby_ph1 = duplicates_skucode_whcode_comb_in_current_day_groupby_ph1.first()
    classified_duplicates_skucode_whcode_comb_in_current_day_groupby_ph1.reset_index(inplace=True)
    classified_duplicates_skucode_whcode_comb_in_current_day_groupby_ph1['wh_code_count'] = list(duplicates_skucode_whcode_comb_in_current_day_groupby_ph1.size())

    sheet_01_col_06 = classified_duplicates_skucode_whcode_comb_in_current_day_groupby_ph1[['specific_sales', 'wh_code_count']].round(2)
    sheet_07 = duplicates_skucode_whcode_comb_in_current_day[['sku_code_x', 'wh_code', 'wh_name', 'report_date']].round(2)
    sheet_07 = sheet_07.copy()
    sheet_07.rename(columns={'sku_code_x': 'sku_code'}, inplace=True)

    #######################################

    # D: Finding stores with abs variation of Current Stock > 125 percent of last 7 day\'s average (stock_>_125%_today)

    # sepration of today data from earlier data 
    days_date = sorted(last_60_days['report_date'].dropna().unique(), reverse=True)
    horizon = days_date[1:HORIZON_FOR_STOCK_COMPARISON+1]
    last_seven_days_exclude_todays_data = last_60_days[last_60_days['report_date'].isin(horizon)]
    present_day = days_date[0]
    todays_data = last_60_days[last_60_days['report_date'].isin([present_day])]

    # perform group by on wh_code, specific_sales on todays data, last_7_days data 
    group_todays_data = todays_data.groupby(['wh_code', 'specific_sales'])
    group_last_seven_days = last_seven_days_exclude_todays_data.groupby(['wh_code', 'specific_sales'])

    # to perform join with no duplicate data we took first 
    todays_data_first_entry = group_todays_data.first()
    last_seven_days_exclude_todays_data_first_entry = group_last_seven_days.first()

    number_of_days_data_till_yesterday = len(last_seven_days_exclude_todays_data['report_date'].unique())
    number_of_days_data_till_yesterday = HORIZON_FOR_STOCK_COMPARISON # variablize 7 days

    # we want stock + git sum for todays data, average of stock + git sum for last_7_days data 
    todays_data_first_entry['stock_git_sum'] = group_todays_data['stock'].sum() + group_todays_data['git'].sum()
    last_seven_days_exclude_todays_data_first_entry['average_stock_git_sum'] = (group_last_seven_days['stock'].sum()+ group_last_seven_days['git'].sum())/number_of_days_data_till_yesterday

    # we want consumption sum for todays data, last_7_days data 
    todays_data_first_entry['consumption_sum'] = group_todays_data['consumption'].sum() 
    last_seven_days_exclude_todays_data_first_entry['last_7_consumption_sum'] = group_last_seven_days['consumption'].sum()
    todays_data_first_entry.reset_index(inplace=True)
    last_seven_days_exclude_todays_data_first_entry.reset_index(inplace=True)

    # merge todays, last_7_days data. F 
    todays_last_seven_days_merged = pd.merge(last_seven_days_exclude_todays_data_first_entry, todays_data_first_entry, on =['wh_code', 'specific_sales'], how ='outer', indicator=True)

    # take wh_codes which are presnt today and last 7 days only
    todays_last_seven_days_merged = todays_last_seven_days_merged[todays_last_seven_days_merged['_merge'] == 'both']

    # Find stock percentage 
    todays_last_seven_days_merged['stock_percentage'] = ((todays_last_seven_days_merged['stock_git_sum'] - todays_last_seven_days_merged['average_stock_git_sum']) / todays_last_seven_days_merged['average_stock_git_sum']) * 100 

    # Find wh_codes with stock variation greater than 125 percent (STOCK_VARIATION_PERCENTAGE) 
    wh_code_with_huge_stock_variation = todays_last_seven_days_merged[(abs(todays_last_seven_days_merged['stock_percentage']) > STOCK_VARIATION_PERCENTAGE)][['specific_sales', 'wh_code', 'wh_name_x', 'average_stock_git_sum','stock_git_sum', 'stock_percentage']]


    # classify the resulted wh_code with huge stock variation into categories of product hierarchy 
    wh_code_with_huge_stock_variation_groupby = wh_code_with_huge_stock_variation.groupby(['specific_sales'])
    classified_ph1_stock_variation = wh_code_with_huge_stock_variation_groupby.first()
    classified_ph1_stock_variation.reset_index(inplace=True)
    classified_ph1_stock_variation['wh_code_count'] = list(wh_code_with_huge_stock_variation_groupby.size())

    sheet_01_col_03 = classified_ph1_stock_variation[['specific_sales', 'wh_code_count']].round(2)
    sheet_04 = wh_code_with_huge_stock_variation.round(2)
    sheet_04.rename(columns={'wh_name_x':'wh_name', 'average_stock_git_sum': 'last_7_days_average_stock_git_sum', 'stock_git_sum': 'todays_stock_git_sum'}, inplace=True)

    #######################################################################

    # E: Find wh_code with consumption sum equal to zero for todays data. 
    # Also by logic if consumption sum equals zeros for last 7 days it will be zero for today too.  
    todays_wh_code_consump_equals_zero = todays_last_seven_days_merged[todays_last_seven_days_merged['consumption_sum'] <= 0]

    todays_wh_code_consump_equals_zero_groupby_ph1 = todays_wh_code_consump_equals_zero.groupby('specific_sales')
    classified_ph1_wh_code_consump_equals_zero_todays_data= todays_wh_code_consump_equals_zero_groupby_ph1.first()
    classified_ph1_wh_code_consump_equals_zero_todays_data.reset_index(inplace=True)
    classified_ph1_wh_code_consump_equals_zero_todays_data['wh_code_count'] = list(todays_wh_code_consump_equals_zero_groupby_ph1.size())
    sheet_01_col_04 = classified_ph1_wh_code_consump_equals_zero_todays_data[['specific_sales', 'wh_code_count']].round(2)
    sheet_05 = todays_wh_code_consump_equals_zero[['wh_code', 'wh_name_x', 'specific_sales', 'consumption_sum', 'last_7_consumption_sum']].round(2)
    sheet_05 = sheet_05.copy()
    sheet_05.rename(columns={'wh_name_x':'wh_name','consumption_sum':'todays_consumption_sum', 'last_7_consumption_sum':'last_7_days_consumption_sum'}, inplace=True)
    sheet_05.sort_values(by=['last_7_days_consumption_sum', 'specific_sales'], inplace=True)

    #######################################################################

    # F: Find wh_code with consumption sum equal to zero for last_7_days
    last_7_days_wh_code_consump_equals_zero = todays_last_seven_days_merged[todays_last_seven_days_merged['last_7_consumption_sum'] <= 0]

    # classify resulted wh_codes from last_7_days with consumption sum equal to zero into categories of product hierarchy  
    last_7_days_wh_code_consump_equals_zero_groupby_ph1 = last_7_days_wh_code_consump_equals_zero.groupby('specific_sales')
    classified_ph1_last_7_days_wh_code_consump_equals_zero = last_7_days_wh_code_consump_equals_zero_groupby_ph1.first()
    classified_ph1_last_7_days_wh_code_consump_equals_zero.reset_index(inplace=True)
    classified_ph1_last_7_days_wh_code_consump_equals_zero['wh_code_count'] = list(last_7_days_wh_code_consump_equals_zero_groupby_ph1.size())
    
    sheet_01_col_05 = classified_ph1_last_7_days_wh_code_consump_equals_zero[['specific_sales', 'wh_code_count']].round(2)
    sheet_06 = last_7_days_wh_code_consump_equals_zero[['wh_code', 'wh_name_x', 'specific_sales', 'consumption_sum', 'last_7_consumption_sum']].round(2)

    #######################################################################


    dfs = sheet_01_col_01, sheet_01_col_02, sheet_01_col_03, sheet_01_col_04, sheet_01_col_05, sheet_01_col_06

    # sheet_names = sheet_02, sheet_03, sheet_04, sheet_05, sheet_06, sheet_07

    # Define a function for merging two data frames
    def merge_dfs(left, right):
        return pd.merge(left, right, on='specific_sales', how='left', suffixes=('', '_right'))

    # Use reduce to apply the merge function to the list of data frames
    # sheet_01 contains the summary data of all tables/sheets. 
    sheet_01 = reduce(merge_dfs, dfs)
    sheet_01 = sheet_01.round(2)
    sheet_01 = sheet_01.fillna(0)
    sheet_01.columns = [
        "Specific Sales",
        "Unique Stores in Deployment Master with Movement Status as True",
        "Stores Missing in Today's data (wh_missing)",
        "Stores with abs Variation of Current Stock > 125 percent of last 7 day\'s average (stock>125%)",
        "Stores with 0 Sales in Today\'s Data (zero_sales)",
        "Stores with 0 Sales in Last 7 Day\'s",
        'Duplicate Data (duplicate_data)'
    ]

    uncertain_data_summary_df = sheet_01.copy()

    header = pd.DataFrame({
        'Horizon': [f'Last {HORIZON_FOR_STOCK_COMPARISON} days spans from {horizon[len(horizon)-1]} to {horizon[0]}']
        })
    sheet_01 = pd.concat([header, uncertain_data_summary_df], ignore_index=True)
    
    with pd.ExcelWriter(f'{USER_STORIES_STORAGE}/Warning_DataMissing.xlsx', engine='openpyxl') as writer:
        # Write each DataFrame to a different sheet
        sheet_01.to_excel(writer, sheet_name='Summary', index=False)
        # sheet_02.to_excel(writer, sheet_name='Sheet2', index=False)
        sheet_03.to_excel(writer, sheet_name='wh_missing', index=False)
        sheet_04.to_excel(writer, sheet_name='stock_>_125%_today', index=False)
        sheet_05.to_excel(writer, sheet_name='zero_sales_today', index=False)
        # sheet_06.to_excel(writer, sheet_name='Sheet5', index=False)
        sheet_07.to_excel(writer, sheet_name='duplicate_data', index=False)

    return uncertain_data_summary_df, horizon

######################################################################################

# trigger emails 
def trigger_email_alerts_after_run():
    file_presence, qty_values= check_final_output_availability()
    to_email = get_user_emails()
    
    # check if today's daily input file is present on FTP 
    todays_date= date.today().strftime("%d%m%Y")
    ftp_file_name='InterStoreTransferData_{}.zip'.format(todays_date)
    is_daily_input_present = os.path.isfile(f'{FTP_ZIP_FILE_STORE}/{ftp_file_name}')

    is_last_60_days_added_cols = os.path.isfile(f'{USER_STORIES_STORAGE}/last_60_days_added_cols.csv')

    uncertain_data_summary_df = pd.DataFrame()
    horizon = [None,None]
    if is_last_60_days_added_cols: 
        if is_file_generated_today("last_60_days_added_cols.csv") == True:
            uncertain_data_summary_df, horizon = email_uncertain_stock_consumption()
    
    if is_daily_input_present:
        daily_input_file_size_in_mb = round((os.path.getsize(f'{FTP_ZIP_FILE_STORE}/{ftp_file_name}')) / (1024 * 1024 ) , 2)
        ftp_file_status = 'Ok'
    else:
        daily_input_file_size_in_mb = 0
        ftp_file_status = 'File Not Available'
    
    # Update status based on both or either of reports are present 
    if file_presence[0] == file_presence[1] == ftp_file_status == 'Ok':
        daily_run_status = 'concluded successfully!'
        subject_status = 'Success'
    elif file_presence[0] != file_presence[1]:
        daily_run_status = 'failed partially!'
        subject_status = 'Partial'
    else:
        daily_run_status = 'failed!'
        subject_status = 'Failed'

    # if other than the two columns 'specific_sales', 'Unique stores in deployment master with movt status as True' any other column contains value greater than 1 then summary table must be shown 
    if (sum(uncertain_data_summary_df.iloc[:, 2:].sum())) > 0 and ftp_file_status == 'Ok':
        show_summary = True
    else:
        show_summary = False

    uncertain_data_summary_df.replace(0, '', inplace=True)


    mail_subject = f'VectorFLOW Retail Run Status: {subject_status}'
    html_content = render_to_string("engine_run_status.html", {
        'status': daily_run_status,
        'file_presence': zip(['Fashion-RationedRequirement.csv', 'IST_Output.csv'],file_presence, qty_values),
        'ftp_file_status': ftp_file_status,
        'daily_input_file_size_in_mb': daily_input_file_size_in_mb,
        'show_summary': show_summary,
        'uncertain_data_summary_table': uncertain_data_summary_df.to_html(index=False, classes='summary-table'), 
        'last_7_days_range_day_7': horizon[0],
        'last_7_days_range_day_1': horizon[len(horizon)-1]
    })
    data = {
        'subject': mail_subject,
        'html_content': html_content,
        'to_email': to_email
    }
    Util.send_html_email(data)