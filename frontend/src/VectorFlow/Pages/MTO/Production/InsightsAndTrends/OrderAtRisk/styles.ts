import styled from "styled-components";
import * as gridSystem from "../../../../../../styles/gridSystem";


export const ChartWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:100%;
    width:100%;
`
export const HorizontalViewWrapper = styled.div`
      width:100%;
      height:90%;
      & > .ag-theme-alpine{
            height: 100%;
            margin-top: 0 !important;
      }
`
export const OrderAtRiskChartWrapper = styled.div`
      display:flex;
    flex-direction:column;
    width:100%;
    margin-top:20px;
    margin-bottom:20px;
    height:100%;
    `

    
    export const VFTableWrapper = styled.div<{ height?: string, disableZoomScaling?: boolean }>`
    height:${(props) => props.height ? props.height : 'auto'};
    max-height:93%;
    position: relative;
    zoom: 1;
    width:100%;
    // padding-right: 25px;
    display: flex;
    flex-direction: column;
    height: 100%;
    margin: 20px 0px;
    & > .ag-theme-alpine {
      flex: 1 !important;
    }

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) 
    {
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
      position: absolute !important;
      bottom:0 !important; 
      background-color: white !important;
      width:100%  !important; 

    }    
` 