import styled from "styled-components";
import * as gridSystem from "../../../../../../../styles/gridSystem";

export const TableResizebarWrapper = styled.div`
  position: relative;
  width: 100%;
`;

export const TableContainer = styled.div`
  width: 100%;
  overflow: hidden;

  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    position: relative;
    width: 100%;
    overflow: hidden;
  }
`;

export const ResizeBar = styled.div`
  position: absolute;
  width: 100%;
  height: 10px; /* Height of the resize bar */
  border-radius: 4px;
  background-color: #8080804d;
  cursor: ns-resize; /* Cursor style for resizing */
  bottom: 0px; /* Adjust distance from the bottom of the table */
  left: 0px;
`;

export const TableWrapper = styled.div`
  width: 100%;
  text-align: center;
  & .ag-theme-alpine {
    margin: 20px 0;
  }
`;

export const CellWithBar = styled.div`
  font-weight: 400;
  font-size: 18px;
  color: #686060;
  letter-spacing: 0;
  letter-spacing: 21;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 20px;

  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    font-weight: 400;
    font-size: 18px;
    color: #686060;
    letter-spacing: 0;
    letter-spacing: 21;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-right: 10px;
  }
`;

export const BarContainer = styled.div`
  width: 100px;

  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    width: 30px;
  }
`;

export const CellBar = styled.div`
  background-image: linear-gradient(to right, #8d2e61, #bb3f81, #db6ba7);
  height: 20px;
  border-radius: 2px;
`;

export const CellBarValue = styled.div`
  margin-right: 20px;

  @media only screen and (min-width: ${gridSystem.size
    .mobileS}) and (max-width: ${gridSystem.size.mobileL}) {
    margin-right: 0px;
  }
`;

export const VFTableWrapper = styled.div<{ height?: string, disableZoomScaling?: boolean }>`
    height:${(props) => props.height ? props.height : 'auto'};
    // max-height:90%;
    position: relative;
    zoom: 1;
    width:100%;
    // padding-right: 25px;
    display: flex;
    height: 100%;
    margin: 20px 0px;
    & .ag-theme-alpine {
      flex: 1;
    }

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) {
        ${props => props.disableZoomScaling ? 1 : 0.75};
    }
  
    @media (min-width: ${gridSystem.size.desktop}) {
      zoom:1;
    }

    & .ag-paging-panel {
       z-index: 1; 
      font-size: 11px !important;
      font-family:'Roboto' !important;
      position: relative !important;
    }

    & .ag-status-bar{
      z-index: 2 !important; 
      display: flex  !important; 
      justify-content: space-between !important;
      align-items: center !important;
      border:none !important;
      width: calc(100% - 230px) !important;
      position: absolute !important;
      bottom:0 !important; 
    }    
` 