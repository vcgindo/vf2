import styled from "styled-components";

export const SaveBtnWrapper = styled.div`
    height:50px;
    width:100%;
    display:flex;
    justify-content:flex-end;
    // background-color:#23232f;
    align-items:center;
    padding:25px;
    margin-top:30px;
`

export const SaveBtn=styled.div<{ theme: string }>`
    display:flex;
    height:40px;
    width:169px;
    align-items:center;
    justify-content:center;
    color:${(props)=>props.theme ==='REGALBLAZE'? '#CB830E' :'#BC3D81'};
    background-color:#fff;
    border:1px solid ${(props)=>props.theme ==='REGALBLAZE'? '#CB830E' :'#BC3D81'};
    border-radius:4px;
    font-size:14px;
    font-family: 'Roboto', sans-serif;
    font-weight:400;
    curser:pointer;
`

export const BPRDailyAnalyticsWrapper=styled.div`
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

export const BPRDailyAnalyticsTableCellHeader = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:500;
    font-size:16px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #313131;
`

export const Wrapper = styled.div`
  width: 100%;
  height: 80%;
  display: flex;
  flex-direction: column;
//   margin: 20px 0 0;
  padding: 20px 0px 20px 20px;

  & .ag-header-cell-text {
    font-size: 13px;
  }

  & > .ag-theme-alpine{
    flex: 1;
    margin: 0 !important;
    }
& div[data-testid="vf_pagination"]{
  margin: 0 !important;
  padding: 0;
}
 
`;
