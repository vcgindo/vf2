import styled from "styled-components";

export const SCChartContainer = styled.div<{ height?: number }>`
    padding:5px;
    border-radius:12px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 12px;    margin-right:5px;
    // margin-top:60px;
    margin-bottom:20px;
    margin-left:5px;
    // height:547px;
    height:${props => props.height ? props.height + 'px' : 'auto'}
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

