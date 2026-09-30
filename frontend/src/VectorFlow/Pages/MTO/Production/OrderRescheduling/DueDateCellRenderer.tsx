import React, { useEffect, useState, useRef } from 'react';
import moment from 'moment';
import Calendar, { CalendarProps } from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import { useUserData } from "../../../../../context/index";
import VFDatePicker from '../../Common/VFDatePicker';
import _ from 'lodash';
import { useGetHolidaysForMaxFolCCROfOrder } from '../../../../../VectorFlow/Services/MTO/Production/OrderRescheduling';
import { notifyError } from '../../../../../helpers/notify';
import OverlayLoader from "../../Common/Loader";

type Value = CalendarProps['value'];

const DueDateCellRenderer = (params: any) => {

  const [currDate, setCurrDate] = useState(() => {
    if (!_.isEmpty(params.data)) {
      return params.data.dd;
    }
  });
  const [showCalendar, setShowCalendar] = useState(false);
  const format2 = "YYYY-MM-DD";
  const [minDate] = useState(new Date());

  const inputRef = useRef<HTMLInputElement>(null);
  const calendarRef = useRef<HTMLDivElement>(null); 

  const [isLoading, setIsLoading] = useState(false);
  const {mutateAsync:getHolidaysForMaxFolCCROfOrder}=useGetHolidaysForMaxFolCCROfOrder()

  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  useEffect(() => {
    if (!params.node.selected && !_.isEmpty(params.data)) {
        params.data.dd = params.data.oldDate;
        setCurrDate(params.data.oldDate);
        setShowCalendar(false);
      }
  }, [params.node.selected]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        //if user is inside calendar
        showCalendar &&
        calendarRef.current &&
        !calendarRef.current.contains(target) &&
        //if user is in input field
        inputRef.current &&
        !inputRef.current.contains(target)
      ) {
        setShowCalendar(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showCalendar]);

  const handleDateChange = (value: Value) => {
    if (value && !(value instanceof Array) && !_.isEmpty(params.data)) {
      const formattedDate = moment(value).format(format2);
      setCurrDate(formattedDate);
      params.data.dd = formattedDate;
      setShowCalendar(false);
    }
  };

  if (_.isEmpty(params.data)) {
    return <></>
  }

  const [holidayDates, setHolidayDates] = useState<any>([])
  const [forceOpenCalendar, setForceOpenCalendar] = useState(false);
  const [maxDate, setMaxDate] = useState<Date | undefined>(undefined);

  const handleCalendarIconClick = async (rowData: any) => {
    try {
      setForceOpenCalendar(false); 
      setIsLoading(true)
      const data = await getHolidaysForMaxFolCCROfOrder(rowData.odk);
      setHolidayDates(data.data.data.holidays || []);
      setMaxDate(data.data.data.schhor?  new Date(data.data.data.schhor): undefined);
  
      if (data.status == 200) {
        setTimeout(() => {
          setIsLoading(false)
          setForceOpenCalendar(true);
        },500)

      }
      else {
        setIsLoading(false)
        setForceOpenCalendar(false);
        notifyError("Failed to fetch holidays")
      } 
  
    } catch (error) {
      setIsLoading(false)
      setForceOpenCalendar(false);
      notifyError("Failed to fetch holidays");
    }
  };

  const tileDisabled = ({ date }:any) => {
    const formattedDate = moment(date).format('YYYY-MM-DD');
      return holidayDates.includes(formattedDate);
    }

  

  return (
    <>
    {(isLoading ) && (
      <OverlayLoader />
    )}

    <VFDatePicker
      dateInputStyle={{
        background: 'transparent',
        paddingLeft: '-10px',
        color: params.data.oldDate === currDate ? 'black' : '#BC3D81',
      }}
      themeUi={themeUi}
      enableIconClick={true}
      onDateChange={handleDateChange}
      date={!params.node.selected ? params.data.oldDate : currDate}
      minDate={minDate}
      maxDate={maxDate}
      onClick={() => handleCalendarIconClick(params.data)}
      showCalendarIcon={params.node.selected}
      forceOpenCalendar={forceOpenCalendar}
      tileDisabled={tileDisabled}
      />
    </>
  );
};

export default React.memo(DueDateCellRenderer);
