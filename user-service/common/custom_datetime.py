from datetime import datetime

class DatetimeGenerator:
    def __init__(self, USE_CUSTOM_DATETIME_FLAG, CUSTOM_DATETIME_DAY, CUSTOM_DATETIME_MONTH, CUSTOM_DATETIME_YEAR, CUSTOM_FORMAT):
        self.CUSTOM_FORMAT = CUSTOM_FORMAT
        if int(USE_CUSTOM_DATETIME_FLAG) == 1:
            self.custom_datetime = datetime(year=int(CUSTOM_DATETIME_YEAR), month=int(CUSTOM_DATETIME_MONTH), day=int(CUSTOM_DATETIME_DAY), hour=1,minute=0, second=0)
        else:
            self.custom_datetime = datetime.now()
        
    def return_custom_datetime(self):
        return self.custom_datetime
    def return_custom_datetime_formatted(self):
        return self.custom_datetime.strftime(self.CUSTOM_FORMAT)