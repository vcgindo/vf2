import styled from "styled-components"

export const CapsuleWrapper = styled.div`
     width:100%;
    // max-width:120px;
    margin-left:auto;
`
export const ChartWrapper = styled.div`
    position:relative;
    width:100%;
    // padding-top:-100px;
    display:flex;
    justify-content:center;
    align-items:center;
    height: 100%;
    & .chart-wrapper > div{
        height: 100% !important;
        & .ag-charts-wrapper{
          max-height: 100% !important;
          .ag-charts-canvas{
            height: 100%;
          }
          & .ag-charts-canvas >canvas{
            height:100% !important;
          }
        }
      }
`

export const GraphViewWrapper = styled.div`
  width: 100%;
  height: 100%;
  padding-left: 20px;
  padding-top: 20px;
  padding-bottom: 20px;
`