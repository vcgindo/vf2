import styled from 'styled-components'
import * as gridSystem from '../../../../../../styles/gridSystem'

export const BTRTableWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:400px;
    width:100%;
    margin-top:20px;
    margin-bottom:20px;
    height:100%;
`
export const BTRAllomentSection = styled.div`
    display:flex;
    flex-direction:column;
    height:100%;
    max-height:100%;
`

export const HorizontalViewWrapper = styled.div`
    //   display:flex;
      width:100%;
`

export const SCChartContainer = styled.div<{ height?: string }>`
    padding:5px;
    border-radius:12px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    // box-shadow: -5px 5px 25px #86868633;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 12px;
    margin: 20px;
    // height:547px;
    height:${props => props.height ? props.height : 'auto'}
`

export const SCHorizontalDivider = styled.hr`
    width:100%;
    border: none;
    border-top:1px solid #B2B2B2;
`
export const BPRColorCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 100%;
    height: 90%;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 4px;
    position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`
export const SCDynamicContainer = styled.div`
    display:block;
    height:150vh;
    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.desktop}) {
        height:70vh
    }
  
    @media (min-width: ${gridSystem.size.desktop}) {
      height:110vh
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
        height: 24px !important;
        font-size: 10px;
      }
  }   
`