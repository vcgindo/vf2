import styled from "styled-components";
import * as globalStyles from "../../../../../styles/global";

export const BPRLayout = styled.div`
   margin-top:0px;
 //   margin-bottom:40px;
`


export const SaveBtnWrapper = styled.div`
    height:40px;
    width:100%;
    display:flex;
    justify-content:flex-end;
    // background-color:#23232f;
    align-items:center;
`

export const SaveBtn= styled.button<{themeUi: string}>`
    display:flex;
    height:40px;
    width:169px;
    align-items:center;
    justify-content:center;
    color:#B93B7E;
    background-color:#fff;
    border:1px solid #B93B7E;
    border-radius:4px;
    font-size:14px;
    font-family: 'Roboto', sans-serif;
    font-weight:400;
    curser:pointer;
`



export const LastRunDate = styled.div`
    width:100%;
    display:flex;
    justify-content:center;
    align-items:center;
    padding-top:1px;
    padding-bottom:1px;
`

export const LastRunDateHeader = styled.div`
    font-size:14px;
    font-weight:500;
`

export const BPRTaskBar  = styled.div`
    position:fixed;
    width:97%;
    right:0;
    top:13vh;
    height:70px;
    background-color:white;
    display:flex;
    flex-direction:row;
    justify-content:flex-end;
    align-items:center;
    gap:20px;
    padding:16px;
    z-index:2;
    transition:0.3s ease 0s;
`
export const BPRViewTableWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:column;
    margin-top:10px;
    height:100%;
`

export const BPRViewTablePrefixWrapper = styled.div`
    // width:100%;
    display:flex;
    zoom:0.8;
`

export const BPRViewTablePrefix = styled.div`
   min-width:270px;
//    margin-left:7px;
`

export const BPRViewTablePrefixText = styled.div`
    // font: normal normal normal 16px/21px Roboto Medium;
    font-size:16px;
    font-weight:400;
    font-family:Roboto;
    color: #FFFFFF;
`

export const BPRViewTablePrefixIcon = styled.img`
    // height:33px;
    // width:33px;
    margin-left:10px;
`

export const BPRViewTableGrid = styled.div`
    display:flex;
    flex-direction:column;
    border: 1px solid #CCCCCC;
    width:100%;
    min-height:200px;
    max-height:100%;
    // max-height:205px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #9B9B9B29;
    border-radius:8px;
    overflow-y:scroll;
    // scrollbar-gutter: stable both-edges;
    &::-webkit-scrollbar{
        width: 4px;      
        height:4px; 
    }
    &::-webkit-scrollbar-track{
        //border-radius: 30px;
        opacity: 1;
    }
    &::-webkit-scrollbar-thumb{
        width: 7px;
    /* UI Properties */
    background: #313131 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 9px #41414129;
    //border-radius: 30px;
    opacity: 1;
    }
`

export const BPRViewTableHeaderContainer = styled.div`
    display:flex;
    flex-direction:row;
    position:sticky;
    top:0;
    background-color: white;
    z-index:1;
   
`

export const BPRViewTableHeader = styled.div`
    position:relative;
    width:100%;
   overflow:hidden;
    min-width:120px;
    height:45px;
    padding:10px;
    padding-top:15px;
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-size:13px;
    line-height:13px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    // border-bottom: 1px solid #919191B3;
    box-shadow: 0px 6px 12px #9B9B9B29;
    text-align:center;
    &::after{
        content:'';
        position:absolute;
        right:1px;
        top:4px;
        bottom:4px;
        background-color:#898585;
        width:0.5px;
    }
    &:last-child::after {
        display: none;
    }
    white-space:nowrap;
    text-overflow:ellipsis;
`

export const BPRViewTableHeaderFilterIcon = styled.img`
    position:absolute;
    right:10px;
    top:13px;
    height:17px;
    width:17px;
    cursor:pointer;
`
export const BPRViewTableHeaderFilterAlert = styled.div<{themeUi:string}>`
    position:absolute;
    right:10px;
    top:14px;
    background-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi].color4};
    height:6px;
    width:6px;
    border-radius:50%;
`

export const BPRViewTableColumnFilterWrapper = styled.div`
    position:fixed;
    z-index:100;
    // transform:translateX(-150%);
`

export const BPRViewTableColumnFilterContainer = styled.div`
    display:flex;
    flex-direction:column;
    padding:5px;
    width:100px;
    box-shadow: rgba(0, 0, 0, 0.02) 0px 1px 3px 0px, rgba(27, 31, 35, 0.15) 0px 0px 0px 1px;
    background-color:white;
`

export const BPRViewTableColumnFilterInput = styled.input`
    height:15px;
    font-size:10px;
    &:focus{
        outline:none;
    };
`

export const BPRViewTableColumnFilterSelect = styled.select`
    height:15px;
    font-size:10px;
    &:focus{
        outline:none;
    };
    
    margin-bottom:5px;
    accent-color:red;
`
export const BPRViewTableColumnFilterSelectOption = styled.option`
accent-color:inherit;
`

export const BPRViewTableColumnFilterButton = styled.button`

`


export const BPRViewTableRowContainer = styled.div`
position:relative;
    width:100%;
    display:flex;
    flex-direction:column;
        // max-height:250px;
    // margin-top:20px;
    
`

export const BPRViewTableRow = styled.div`
    width:100%;
    height:40px;
    display:flex;
    &:nth-child(even) {
        background-color: #8D8D8D29; /* You can use a specific shade of yellow if needed */
    }

`

export const BPRViewTableRowCell = styled.span`
    width:100%;
   overflow:hidden;
    min-width:120px;
    height:50px;
    padding:6px;
    text-align:center;
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:14px;
    line-height:24px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    white-space:nowrap;
    text-overflow:ellipsis;

`

export const ReadMoreToolTip = styled.div`
    position:absolute;
    top:0;
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

export const BPRTagsCellRendererWrapper = styled.div<{theme:string}>`
    display:block;
    padding:4px 5px;
    // width: 55px;
    max-width:90px;
    height: 25px;
    background: ${(props) => props.theme === "REGALBLAZE" ? "#FCA311" : '#B93B7E'}  0% 0% no-repeat padding-box;
    color: #FFFFFF;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 2px;
    font-style:normal;
    font-variant:normal;
    font-weight:medium;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
    overflow:hidden;

`


export const BPRRemarksCellRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const BPRSubmitRemarkInput = styled.div`
    height:20px;
    width:100%;
    background-color:white;
    border:solid 1px black;
    display:flex;
    align-items:center;
    overflow:hidden;
`

export const BPRRemarkToolTipTextArea = styled.textarea`
     min-width:240px;
    max-width:240px;
    min-height:100px;
    max-height:100px;
`

export const BPRRemarkToolTipButtonGroup = styled.div`
    display:flex;
    justify-content:flex-end;
    width:100%;
    margin-top:5px;
`

export const  BPRRemarkToolTipButton = styled.button`
    height:25px;
    border-radius:4px;
    padding:2px 7px;
    background-color:white;
    font-size:11px;
    box-shadow: rgba(9, 30, 66, 0.25) 0px 1px 1px, rgba(9, 30, 66, 0.13) 0px 0px 1px 1px;
`

export const BPRRemarksToolTipWrapper = styled.div`
    position:fixed;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    padding:10px;
    z-index:100000;
    transition:0.2s ease-in-out;
`

export const BPRRemarksToolTipContent = styled.div`
    height:100%;
    width:100%;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #77777729;
    border: 0.4000000059604645px solid #707070;
    border-radius: 2px;
    padding:10px;
    
`

export const BPRRemarksToolTipContentHeaderContainer = styled.div`
    width:100%;
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:5px;
`
export const BPRRemarkHistoryCloseIcon = styled.img`
    height:10px;
    width:10px;
    cursor:pointer;
`

export const BPRRemarksToolTipContentHeader = styled.div`
    font-weight:500;
    font-size:11px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #464646;
`
export const BPRRemarksToolTipContentColumnContainer = styled.div`
    border-top:solid gray 1px;
    border-bottom:solid gray 1px;
    display:flex;
`

export const BPRRemarksToolTipContentColumn = styled.div`
    margin-right:10px;
    text-align:left;
    font-weight:300;
    font-size:10px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #464646;
`

export const BPRRemarksToolTipContentRowContainer = styled.div`
    display:flex;
    flex-direction:column;
    height:270px;
   
`

export const BPRRemarksToolTipContentRow = styled.div`
    display:flex;
    flex-direction:row;
    gap:10px;
    border-bottom:dotted gray 3px;
    &:last-child {
        border-bottom:none;
    }

`

export const BPRRemarksToolTipContentRowCell = styled.p`
    width:100%;
    white-space: normal;
  word-wrap: break-word;
  overflow-wrap: break-word; 
  text-align:left;
  font-weight:400;
    font-size:10px;
    font-family:Roboto;
    color: #464646;
  display:flex;
  flex-direction:column;
  
`

export const BPRColorCellRendererIcon = styled.img`
    height:15px;
    width:15px;
    cursor:pointer;
`

export const BPRRemarksToolTipContentRowNameCellSection = styled.div`
    margin-bottom:5px;
    color:gray;
`

export const BPRRemarksToolTipContentRowDataCellSection = styled.div`
    margin-bottom:5px;
`
export const BPRViewTableToolTip = styled.div`
    position:fixed;
    color:white;
    background: #4E4E4E 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #38383829;
    border-radius:4px;
    font-weight:500;
    font-size:10px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #FFFFFF;
    max-width:200px;
    padding:5px;
    z-index:10000;
    &::after {
        content: '';
        position: absolute;
        bottom: 0%;
        left: 50%;
        transform: translate(-50%, 100%);
        border-width: 6px;
        border-style: solid;
        border-color: #4E4E4E transparent transparent transparent; /* Updated to black */
    }
`

export const BPRGraphCellRendererWrapper = styled.img`
    height:15px;
    width:15px;
    cursor:pointer;
`

export const TableHeader = styled.p`
    text-align: left;
    font-weight:500;
    font-size:20px;
    line-height:26px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
    margin-left:40px;
    padding:10px;
`

export const BPRViewTableRequestCellRendererWrapper = styled.div`
    width:100%;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    height:30px;
    min-width:120px;
    // z-index:1;
`

export const BPRViewTableRequestCellRendererImg = styled.img`
    height:20px;
    width:20px;
`

export const BPRViewTableRequestCellRendererText = styled.p`
    height:20px;
    width:20px;
    font-size:12px;
    font-weight:500;
    font-family:Roboto;
    margin-left:5px;
`

export const RequestExpeditingModalContent = styled.div`
    display:flex;
    flex-direction:column;
    width:100%;
`

export const RequestExpeditingModalInput = styled.textarea`
    max-height:150px;
    width:600px;
    min-height:150px;
    max-width:600px;
    min-width:600px;
    font-weight:300;
    font-size:18px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #7E7E7E;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    border:none;
    outline:none;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 5px 0px, rgba(0, 0, 0, 0.1) 0px 0px 1px 0px;
    border-radius: 6px;
    margin:10px;
`

export const RequestExpeditingModalButtonGroup = styled.div`
    display:flex;
    justify-content:flex-end;
    align-items:center;
    gap:10px;
    margin-top:10px;
    padding:10px;
    border-top:2px dashed #A0A0A0;
`

export const BPRViewTableNoDataContainer = styled.div`
    position:absolute;
    left:0;
    right:0;
    top:45px;
    bottom:0;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
`

export const BPRViewTableNoDataHeader = styled.p`
    font-weight:500;
    font-size:16px;
    font-family:Roboto;
`

export const BPRViewTableNoDataText = styled.p`
    font-weight:300;
    font-size:16px;
    font-family:Roboto;
`

export const AgeingCell = styled.div`
    height:100%;
    width:100%;
    display:flex;
    justify-content:center;
`

export const AgeingText = styled.div`
    font-weight:500;
    font-size:14px;
    font-family:Roboto;
`

export const AgeingIcon = styled.img`
    margin-left:10px;
    height:15px;
    width:15px;
    margin-top:4px;
`

export const AgeingToolTipWrapper = styled.div`
    display:flex;
    flex-direction:column;
    width:200px;
    padding:0px 5px;
`

export const AgeingToolTipSection = styled.div`
    display:flex;
    width:100%;
    justify-content:space-between;
`

export const AgeingToolTipText = styled.div`
    font-weight:500;
    font-size:12px;
    font-family:Roboto;
    color: #FFFFFF;
`

export const WhereAboutsCell = styled.div`
    display:flex;
    flex-direction:column;
    padding:0px 10px;
`

export const WhereAboutsCellSection = styled.div`
    display:flex;
    
`

export const WhereAboutsCellSectionHeader = styled.div`
    font-weight:300;
    font-size:12px;
    font-family:Roboto;
    line-height:15px;
`
export const WhereAboutsCellSectionValue = styled.div`
    font-weight:500;
    font-size:12px;
    font-family:Roboto;
    margin:0px 5px;
    line-height:15px;
`

export const WhereAboutsMoreInfo = styled.div`
    font-weight:400;
    font-size:14px;
    font-family:Roboto;
    letter-spacing: 0px;
    margin-left:5px;
    text-decoration: underline;
    cursor:default;
    line-height:15px;
    
`

export const BPRViewTableHeaderTab = styled.div<{
    status: string
    zIndex: number
    marLeft: true | false
    themeUi: string
  }>`
    color: ${(props) => (props.status==='active' ? '#FFFFFF' : '')};
    opacity: 1;
    min-height: 60px;
    text-align: center;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    position: relative;
    z-index: ${(props) => props.zIndex};
    margin-left: ${(props) => (props.marLeft ? '-1.5em' : '0')};
    padding-left: ${(props) => (props.marLeft ? '1.5em' : '0')};
  
    cursor: pointer;
    
    // pointer-events:${(props)=>props.status === 'completed' ? 'none' : 'all'};
  
    ::before {
      border: 0.5px solid #cccccc;
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
      z-index: -1;
      border-bottom: none;
      border-top-left-radius: 6px;
      border-top-right-radius: 6px;
      background: ${(props) =>
        props.themeUi === "REGALBLAZE"
          ? globalStyles.chooseThemeColor[props.themeUi]?.color5
          : "transparent linear-gradient(74deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box"};
        no-repeat padding-box;
      box-shadow: 0px 5px 25px #9d9d9d29;
      transform: scale(1.2, 1.3) perspective(0.5em) rotateX(2.5deg);
      transform-origin: bottom left;
    }
  `
  export const BPRViewTableAvailabilityCellRenderer = styled.div`
    background-color:#F8F8F8;
    border:solid 1px #AFAFAF;
    height:40px;
    width:80px;
    display:flex;
    align-items:center;
    justify-content:center;
    margin-left:50px;
    border-radius:4px;
  `
  export const Wrapper = styled.div`
  width: 100%;
  height: 90%;
//   margin: 20px 0 0;
//   padding: 20px 0px 20px 20px;

  & .ag-header-cell-text {
    font-size: 13px;
  }

  & > .ag-theme-alpine{
    margin: 0 !important;
  }
    
  & div[data-testid="vf_pagination"]{
  margin: 0 !important;
  padding: 0;
  }
 
`;