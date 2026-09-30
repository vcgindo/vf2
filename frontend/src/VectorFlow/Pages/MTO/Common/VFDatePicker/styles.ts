import styled from 'styled-components';
import Calendar, { CalendarProps } from 'react-calendar';

export const DatePickerWrapper = styled.div`
    display: flex;
    cursor: pointer;
    flex-direction: row;
    width: 180px;
    padding: 5px;
    justify-content: sapce-between;
`;

export const TextInputWrapper = styled.input`
  width: 80%;
  height: 100%;
  text-align: center;
  letter-spacing: 0px;
  opacity: 1;
  font-size: 12px;
  padding: 4px;
  font-family: Roboto;
  border: none;
  pointer-events: none;
  background: transparent;
`;

export const DateInputWrapper = styled.input`
  opacity: 0;
  position: absolute;
  pointer-events: none;
`;

export const ButtonWrapper = styled.button`
  background: none;
`;

export const ImageWrapper = styled.img`
  cursor: pointer;
  height: 15px;
  width:15px;
`;

// Extended CalendarProps with themeUi for custom propss
type StyledCalendarProps = CalendarProps & { themeUi: string } ;

export const StyledCalendar = styled(Calendar)<StyledCalendarProps>`
  width: 250px;

  .react-calendar__navigation__label__labelText {
    font-weight: 400 !important; 
  }

  .react-calendar__navigation button:disabled {
    background-color: #e6e6e6;
  }

  .react-calendar__navigation button {
    min-width: 40px;
    background: none;
  }

  .react-calendar__navigation button:enabled:focus {  
    background-color: ${(props) => props.themeUi === "REGALBLAZE" ? "#C7810E" : "#82104C"};
    color: white;  
  }

  .react-calendar__navigation button:disabled:hover {
    background-color: rgb(230, 230, 230);
  }

  .react-calendar__month-view__weekdays__weekday {
    text-decoration: none;
  }

  .react-calendar__tile--now {
    background: ${(props) => props.themeUi === "REGALBLAZE" ? "#E1B69F" : "#e2a9c8"};  
  }

  .react-calendar__tile--active {
    background-color: ${(props) => props.themeUi === "REGALBLAZE" ? "#C7810E" : "#82104C"};
    color: white;
  }

  .react-calendar__tile--hasActive {
    background-color: ${(props) => props.themeUi === "REGALBLAZE" ? "#C7810E" : "#82104C"};
    color: white;
  }

  .react-calendar__tile:disabled {
    background-color: white;
    color: #ababab;
  }

  .react-calendar__tile:disabled:hover {
    background-color: white;
  }

  .react-calendar__month-view__days__day--weekend {
    color: #121212;
  }

  .react-calendar__tile:hover {
    background-color: ${(props) => props.themeUi === "REGALBLAZE" ? "#fee3b7" : "rgba(188, 61, 129, 0.2)"};  
    color: black;
  }

  .react-calendar__navigation button:hover {
    background-color: ${(props) => props.themeUi === "REGALBLAZE" ? "#fee3b7" : "rgba(188, 61, 129, 0.2)"};  
  }

.react-calendar__month-view__days__day--neighboringMonth,
.react-calendar__month-view__days__day--neighboringMonth.react-calendar__tile--weekend {
  color: #757575 !important;
}


`;
