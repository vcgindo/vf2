import styled from 'styled-components';
import * as globalStyles from '../../../../../../styles/global'

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

export const CapsuleWrapper = styled.div`
     width:20%;
    // max-width:120px;
    margin-left:auto;
`

export const HorizontalWrapper = styled.div`
display:flex;
margin-top: 10px;
padding-bottom: 10px;
`

export const GraphWrapper = styled.div`
width: 100%;
display:flex;
justify-content: center;
position: relative;
flex-grow: 1;
`

export const VerticalWrapper = styled.div`
    width: 25%;
    background: white;
    box-shadow: rgba(133, 132, 132, 0.247) -5px 4px 10px;
    border-radius: 5px;
    display: flex;
    align-items: center;
    flex-direction: column;
    zoom: 0.8;
`

export const HorizontalLineDashed = styled.div`
    border: 1px dashed gray; 
    width: 100%; 
`

export const SectionFlex = styled.div`
    padding: 10px;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
`

export const MarkerWrapper = styled.div`
    display: flex;
    align-items: center;
    gap: 5px;
`

export const CalenderHeading = styled.div`
    text-align: center;
    border-bottom: 1px solid #D0CCCC;
    padding: 5px;
`

export const CalenderWrapper = styled.div`
    background: #ACABAB33;
    border-radius: 8px;
    width: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
`

export const CalenderLabel = styled.div`
    display: flex;
    justify-content: space-around;
    padding: 0px 10px 10px;
`

export const VerticalTitle = styled.div`
    text-align: left;
    letter-spacing: 0px;
    color: #000000;
    opacity: 1;
    font-size: 21px;
    font-family: ROBOTO;
    font-weight: 500;
`

export const ColoredMarker = styled.div<{ color?: string }>`
    height: 15px;
    width: 15px;
    background: ${props => props.color ? props.color : 'gray'};
`

export const SCChartSliderContainer = styled.div`
    display: flex;
    justify-content:space-between;
    justify-content:center;
    gap:13px;
    align-items:center;
    height:55px
`

export const RadioGroup = styled.div`
    display:flex;
    min-width: 200px;
    & > div{
        flex: 1;
    }
`

export const SelectGroup = styled.div`
    display:flex;
    gap: 20px;
    & > div{
        flex: 1;
    }
`

export const ChartHeaderRadioGroup = styled.div<{ theme: string }>`
    display:flex;
    align-items:center;
    justify-content:center;
    accent-color:${(props) => globalStyles.chooseThemeColor[props.theme].color5};
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
`

export const SCVerticalDividerGray = styled.div`
  width: 0.5px;
  background-color: #c7c7c7;
  height: 40px;
  margin-right: 8px;
  margin-left: 8px;
  align-items: center;
`;