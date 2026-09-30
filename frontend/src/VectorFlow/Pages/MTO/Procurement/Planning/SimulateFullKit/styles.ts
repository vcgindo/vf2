import styled from 'styled-components';

export const Main = styled.div`
    margin-top:12px;
`

export const MainContainer = styled.div`
  display: flex;
  gap: 75px;
  margin-left:15px;
  padding: 0.75rem;
`

export const Box = styled.div`
    width: 210px;
    min-height: 12vh;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow:0px 6px 12px #74747429;
    //box-shadow: -5px 4px 20px #91919133;
    opacity: 1;
    border-radius: 6px;
    position: relative;
    display: flex;
    flex-direction:column;
    align-items:center;
    justify-content: space-between;
    margin-bottom:30px
`

export const PercentBorderContainer = styled.div`
    height: 100%;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
`

export const Percentborder = styled.div` 
    border: 3px solid #F0F0F0;
    border-radius: 50%;
    background-color:#CDCDCD;
    height: 50px;
    width: 50px;
    margin-left: auto;
    margin-right: auto;
    position: relative;
`

export const Percent = styled.h3`
    text-align: center;
`
export const BtnGroup = styled.div`
    height: 80px;
    width:100%;
    display: flex;
    //padding-top: 0;
    //background-color:#EBEBEB
    
`

export const Btns = styled.button`
    width: 100%;
    padding-top:5px;
    padding-right:5px;
    display: flex;
    justify-content: center;
    align-items: center;
`

export const TextXAxis = styled.h3`
    font-size:12px;
    text-align:center;
    transform:rotate(-90deg);   
    width:max-content;
    text-wrap:nowrap;
    //text-decoration:underline;
`

export const TextYAxis = styled.h3`
    font-size:12px;
    text-align:center;
    //text-decoration:underline;
    padding-bottom:4px;
    
`

export const ViewOrder = styled.button`
    font-size:10px;
    color:#BC3D81;
    margin-bottom:30px;
    background-color:#fcf0f7;
    width:70%;
    padding:10px;
    text-align:center;
    border-radius:8px;
`

export const TextOnBox = styled.div`
    position:absolute;
    bottom:100%;
    left:0;
    background-color:#E0E0E0;
    width:80px;
    border-radius:8px 8px 0 0;
    fontColor:#000;
    justify-content:'center';
    display:flex;
    align-items: center;
    justify-content: center;
`

export const ImgDiv = styled.div`
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: center;
    padding:1px;
    font-weight:bold;
`

export const ColorOnLeft = styled.div<{ color: string, height: string }>`
    position:absolute;
    right:100%;
    border-radius: 8px 0 0 8px;
    background-color: ${props => props.color ? props.color : null};
    width:20px;
    height:${props => props.height ? props.height : null};

    &:nth-of-type(1){
        top:0px;
        z-index: 0;
    }
    &:nth-of-type(2){
        top:15px;
        z-index:1;

    }
    &:nth-of-type(3){
        top:25px;
        z-index:2;
    }
`

export const Separator = styled.div<{ color: any }>`
    border-right:1px solid ${(props) => props.color};
    height:85%;
    margin:auto
    `


export const BTRLayoutTabsWrapper = styled.div`
    display:flex;
    zoom: 0.75;
    justify-content:center;
    margin-bottom:15px;
`

export const ButtonImg = styled.img`
    justify-content:center;
    align-item:center;
    margin-right:3px;
`
export const Btncount = styled.div`
    justify-content:center;
    align-item:center;
    width:100%;
`
export const diviLine = styled.div`
    width:"400" 
    style:"border: 2px dashed #C0C0C0" 
    color:"#FFFFFF" 
    size:"6"
`

export const TextOnColor = styled.h3`
    font-size: 10px;
    transform: rotate(-90deg);
    text-wrap: nowrap;
    color: white;
`
export const underLine = styled.div`
    width:"400" 
    style:"border: 1px solid #000" 
    color:"#000"    
`
export const ProcurementLayout = styled.div`
    height: 100vh;
    display: flex;
    flex-direction: column;

    & div[data-testid="vf_pagination"]{
        margin: -20px -15px !important;
        margin-bottom: 0px !important; 
    }

    & > .ag-theme-alpine{
          flex: 1 !important;

    }

`

/***Analytical screen css */
export const BPRDailyAnalyticsWrapper = styled.div`
    padding:0px;
    display:flex;
    flex-direction:column;
    align-items:center;
    
`

export const BPRDailyAnalyticsContainer = styled.div`
    display:flex;
    flex-direction:column;
    width:95%;
    background: #383737 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #00000034;
    padding:4px 8px;
    border-radius:4px;
`

export const BPRDailyAnalyticsHeader = styled.div`
   color:white; 
   margin-bottom:6px;
   //border-bottom:1px white solid;
`

export const BPRDailyAnalyticsTableContainer = styled.div`

`

export const BPRDailyAnalyticsTableHeaderContainer = styled.div`
    display:flex;
    flex-direction:row;
    color:white;
    width:100%
`

export const BPRDailyAnalyticsTableHeader = styled.div`
    width:100%;
    padding: 2px;
    display: flex;
    align-items: center;
    justif-content: center;
    flex-wrap: wrap;
    text-align: left;
    margin-bottom:5px;
    
`

export const BPRDailyAnalyticsTableRowContainer = styled.div`
    display:flex;
    flex-direction:column;
    justify-content:center;
`

export const BPRDailyAnalyticsTableRow = styled.div`
    display:flex;
    flex-direction:row;
    width:95%;
    border-radius: 4px ;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 3px 12px #58585829;
    margin-bottom:5px;
    overflow:hidden;
    zoom:0.7;
`

export const BPRDailyAnalyticsTableCell = styled.div`
    
    text-align:center;
    position:relative;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-direction:column;
    font-weight:500;
    font-size:11px;
    line-height:21px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
    &:before{
        content:'';
        position:absolute;
        right:0;
        height:100%;
        width:1px;
    }
`

export const BPRDailyAnalyticsTableNoChangeWrapper = styled.div`
    display:flex;
    flex-direction:column;
`

export const BPRDailyAnalyticsTableChangeIcon = styled.img`
    height:10px;
    width:10px;
`

export const BPRDailyAnalyticStatusBar = styled.div`
    display:flex;
    align-items:center;

`

export const BPRDailyAnalyticStatusBarSection = styled.div`
    width:100%;
    font-family:Roboto;
    font-weight:500;
    font-size:12px;  
    line-height:21px;
    letter-spacing: 0px;
    color: #FFFFFF;
    text-align:center;
`

export const BPRDailyAnalyticsTableCellHeader = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`

export const BPRDailyAnalyticsTableCellText = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`

export const ProcPlanningChildrenColor = styled.div`
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
`
const determineColor = (value: any) => {
    if (value === "Red") return 'Red';
    if (value === "Yellow") return 'Yellow';
    if (value === "Black") return 'Black';
    if (value === "Green") return 'Green';
};
export const ChildrenColorCellRenderer = styled.div<{ value: string }>`
        display: flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
        border-radius: 50%;
        margin-top: 14px;
        background-color: ${(props) => determineColor(props.value)};
`;



export const SCDynamicContainer = styled.div`


    & .ag-header-cell-text {
      font-size: 10px !important;
      font-weight: bold;
    }

    

      & > .ag-theme-alpine{
     
        --ag-borders: none !important;
          & .ag-cell {
            border: none;
            height: 100% !important;
            border-top: 0.1px solid #cecece !important;
          }
  
        }
}


  
   

    
`
