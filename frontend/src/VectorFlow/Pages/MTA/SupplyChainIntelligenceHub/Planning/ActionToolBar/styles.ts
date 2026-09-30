import styled from "styled-components";
import * as gridSystem from "../../../../../../styles/gridSystem";

export const SCTaskBarContainer = styled.div`
    //  margin-top:5px;
    padding-left:10px;
    display:flex;
    align-items:center;
   // margin-bottom:20px;
    margin-left:20px;
    justify-content:space-between; //changed

    @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
        .size.desktop}) {
        zoom:0.7;
    }
  
    @media (min-width: ${gridSystem.size.desktop}) {
      zoom:1;
    }
`
export const SCGoBackContainer = styled.div`
    display:flex;
    align-items:center;
    gap:10px;
    cursor:pointer;
    text-wrap:nowrap;
    width:max-content;
`

export const SCGoBackText = styled.div`
    font-weight:500;
    font-size:20px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
`

export const SCViewContainer = styled.div`
    display:flex;
    flex-direction:column;
    align-items:center;
    cursor:pointer;
    overflow:hidden;

`

export const SCViewContainerWithBg = styled.div`
    display:flex;
    flex-direction:column;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: -5px 4px 10px #8584843F;
    border-radius:5px;
    padding:5px;
    justify-content:center;
    align-items:center;
    width:82px;
    height:58px; 
    font-size:13px;
    min-width:95px;
    cursor:pointer;
`
export const SCViewBackground = styled.div`
    display:flex;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: -5px 4px 10px #8584843F;
    border-radius:5px;
    padding:10px;
    min-width:170px;
    font-size:13px;
    // height:58px;    
`
export const SCVerticalDivider = styled.div`
    width:0.5px;
    background-color:#C6C6C6; //#6C696A
    height:40px;
    margin-right:8px;
    margin-left:8px;
    align-items:center;
`
export const SCViewImage = styled.img`
    width:38px;
    height:20px;
    margin-bottom:7px;
    cursor:pointer;
`

export const SCCustomActionsContainer = styled.div`
    display:flex;
    //gap:22px;
    gap:10px;
    align-items:center;
    justify-content: flex-end;
    //width:100%
`
export const SCTaskFilterContainer = styled.div`
    display:flex;
    justify-content:space-between;
    gap:30px;
    max-width:40%;
    align-items:center;
`
export const ReleaseText = styled.div`
//display: flex;
  height: 100%;
  width: 15000px;
  background-color: #FFFFFF;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Elevation */
  padding: 10px;
  font-size: 2.2em; /* Increased font size */
`

export const LastRunDateHeader = styled.div`
    font-size:20px;
    font-weight:500;
`