# Define helper functions for checking input
import math
import re

def check_for_comma_pipe(data,field):
    if(',' in data and '|' in data):
        return '{f} should not contain comma and pipe.'.format(f=field)
    if(',' in data):
        return '{f} should not contain comma.'.format(f=field)
    if('|' in data):
        return '{f} should not contain pipe.'.format(f=field)
    return ''
        
def is_input_has_comma(data,field):
    if(',' in data):
        return '{f} should not contain comma.'.format(f=field)
    return ''

def is_input_has_pipe(data,field):
    if('|' in data):
        return '{f} should not contain pipe.'.format(f=field)
    return ''

def is_empty(data):
    if(isinstance(data,str)):
        return False
        
    if(math.isnan(data)):
        return True 
    return False

def is_integer(data,field):
    if(not isinstance(data,int) and not bool(re.match(r'^[-]?\d+$', data))):
        return '{f} must be an integer.'.format(f=field)
    return ''

def is_number(data,field):
    if(not str.isnumeric(str(data).replace('.','',1))):
        return '{f} must be a valid number.'.format(f=field)
    return ''



def max_length(data,field,max_length):
    if(len(data) > max_length):
        return '{f} should not exceed {m} characters.'.format(f=field,m=max_length)
    return ''

def min_length(data,field,min_length):
    if(len(data) < min_length):
        return '{f} should be minimum {m} characters.'.format(f=field,m=min_length)
    return ''

def greater_than(data,field,value):
    if(float(data) <= value):
        return '{f} should be greater than {m}.'.format(f=field,m=value)
    return ''

def less_than(data,field,value):
    if(float(data) >= value):
        return '{f} should be less than {m}.'.format(f=field,m=value)
    return ''

def min_value(data,field,min_value):
    if(float(data) < min_value):
        return '{f} should be greater than or equal to {m}.'.format(f=field,m=min_value)
    return ''

def max_value(data,field,max_value):
    if(float(data) > max_value):
        return '{f} should be less than or equal to {m}.'.format(f=field,m=max_value)
    return ''

def is_valid(data,field,values):
    values_string = ','.join(values)
    if(data not in values):
        return '{f} should contain a valid value amongst [{m}].'.format(f=field,m=values_string)
    return ''


def check_regex(data,feild,regexPattern):
    if not re.match(regexPattern, data):
        return '{f} should not contain special characters.'.format(f=feild)
    return ''

def checkForSeparator(data,field):
    if((',' in data) and ('|' in data)):
        return '{f} should not contain comma and pipe.'.format(f=field)
    else:
        return ''   

def is_input_only_special_characters(data, field):
   
    pattern = r'^[\W_]+$'  
    # Check if the data contains only special characters
    if re.match(pattern, data):
        return '{f} should not contain only special characters.'.format(f=field)
    return ''
        
def check_for_all_special_char_and_comma_pipe(data,field):
    spchar_checks =  is_input_only_special_characters(data,field)
    if len(spchar_checks) ==0:
        return check_for_comma_pipe(data,field)
    return spchar_checks


def description_validator(data,field):
    spchar_checks =  is_input_only_special_characters(data,field)
    if len(spchar_checks)==0:
        return is_input_has_pipe(data,field)
    else:
        return spchar_checks

from datetime import datetime

def validate_yyyy_mm_dd(data,field):
    """
    Validates if a string is a date in the 'yyyy-mm-dd' format.

    Args:
        date_string (str): The date string to validate.

    Returns:
        bool: True if the string is a valid date in 'yyyy-mm-dd' format, False otherwise.
    """
    try:

        today_date =datetime.today()
        current_date = datetime.strptime(data, "%Y-%m-%d")

        if (current_date-today_date).days < 0:
            return '{f} should be greater than current date.'.format(f=field)

        return ''
    except ValueError:
        # If parsing fails, it's not a valid date
        return '{f} should be in YYYY-MM-DD format.'.format(f=field)

# def is_number(data, field):
#     s = str(data).strip()  # Remove whitespace
#     try:
#         float(s)  # Attempt to convert to float (handles +, -, decimals)
#         return ''  # Valid number
#     except ValueError:
#         return '{f} must be a valid number.'.format(f=field)

def customAttributeCheck(row  , key_to_header_map , MAX_CODE_LENGTH) :
    C_COLUMNS = [f'c{i}' for i in range(1, 16)]
    error = ""
    for col in C_COLUMNS:
        if col in row.index:
            value = row[col]
            header = key_to_header_map[col]

            if not is_empty(value):
                error += max_length(value, header, MAX_CODE_LENGTH)
    return error


def check_single_column_duplicate(df, column_name, row_value, key_to_header_map):
    error = ""
    if len(df[df[column_name].str.lower() == str(row_value).lower()]) > 1:
        error += '{f} should be unique.'.format(f=key_to_header_map[column_name])
    return error


def check_multiple_column_duplicate(df, columns, row_values, key_to_header_map):
    mask = None
    for col in columns:
        col_mask = (df[col].str.lower() == str(row_values[col]).lower())
        mask = col_mask if mask is None else (mask & col_mask)
    
    if len(df[mask]) > 1:
        names = [key_to_header_map[col] for col in columns]
        if len(names) == 2:
            error_msg = f"{names[0]} and {names[1]} should be unique."
        else:
            error_msg = f"{', '.join(names[:-1])} and {names[-1]} should be unique."
        return error_msg
    
    return ""