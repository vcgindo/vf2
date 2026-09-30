import styled from "styled-components";

export const SCChartContainer = styled.div<{ height?: string }>`
    padding:5px;
    border-radius:12px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    // box-shadow: -5px 5px 25px #86868633;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 12px;
    margin: 20px;
    display: flex;
    flex-direction: column;
    
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


export const TableWrapper = styled.div`
    // height : 95vh;
    height: 100%;
    zoom: 1;
    display: flex;
    flex-direction: column;
    margin-left: 2rem;
    margin-top: 1rem;
    padding-bottom: 20px;

    & > .ag-theme-alpine {
        flex: 1;
        margin-bottom: 0 !important;
    }
    
    & div[data-testid="vf_pagination"]{
      margin-top: 0 !important;
    }
    
`