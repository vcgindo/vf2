import styled from "styled-components";
import { ColorsMTO } from "../Colors";

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
    // height:90%
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
export const SCChartLayout = styled.div`
    overflow-y:scroll;
    display:flex;
    height:100%;
    flex-direction:column;
    // margin-top:30px;
`;

export const SCChartHeaderContainer = styled.div`
    background-color:white;
    display:flex;
    justify-content:center;
    align-items:center;
    height: 54px;
   
`

export const SCChartSliderContainer = styled.div`
    display: flex;
    justify-content:space-between;
    justify-content:center;
    gap:13px;
    align-items:center;
    height:55px


`

export const SCChartMainContainer = styled.div`
    display: flex;
    justify-content:space-between;
    
`
export const HorizonHeader = styled.p`
    text-align:center;
    font-weight:500;
    font-size:10px;
`

export const SCChartHeader = styled.p`
    font-weight:500;
    font-size:16px;
    line-height:21px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
`

export const SCHorizontalDivider = styled.hr`
    width:100%;
    border: none;
    border-top:1px solid #B2B2B2;
`




export const BTRLayoutWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:90%;
`

export const BTRLayoutTabsWrapper = styled.div`
    display:flex;
    justify-content:center;
    margin-top:25px;
    z-index:200;
`

export const ToggleViewBtnWrapper = styled.div`
    position:absolute;
    right:35px;
    zoom:0.6;
    z-index:0;
    margin-top:-10px;
`

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

export const BTRTableHeader = styled.p`
    font-size:13px;
    font-weight:500;
    margin:0px 25px;
`

export const BTRAvailabiltyCellRendererWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const BTRAvailabiltyCellRenderer = styled.div<{ value: number }>`
    position:relative;
    height:100%;
    max-height:15px;
    width:45px;
    background: #DEDEDE 0% 0% no-repeat padding-box;
    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom:0;
        width:${(props) => props.value}%;
        background: transparent linear-gradient(270deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box;
      }
`


export const CategoryCellRendererWrapper = styled.div`
height: 100 %;
width: 100 %;
display: flex;
align - items: center;
justify - content: center;
`

export const CategoryCellRendererChip = styled.div`
    width: 18px;
    min-width:18px;
    height: 18px;
    display:flex;
    font-size:8px;
    font-family:Roboto;
    align-items:center;
    justify-content:center;
    margin-left:5px;
    background-color: #355FD3;
    border-radius:4px;
    box-shadow: 0px 4px 5px #00000043;
`

export const AvailabilityToolTipWrapper = styled.div`
    height: 27px;
    display:flex;
    align-items:center;
    justify-content:center;
    background-color: black;
    color:white;
    padding:15px;
    border-radius: 4px;
    font-size:9px;
`

export const CategoryToolTipWrapper = styled.div`
    display:flex;
    flex-direction:column;
    width: 150px;
    border-radius:4px;
    overflow:hidden;
`

export const CategoryToolTipSection = styled.div`
width: 100 %;
padding: 10px;
display: flex;
flex - direction: column;
`

export const CategoryToolTipSectionHeader = styled.p`
    font-weight:500;
    width:100%;
    font-size:10px;
    text-align:center;
    font-family:Roboto;
`

export const CategoryToolTipSectionDescription = styled.div`
    font-weight:300;
    font-size:9px;
    text-align:center;
    font-family:Roboto;
    margin-top:5px;
`

export const LockBtnWrapper = styled.div`
    position:relative;
    z-index:300;
`

export const LockBtn = styled.img`
    position:absolute;
    height:25px;
    width:25px;
    cursor:pointer;
`

export const HorizontalViewWrapper = styled.div`
      display:flex;
      width:100%;
`


export const Separator = styled.div`
      height: 100%;
      width: 15px;
      margin: 5px;
      display: flex;
      justify-content: center;
      align-items: center;
      pointer-events: none;
`

export const ViewSlider = styled.div`
    height: 80%;
    width: 100%;
    background: ${ColorsMTO.LightGrey.code};
    border-radius: 5px;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
`
