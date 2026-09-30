import styled from "styled-components";

// Top-level container for Tabs and Toolbar
export const TabsToolbarRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  // margin-top: 5px;
  position: relative;
`;

// Left Section - Tabs
export const TabsSection = styled.div`
  flex: 0 0 auto;
  padding-left: 20px;
`;

// Toolbar (Right)
export const ToolbarAbsolute = styled.div`
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
`;

// Filter Column Group (Select / Date pickers)
export const FilterColumn = styled.div<{ minWidth?: string }>`
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: ${({ minWidth }) => minWidth || "140px"};
`;

// Label for filter fields
export const FilterLabel = styled.span`
  font-family: Roboto;
  font-weight: 300;
  font-size: 10px;
  color: #434343;
`;

// Date Pickers Row
export const DatePickersRow = styled.div`
  display: flex;
  gap: 8px;
  align-items: flex-start;
`;

// Date Column
export const DateColumn = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 150px;
`;

// Date Field Container
export const DateFieldContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #cccccc;
  background: #fff;
  height: 25px;
  width: 140px;
  padding: 0 10px;
`;

export const FilterWrapper = styled.div`
  margin-left: 15px;
  width: 780px;
  padding-left: 10px;
  display: flex;
  align-items: center;
  gap: 15px;
  min-height: 76px;
`;

export const MyFutureOrderTabsFix = styled.div`
  .cqHMwT {
    min-width: 0 !important;
    padding-right: 10 !important;
    width: auto !important;
  }
`;


