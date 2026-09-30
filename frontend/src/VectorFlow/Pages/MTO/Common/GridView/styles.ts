import styled from 'styled-components';
import * as gridSystem from '../../../../../styles/gridSystem'


export const ApplyZoomOut = styled.div`
    zoom: 0.7;
`

export const VFTableWrapper = styled.div<{ height?: string, disableZoomScaling?: boolean }>`
    height:${(props) => props.height ? props.height : 'auto'};
    // max-height:90%;
    margin:20px;
    width:100%,

    & > div[data-testid="vf_pagination"]{
      margin-top: 0 !important;
  }

    & .ag-theme-alpine .ag-header-row:nth-child(2) {
      background-color: #F7F7F7;
      color: black;
      height: 40% !important;
      width: 100% !important;
    }

 
    & .ag-theme-alpine {

        margin: 0 !important;
      }
    & .ag-theme-noir-fusion {
        margin: 0 !important;
      }

      & .ag-header-container {
        height: 60% !important;
        --ag-grid-size: 2px !important;
        --ag-list-item-height: 12px !important;
        --ag-font-size: 10px !important;
        font-size: 14px;
        // top: -10px;
      }

      & .ag-header  {
        height: 26% !important;
        min-height: 26% !important;
      }
      & .ag-header-row{
        height: 80% !important;
      }
      
      & .ag-header-row-column-filter{
        height: 80% !important;
        top: 90% !important;
      }
      & .ag-header-viewport  {
        // height: 70% !important;
      }

      & .ag-pivot-off{
        top: -10px;
      }
      & .ag-floating-filter {
        top: -5px;
      }

      & .ag-advanced-filter-header{
        height: 10% !important;
      }

      & .ag-header-cell {
        padding-top: 10px;
        height: 100% !important;
      }

      & .ag-cell {
        height: 100% !important
      }
    
`
export const PaginationWrapper = styled.div`

`


export const ETACellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    height:100%;
    width:100%;
`

export const ETACellValue = styled.p`
    display:flex;
    justify-content:center;
    align-items:center;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    height:30px;
    width:100%;
    padding:4px;
`

export const SCDynamicContainer = styled.div`
    display:block;
    height:150vh;
    padding:20px;
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) {
        height:70vh
    }
  
    @media (min-width: ${gridSystem.size.desktop}) {
      height:110vh
    }

    & > div[data-testid="vf_pagination"]{
      margin-top: 0px !important;
      // padding: 0 20px;
  }


    & .ag-header-cell-text {
      font-size: 12px;
  }
  & > .ag-theme-alpine{
    --ag-grid-size: 3px !important;
    --ag-list-item-height: 20px !important;
    --ag-font-size: 10px !important;
      flex: 1;
      height: 100%;
      --ag-row-hover-color: rgb(188, 61, 129,0.3) !important;

      & .ag-cell {
        height: 100% !important;
      }

      & .ag-paging-panel {
        height: 24px !important;
      }

      & .ag-side-buttons {
        font-size: 10px;
      }

      & .ag-header {
        border-radius: 0;
      }

      & .ag-pivot-off{
        height: 47px !important;
        min-height: 47px !important;

      }
     
      & .ag-header-cell {
        min-height: 24px !important;
        height: 24px !important;
      }
      & .ag-header-row {
        min-height: 20px !important;
        height: 20px !important;
      }
      & .ag-header-container {
        min-height: 20px !important;
        height: 20px !important;
      }
      
      
       & .ag-header-row-column-filter{
        top: 23px !important;
        height: 24px !important;
       }

      
       & .ag-input-field-input {
        height: 14px !important;
        min-height: 10px !important;
        font-size: 12px;
       }
      & .ag-column-drop{
        background: #D2CECE;
      }

      & .ag-status-bar{
        // height: 24px !important;
        font-size: 12px;
      }
  }

  
   

    
`
