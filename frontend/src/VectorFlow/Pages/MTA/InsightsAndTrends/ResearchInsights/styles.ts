import styled from "styled-components";
import * as globalStyles from '../../../../../styles/global'

export const ResearchInsightsLayout = styled.div`
    // margin-top:10px
    margin-top:5px;
    margin-left:20px;
    // min-height:100vh;
    height: 85%;
    display:grid;
    grid-template-columns:3fr 1fr;
    padding-bottom:50px;


    
`

export const ResearchInsightsTableWrapper = styled.div`
    display:flex;
    flex-direction:column;
`

export const ResearchInsightsTableTaskBar = styled.div`
    width:100%;
    padding:10px 15px;
    // margin-top:-10px;
`

export const AvailabilityTrendWrapper = styled.div`
    // height:calc(640px * 0.75);
    height:100%;
    // overflow-y:auto;
    // &::-webkit-scrollbar{
    //    display:none;      
    // }
    width:100%;
    min-width:300px;
    background-color:white;
    border-radius:12px;
    box-shadow: rgba(149, 157, 165, 0.2) 0px 8px 24px;
    position:relative;
`
export const AvailabilityTrendHeader = styled.div<{themeUi:string}>`
    background-color:${(props)=>props.themeUi==="PUREELEGANCE"?'black':globalStyles.chooseThemeColor[props.themeUi].color1};
    padding:5px;
    color:white;
    width:100%;
    text-align:center;
    font-size:14px;
    font-weight:500;
    font-family:Roboto;
    border-radius:12px 12px 0px 0px;
    position:sticky;
    top:0;
`

export const AvailabilityTrendSection = styled.div`
    margin-bottom:10px;
    padding:5px 10px 15px 10px;
    width:100%;
    // border-bottom:dashed 2px #B2B2B2;
`

export const HistoricalAvailabiltyHeader = styled.p`
    font-weight:500;
    font-size:10px;
    margin-bottom:5px;
`

export const HistoricalAvailabiltyContent = styled.div`
    width:100%;
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    padding:4px;
    box-shadow: rgba(99, 99, 99, 0.2) 0px 2px 8px 0px;
    border-radius:4px;
`

export const HistoricalAvailabiltyContentSection = styled.span`
    display:flex;
    flex-direction:column;
    align-items:center;
   border-right:1px solid black;
`

export const HistoricalAvailabiltyContentSectionHeader = styled.p`
    display:inline;
    font-weight:400;
    font-size:7px;
    line-height:10px;
    color:#383737;
`

export const HistoricalAvailabiltyContentSectionData = styled.p`
    display:inline;
    font-weight:700;
    font-size:11px;
    color:black;
`

export const HorizonHeader = styled.p`
    text-align:center;
    font-weight:500;
    font-size:14px;
    margin-bottom:-10px;

`

export const ChartHeader = styled.div`
    width:100%;
    display:flex;
    // align-items:center:
    gap:12px;
    justify-content:space-between;

    
`

export const ChartHeaderText = styled.p`
    font-size:10px;
    font-weight:400;
    display:flex;
    align-items:center;
`

export const ChartHeaderRadioGroup = styled.div<{theme:string}>`
    display:flex;
    align-items:center;
    justify-content:center;
    accent-color:${(props)=>globalStyles.chooseThemeColor[props.theme].color5};
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
`


export const CapsuleWrapper = styled.div`
    // width:100%;
    // max-width:80px;
    // margin-left:auto;
    zoom:0.7;
    width:180px;

`

export const CalenderWrapper = styled.div`
    width:100%;
    background-color:#F4F4F4;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
    margin-top:10px;
    border-radius:4px;
    zoom:0.9;
    box-shadow: rgba(0, 0, 0, 0.16) 0px 1px 4px;
    margin-top:15px;
`
export const CalenderHeader = styled.p`
    width:100%;
    text-align:center;
    font-weight:500;
    font-size:13px;
    border-bottom:solid 1px #D0CCCC;
    padding:5px;
   
`
export const CustomCalenderCaptionWrapper = styled.div`
    display:flex;
    justify-content:space-between;
    align-items:center;
`

export const CustomCalenderCaptionArrow = styled.img`
    width: 14px;
    height: 14px;
    cursor:pointer;
`

export const CustomCalenderCaptionHeader = styled.p`
    font-size:13px;
    font-weight:500;
`

export const CustomCalenderDayWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    border-radius:4px;
    box-shadow: rgba(50, 50, 93, 0.25) 0px 13px 27px -5px, rgba(0, 0, 0, 0.3) 0px 8px 16px -8px;
    height:100%;
    width:100%;
    cursor:pointer;
`

export const ChartWrapper = styled.div`
    position:relative;
    width:100%;
    padding-top:10px;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const CalenderSummaryWrapper = styled.div`
    display:flex;
    flex-direction:row;
    width:100%;
`

export const CalenderSummaryCell = styled.div`
display:flex;
flex-direction:column;
align-items:center;
width:100%;
`
export const CalenderSummaryCellText = styled.p`
    font-weight:400;
    font-size:9px;
    text-align:center;
`

export const CalenderSummaryCellContentWrapper = styled.div`
    display:flex;
    flex-direction:row;
    align-items:center;
`

export const CalenderSummaryCellContent = styled.p`
    font-weight:500;
    font-size:12px;
`
export const CalenderSummaryCellContentStick = styled.div`
    height:15px ;
    width:2px;
    margin-left:5px;
`

export const ExpandChartIcon = styled.img`
    position:absolute;
    right:0;
    top:5px;
    height:20px;
    width:20px;
    z-index:20;
    cursor:pointer;
`

export const ExpandedChartFilterWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:row;
    align-items:center;
    padding:10px;
    margin-top:20px;
    border-bottom:2px dashed gray;
`


export const ExpandedChartSelectWrapper = styled.div`
    display:flex;
    flex-direction:row;
    justify-content:center;
    align-items:center;
    margin-right:20px;
`

export const ExpandedChartSelectLabel = styled.p`
    margin-right:15px;
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:12px;
    line-height:26px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
`

export const ExpandedChartCapsuleWrapper = styled.div`
    // width:100px;
    margin-left:auto;
    // margin-right:5px;
    zoom:0.8;
`

export const RadioGroup = styled.span`
    display:flex;
`

export const DefaultViewRendererWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    flex-direction:column;
    align-items:center;
    padding-top:140px;
`

export const DefaultViewRendererHeader = styled.p`
    font-weight:500;
    font-size:20px;
    line-height:30px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    text-align:center;
`

export const DefaultViewRendererText = styled.p`
    font-weight:300;
    font-size:20px;
    line-height:25px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    text-align:center;
    padding:0px 60px;
    margin-top:10px;
    margin-bottom:10px;
`