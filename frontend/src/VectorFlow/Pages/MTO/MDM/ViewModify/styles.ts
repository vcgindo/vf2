import styled,{keyframes} from 'styled-components'

const fadeIn = keyframes`
  from {
   opacity:0;
  }

  to {
  opacity:1;
  }
`;

export const SCContainer = styled.div`
    margin-left:50px;
    padding-bottom:70px;
    height:90%;
`

export const SCFilterContainer = styled.div`
    margin:10px;
    display:flex;
    flex-direction:row;
`

export const SCFilterControls = styled.div`
    position:relative;
    display:flex;
    flex-direction:column;
    gap:10px;
    width:100%;
    border: 0.5px solid rgba(112,112,112,0.46);
    padding-top:19px;
    padding-bottom: 14px;
    padding-left:9px;
    padding-right:9px;
    border-radius: 6px;
`

export const SCFilterAddControls = styled.div`
    display:flex;
    flex-direction:column;
    gap:10px;
    padding-top:19px;
    padding-bottom: 14px;
    padding-left:9px;
    padding-right:9px;

`

export const SCFilterAddButtonWrapper = styled.div`
    height:56px;
    width:56px;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const SCFilterAddButton = styled.img`
    width: 30px;
    height: 30px;
    padding:5px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 3px 6px #00000029;
    border-radius:50%;
    cursor:pointer;
`

export const SCLegend = styled.legend`
    position:absolute;
    left:16px;
    top:-10px;
    background-color:white;
    font-family:Roboto;
    font-size:14px;
    line-height:20px;
    font-weight:300;
    padding:0 5px;
    color:#313131;
`

export const SCFilterSeperator = styled.div`
    width: 0px;
    outline: 1px solid #D0D0D0;
`

export const SCFilterButtonGroup = styled.div`
    display:flex;
    flex-direction:row;
    gap:12px;
    height:56px;
    padding-top:19px;
    padding-bottom: 14px;
    padding-left:9px;
    padding-right:9px;

`

export const TaskBarContainer = styled.div`
    background: #FFFFFF 0% 0% no-repeat padding-box;
    display:flex;
    flex-direction:row;
    justify-content:space-between;
    position:fixed;
    right:0;
    width:97%;
    bottom:0;
    height:95px;
    padding-top:23px;
    padding-bottom:22px;
    padding-left:38px;
    padding-right:30px;
    gap:30px;
    transition:0.3s ease 0s;

`

export const VFTaskBarButtonGroup = styled.div`
    display:flex;
    flex-direction:row;
    gap:20px;
`

export const UploadModalWrapper=styled.div`
display:flex;
justify-content:center;
padding:26px 0 40px 0; 

`

export const UploadModalSection=styled.div`
display: flex;
 flex-direction:column;
 flex:1;
 margin-right:32px;
 
`
export const UploadModalRadioWrapper = styled.div`
    width:100%;
    height:20px;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const UploadBorderContainer=styled.div`
border: 1.5px dashed #707070;
 width: 393px; 
 height: 212px;
 justify-content:center;
 align-items:center;
 display:flex;
`
export const UploadModalContent = styled.div`
display:flex;
align-items:center;
flex-direction:column;
background: #FFFFFF 0% 0% no-repeat padding-box;
height: 152px;
width:349px;
box-shadow: 5px 5px 30px #6E6B6B29;
border-radius: 6px;
`

export const TextContent=styled.div`
display:flex;
align-items:center;
justify-content:center;
flex:4;
flex-direction:column;
font-style: normal;
font-variant: normal;
font-weight: 600;
font-size: 12px;
line-height: 14px; 
font-family:Roboto;
`

export const InputWrapper = styled.div`
    display:flex;
    flex-direction:row;
    width:100%;
   
`

export const UploadModalInput=styled.input`

    width:100%;
    border:none;
    outline:none;
    color: #939393;
    opacity: 1;
    font-style: normal;
    font-variant: normal;
    font-weight: 300;
    font-size: 12px;
    line-height: 14px; 
    font-family:Roboto;
    padding-left:15px;
    &:focus{
        border:none;
        outline:none;
    }
    &:active{
        border:none;
        outline:none;
    }
    border-bottom-left-radius: 6px;
    border-bottom-right-radius: 6px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: -2px -2px 15px #A2A0A017;
`

export const UploadModalText=styled.div`
    font-style: normal;
    font-variant: normal;
    font-weight: 400;
    font-size: 16px;
    line-height: 19px;
    font-family: Roboto
`

export const UploadFileText=styled(UploadModalText)`
    width:100%;
    padding-left:16px;
    padding-bottom:5px;
    text-align:left;
    font-weight:600;
    font-size:7px;
    line-height:8px;
`

export const SeasonalityQuickFilterWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:row;
    justify-content:flex-end;
    margin-bottom:10px;
`

export const SeasonalityQuickFilterHeader = styled.p`
    display:flex;
    align-items:center;
    justify-content:center;
    font-style:normal;
    font-variant:normal;
    font-weight:700;
    font-size:20px;
    line-height:24px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #000000;
`

export const SeasonalityQuickFilter = styled.button<{stateColor:string,isActive:boolean}>`
    margin-left:20px;
    position:relative;
    background-color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    width: 90px;
    height: 40px;
    border: ${(props)=> props.isActive ? '1px solid transperent' : '1px solid #929292'};
    transition:0.3s ease-in-out;
    border-radius: 6px;
    
    color:${(props)=>props.isActive?'white':'#929292'};
    &:before{
        content:'';
        position:absolute;
        left:0;
        top:0;
        bottom:0;
        width:${(props)=>props.isActive?'100%':'8px'};
        background-color:${(props)=>props.stateColor};
        transition:0.3s ease-in-out;
    }
    overflow:hidden;
    cursor:pointer;
    
`

export const SeasonalityQuickFilterText = styled.p`
    font-style:normal;
    font-variant:normal;
    font-weight:300;
    font-size:12px;
    line-height:14px;
    font-family:Roboto;
    letter-spacing: 0px;
    color:inherit;
    z-index:100;
    transition:0.1s ease-out;
`

export const SubmitDataTextContainer = styled.div`
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

export const SubmitDataButtonWrapper = styled.div`
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

export const ConflictErrorToolTipWrapper = styled.div`
    position:fixed;
    min-width:140px;
    background-color:white;
    display:flex;
    flex-direction:column;
    padding:5px;
    z-index:10000;
    border-radius:4px;
    box-shadow: rgba(0, 0, 0, 0.16) 0px 1px 4px;
    animation:${fadeIn} 0.2s ease-in;
    transform:translateX(-50%);
   
`
export const ConflictErrorToolTipSection = styled.div`
   width:100%;
   margin-bottom:5px;
   border-bottom:solid 1px gray;  
   font-size:10px;
`

export const ConflictErrorText = styled.p`
    text-align:left;

`


export const ToolTipTriangle = styled.div`
    position:absolute;
    left:45%;
    height: 0px;
    border-style: solid;
    border-width: 0 7.5px 13.0px 7.5px;
    border-color: transparent transparent white transparent;
    // transform: rotate(0deg);
` 
export const MTOPoogiTableContainer = styled.div`
    display:flex;
    width: 100%;
    & > .ag-theme-alpine {
        width: 100% !important;
    }

`

export const PoogiSection = styled.div`
    display: flex;
    height: 100%;
    flex-direction: column;
`

export const PoogiAddButtonWrapper = styled.div`
    display: flex;
    gap: 40%;

`

interface ToggleProps {
    isActive: boolean;
    isDisabled?: boolean;
  }
  
export const ToggleContainer = styled.div<ToggleProps>`
    display: flex;
    align-items: center;
    width: 120px;
    padding: 5px;
    border-radius: 50px;
    cursor:  ${(props) => (props.isDisabled ? "not-allowed" : "pointer")};
    opacity:  ${(props) => (props.isDisabled ? 0.5 : 1)};
    border 3px solid;
    border-color: ${(props) => (props.isActive ? "#800040" : "#a0a0a0")};
    transition: background-color 0.3s ease;
  `;
  
export const ToggleCircle = styled.div<ToggleProps>`
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background-color: ${(props) => (props.isActive ? "#800040" : "#a0a0a0")};
    transform: ${(props) => (props.isActive ? "translateX(70px)" : "translateX(5px)")};
    transition: transform 0.3s ease, background-color 0.3s ease;
  `;
  
export const ToggleText = styled.span<ToggleProps>`
    margin-left: 8px;
    font-size: 14px;
    font-weight: 600;
    transform: ${(props) => (props.isActive ? "translateX(-25px)" : "translateX(0)")};
    transition: transform 0.3s ease, background-color 0.3s ease;
    color: ${(props) => (props.isActive ? "#800040" : "#808080")};
  `;