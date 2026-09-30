import styled from "styled-components";

export const DayWiseCoverageHeaderContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 1.5rem;
  zoom: 0.75;
`;

export const DayWiseCoverageStatus = styled.div<{ color?: string }>`
  &::before {
    content: "";
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background-color: ${(props) => props.color};
    display: block;
  }
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 16px;
`;

export const CalenderContainer = styled.div`
  width: 100%;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: rgba(0, 0, 0, 0.1) 5px 2px 14px 3px;
  margin: 16px 0;
`;

export const CalenderTitle = styled.h1`
  background: black;
  color: white;
  margin: 0;
  padding: 5px 16px;
  font-size: 12px;
`;

export const CalenderContent = styled.div`
  display: flex;
`;
export const CalenderMonths = styled.div`
  border-right: 1px solid lightgrey;
  display: flex;
  flex-direction: column;
  padding-bottom: 2rem; // for scrollbar width
`;
export const CalenderMonth = styled.div`
  padding: 8px 18px;
  margin: 0.5rem;
  border: none;
  font-size: 12px;
  display: flex;
  align-items: center;
  flex: 1;
`;

export const Divider = styled.div`
  width: 0.5px;
  background-color: grey;
`;

export const Text = styled.div`
  font-size: 16px;
  display: flex;
  align-items: center;
  font-weight: bold;
`;

export const Calender = styled.table`
  font-size: 10px;
  width: 100%;
  overflow: auto;
  display: block;
  border-collapse: collapse;
`;
export const Day = styled.td<{ color: string }>`
  padding: 8px;
  border: none;
  margin: 1rem 0.65rem;
  width: 22px;
  height:22px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: ${(props) => props.color};
  color: white;
  border-radius: 50%;
  cursor: pointer;
`;

export const Month = styled.tr`
  border-bottom: 1.5px dashed lightgrey;
  display: flex;
`;

export const Icon = styled.img``;

export const TableContainer = styled.div`
  background: white; 
  border-radius: 8px; 
  // min-height:400px; 
  display:flex; 
  flex:1;
  justify-content:center; 
  align-items:center;
  width:100%;
  margin: 1rem 0;
  margin-bottom: 2rem;
  box-shadow: rgba(0, 0, 0, 0.1) 5px 2px 14px 3px;
  & > .ag-theme-alpine{
    width: 100%;
    margin: unset;
    height: 100% !important;
    min-height: 400px;
  }
`

export const AnimationWrapper = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  gap: 2rem;
`

export const HelperText = styled.div`
  font-size: 22px;
  width: 65%;
  text-align: center;
`
export const AnalyticsTable = styled.table`
    background: rgb(56, 55, 55);
    color: white;
    margin: 1rem;
    font-size: 12px;
    border-collapse: collapse;
    padding: 1rem;
    display: block;
    border-radius: 4px;
`

export const AnalyticsRow = styled.tr`
  thead &:nth-of-type(2){
    border: 1px dashed #B4B4B4;
    border-left: none;
    border-right: none;
  }
`
export const AnalyticsCol = styled.td`
  padding: 0.5rem;
  text-align: center;
`

// export const PageWrapper = styled.div`
// & .ag-header-cell-text {
//   font-size: 17px;
// }
// `


