import styled from "styled-components";

export const DatePickerContainer = styled.div`
  width: 200px;
  height: 43px;
`;

export const DateInput = styled.input`
  width: 100%;
  height: 100%;
  text-align: left;
  font: 24px;
  letter-spacing: 0px;
  color: #000;
  font-size: 18px;
  padding: 4px;
  font-weight: bold;
  font-family: Roboto;
  border: 0.5px solid #acacac;
  border-radius: 5px;
  &::-webkit-calendar-picker-indicator {
  }

`;
