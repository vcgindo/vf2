import styled from "styled-components";


export const VFErrorFallBackWrapper = styled.div`
    height:100vh;
    width:100vw;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const VFErrorFallBackContainer = styled.div`
    height:100%;
    width:100%;
    // width:500px;
    display:flex;
    flex-direction:column;
    justify-content:center;
`

export const VFErrorFallBackHeader = styled.h1`
    font-family:Roboto;
    font-size:25px;
    line-height:27px;
    font-weight:400;
    text-align:center;
`
export const VFErrorFallBackTextContent = styled.div`
    font-family:Roboto;
    font-size:15px;
    line-height:30px;
    font-weight:300;
    text-align:center;
    margin-bottom:20px;
`

export const VFErrorFallBackButtonGroup = styled.div`
    width:100%;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:center;
`

export const VFErrorFallBackButton = styled.button<{themeUi:string}>`
    height:30px;
    width:130px;
    color:white;
    border-radius: 4px;
    background:${(props)=>props.themeUi==="REGALBLAZE"?"transparent linear-gradient(76deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box":"transparent linear-gradient(76deg, #820F4C 0%, #BC3D81 100%) 0% 0% no-repeat padding-box"};
    box-shadow: -5px 4px 10px #919191B3;
`
export const VFErrorFallBackButtonGhost = styled.button`
    height:30px;
    width:130px;
    color:black;
    border-radius: 4px;
    background-color:transparent;
`