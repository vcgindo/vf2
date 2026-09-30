import styled from "styled-components";

export const DBMLayout = styled.div`
    // margin-top:20px;
    margin-bottom:40px;
`

export const DBMGraphCellRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    justify-content:center;
    align-items:center;
    cursor:pointer;
`

export const DBMSleepCellRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    justify-content:center;
    align-items:center;
    cursor:pointer;
`
export const DBMTickCellRendererWrapper = styled.div`
    width:201px;
    height:49px;
    display:flex;
    justify-content:center;
    align-items:center;
    cursor:pointer;
    // color:"#820F4C";
`

export const DBMApplyNormButton = styled.div`
    display:flex;
    align-items:center;
    max-width: 401px;
    height: 49px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 12px #86868629;
    border-radius: 6px;
    opacity: 1;
    padding: 13px;
    text-align: left;
    font-size:16px;
    font-weight:500;
    line-height:19px;
    letter-spacing: 0px;
    color: #000000;
`



export const SuggestionCategoryIcon = styled.img`
    height:12px;
    width:12px;
`

export const ConfirmationDataTextContainer = styled.div`
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:14px;
    line-height:12px;
    font-family:Roboto;
    color: #000000;
    opacity: 1;
    dispay:flex;
    text-align:center;
    justify-content:center;
    margin-top:26px;  //42
`
 
export const ConfirmationDataButtonWrapper = styled.div`
    // margin-bottom:59px; // 87
    // margin-left:100px;  //192
    // margin-right:100px;  //189
    margin-left:-140px;
    margin-right:-140px;
    padding:15px 20px 0px 10px;
    display:flex;
    justify-content:flex-end;
    border-top:dashed 1px gray;
    flex-direction:row;
    gap:28px;
    transform:scale(0.8);
`