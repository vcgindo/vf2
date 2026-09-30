import styled from "styled-components";

import * as globalStyles from '../../../../styles/global'

export const VFCapsuleWrapper = styled.div<{themeUi:string}>`
    display:inline-flex;
    align-items:center;
    width:100%;
    height: 25px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: -3px 3px 12px #8B8B8B41;
    border: 0.4000000059604645px solid ${(props)=>globalStyles.chooseThemeColor[props.themeUi]?.color4};
    border-radius: 21px;
    opacity: 1;
    overflow:hidden;

`

export const VFCapsuleButton = styled.button<{isActive:boolean,themeUi:string}>`
    width:100%;
    height: 25px;
    font-weight:300;
    font-family:Roboto;
    font-size:10px;
    display:block;
    text-wrap: nowrap;
    color:${(props)=>props.isActive?'white':'#8E8E8E'};
    background: ${(props)=>props.isActive?globalStyles.chooseThemeColor[props.themeUi]?.color4:'#FFFFFF 0% 0% no-repeat padding-box'};
    opacity: 1;

`