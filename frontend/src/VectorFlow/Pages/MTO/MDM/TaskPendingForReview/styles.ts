import styled from "styled-components";

import * as globalStyles from "../../../../../styles/global";

export const TaskPendingWrapper = styled.div`
    width:100%;
    height:95%;
    margin-bottom:100px;
    padding-left:50px;
    padding-top:20px;
    ::ng-deep .ag-cell:focus{
        outline: none;
      }
`

export const ActionRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    align-items:center;
    justify-content:space-around;
`

export const ActionButtonWrapper = styled.img`
    cursor:pointer;
`

export const ActionHeaderWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    flex-direction:row;
    justify-content:space-around;
`

export const ActionHeaderContent = styled.div`
    font-size:16px;
    display:flex;
    padding:5px;
    margin-top: 5px;
    margin-bottom:5px;
`

export const LinkWrapper = styled.div`
    width:100%;
    height:100%;
`
export const RadioContainer = styled.div`
    // display:flex;
    justify-content: space-between;
    align-items: center; 
    // gap:20px;
`
export const RadioButtonGroup = styled.div<{themeUi:string}>`
    font-style: normal;
    font-variant: normal;
    font-weight: 400;
    font-size: 18px;
    line-height: 21px; 
    font-family:Roboto;
    margin-bottom:20px;
    accent-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi].color5};
    display:flex;
    gap:8px;
    margin-top:20px;
    align-items:center;
`
export const SubmitButtonWrapper = styled.div`
    display: flex;
    justify-content: flex-end;
    margin-left:-73px;
    margin-right:-73px;
    border-top:dashed 1px gray;
    padding:10px 20px 0px 10px;
`
export const DeleteFileModalText=styled.div`
text-align: left;
margin-top:40px;
margin-bottom:40px;
font-style: normal;
font-variant: normal;
font-weight: 400;
font-size: 16px;
line-height: 19px; 
font-family:Roboto;
letter-spacing: 0px;
color: #000000;
margin-right:221px;
margin-left:162px;
`

export const ButtonWrapper=styled.div`
margin-bottom:100px;
display:flex;
flex-direction:row;
gap:35px;
// margin-right:210px;
// margin-left:164px;
`

export const ApproveModalText=styled.div`
font-style: normal;
font-variant: normal;
font-weight: 400;
font-size: 16px;
line-height: 19px; 
font-family:Roboto;
margin-right:186px;
margin-left:161px;
margin-bottom:30px;
margin-top:37px;
text-align:center;
`

export const ApproveButtonWrapper=styled.div`
align-items:center;
margin-bottom:85px;
margin-right:221px;
margin-left:221px;
align-items:center;
`

export const TaskPendingActionHeaderButton = styled.button<{ themeUi: string}>`
    background-color:${(props:any)=>globalStyles.chooseThemeColor[props.themeUi]?.color5};
    height:10px;
    width:78px;
    border-radius: 6px;
    display:flex;
    align-items:center;
    justify-content:center;
  font-size:11px;
  font-family:'Roboto';
  letter-spacing:0px;
  font-weight:300;
  color: ${globalStyles.white};
  padding: 15px 7px;
  border: none;
  zoom:0.9;
`

export const ButtonSeperator = styled.div`
      width:1.5px;
      height:30px;
      background-color:#898989;
      margin:0px 10px;
`