import styled from 'styled-components'

import Calendar, { CalendarProps } from 'react-calendar';

export const EOLayout=styled.div`
    margin-top:25px;
    margin-left:-36px;
`

export const EOColorCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 97px;
    height: 34px;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 4px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
`

export const EOTagsCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 55px;
    height: 25px;
    background: #8E8E8E 0% 0% no-repeat padding-box;
    color: #FFFFFF;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 2px;
    font-style:normal;
    font-variant:normal;
    font-weight:medium;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
`


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
  font: 14px;
  letter-spacing: 0px;
  opacity: 1;
  font-size: 14px;
  padding: 4px;
  font-style:normal;
  font-variant:normal;
  font-weight: medium;
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
  height: 20px;
  width: 20px;
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
`;


export const SaveDueDateWrapper = styled.div`
    height:35px;
    width:100%;
    display:flex;
    justify-content:flex-end;
    // background-color:#23232f;
    align-items:center;
`;