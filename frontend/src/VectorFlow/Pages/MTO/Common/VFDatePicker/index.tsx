import { useEffect, useRef, useState } from 'react';
import moment from 'moment';
import {CalendarProps} from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import ReactDOM from 'react-dom';
import { useUserData } from "../../../../../context/index";
import {
  DatePickerWrapper,
  TextInputWrapper,
  ButtonWrapper,
  ImageWrapper,
  StyledCalendar
} from './styles';

interface CustomDatePickerProps {
    date: any;
    onDateChange: any;
    themeUi?: string;
    minDate?: any;
    disabled?: boolean;
    dateInputStyle?: React.CSSProperties;
    imgStyle?: React.CSSProperties;
    showCalendarIcon?: boolean;
    onClick?: any,
    enableIconClick?: boolean;
    forceOpenCalendar?: boolean;
  maxDate?: any;
  tileDisabled?: any
  }
  



type Value = CalendarProps['value'];


const VFDatePicker = ({
  date,
  onDateChange,
  disabled = false,
  dateInputStyle,
  imgStyle,
  showCalendarIcon,
  minDate,
  onClick,
  enableIconClick,
  forceOpenCalendar,
  tileDisabled,
  maxDate,
}: CustomDatePickerProps) => {
  const [showCalendar, setShowCalendar] = useState(false);
  const [calendarPosition, setCalendarPosition] = useState({ top: 0, left: 0 });
  const inputRef = useRef<HTMLInputElement>(null);
  const calendarRef = useRef<HTMLDivElement>(null);

  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
    
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        showCalendar &&
        calendarRef.current &&
        !calendarRef.current.contains(target) &&
        inputRef.current &&
        !inputRef.current.contains(target)
      ) {
        setShowCalendar(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showCalendar]);

  const toggleCalendar = () => {
    if (disabled) return;
    const rect = inputRef.current?.getBoundingClientRect();
    if (rect) {
      setCalendarPosition({
        top: rect.bottom + window.scrollY,
        left: rect.left + window.scrollX
      });
    }
    setShowCalendar(prev => !prev);
  };

  const handleCalendarChange = (value: Value) => {
    if (value instanceof Date) {
      const formatted = moment(value).format('YYYY-MM-DD')
      onDateChange(formatted);
      setShowCalendar(false);
    }
  };

  useEffect(() => {
    if (forceOpenCalendar) {
      const rect = inputRef.current?.getBoundingClientRect();
      if (rect) {
        setCalendarPosition({
          top: rect.bottom + window.scrollY,
          left: rect.left + window.scrollX,
        });
      }
      setShowCalendar(true);
    }
  }, [forceOpenCalendar]);
  


  
  return (
    <DatePickerWrapper>
      <TextInputWrapper
        ref={inputRef}
        type="text"
        value={date ? moment(date).format('YYYY-MM-DD') : ''}
        placeholder="DD-MM-YYYY"
        readOnly
        onClick={toggleCalendar}
        disabled={disabled}
        style={dateInputStyle}
      />

      {showCalendarIcon &&
        <>
        <ButtonWrapper type="button"
         onClick={(e) => {
          if (enableIconClick && onClick ) {
            onClick(e);  
            return;
           }
           toggleCalendar();
        }}
        >
            <ImageWrapper
            style={imgStyle}
              src={
                themeUi === 'REGALBLAZE'
                  ? '/assets/img/mto/OrderRescheduling/edit-calendar-yellow.svg'
                  : '/assets/img/mto/OrderRescheduling/edit-calendar.svg'
              }
              alt="calendar-icon"
            />
          </ButtonWrapper>

          {showCalendar &&
            ReactDOM.createPortal(
              <div
                ref={calendarRef}
                style={{
                  position: 'absolute',
                  top: calendarPosition.top,
                  left: calendarPosition.left,
                  zIndex: 9999,
                  backgroundColor: 'white',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
                }}
              >
                <StyledCalendar
                  themeUi={themeUi}
                  onChange={handleCalendarChange}
                  value={date ? new Date(date) : new Date()}
                  minDate={minDate}
                  maxDate={maxDate}
                  tileDisabled={tileDisabled} 
                />
              </div>,
              document.body
            )}
        </>
      }
    </DatePickerWrapper>
  );
}

export default VFDatePicker;
