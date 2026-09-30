from asyncio.log import logger
from ..validators.commons.index import is_input_has_comma,is_input_has_pipe,max_length,is_empty,is_integer,min_value,max_value,greater_than,less_than,is_number,is_valid
import json


# Define constants
MAX_CODE_LENGTH = 50
MAX_NAME_LENGTH = 255
MIN_DECIMAL_VAL = 0.00
MAX_DECIMAL_VAL = 100000000
MIN_RLT_VALUE = 3
MIN_RCP_VALUE = 3
MIN_GCP_VALUE = 3



# Define custom validation functions


class SeasonalityStatusValidations:
    def __init__(self, df):
        self.df = df
        self.df['error'] = ''
        self.df['warning'] = ''

    #perform data validation
    def validation(self,row,index,key_to_header_map,screen_type,validation_rules):
        error = ''
        warning = ''
       
        try:
            logger.info("ROW-",index)
        except Exception as e:
            error = e

        # print(error)  
        row['error'] += error
        row['warning'] += warning  

        if(len(self.df.index) == 1):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + "]"
        if(index == 0):
            return "[" + json.dumps(row.fillna(value='').to_dict()) + ","
        if(index == len(self.df.index)-1):
            return json.dumps(row.fillna(value='').to_dict()) + "]"
        else:
            return json.dumps(row.fillna(value='').to_dict()) + ","

