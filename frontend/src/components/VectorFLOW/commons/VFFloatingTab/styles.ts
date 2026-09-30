import styled from 'styled-components'
import * as globalStyles from '../../../../styles/global'


export const VFFloatingTabWrapper = styled.div`
    position:relative;
    height:52px;  //52px
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: -3px 3px 12px #8B8B8B41;
    border-radius: 30px;
    display:inline-flex;
    align-items:center;
    padding-right:10px;
    // min-width:270px

   
`

export const VFFloatingTabButton = styled.button<{ isActive: boolean }>`
    height: 36px;
    padding:0 10px;
    font-weight:500;
    font-size:14px;
    line-height:19px;
    font-family:Roboto;
    letter-spacing: 0px;
    background-color:transparent ;
    border-radius: 30px;
    color:${(props) => props.isActive ? "white" : '#2E2E2E'};
    margin-left:10px;
    transition:color 0.3s ease;
    z-index:10;
    

     ${(props) => !props.isActive && `
        &:hover {
            background-color:#F5F5F5;
            cursor:pointer;
        }
    `}
`
export const VFFloatingTabButtonActiveShadow = styled.button<{ theme: string }>`
    position:absolute;
    height: 36px;
    background: ${(props) => props.theme === 'REGALBLAZE' ?
        globalStyles.chooseThemeColor[props.theme].colorButton
        : globalStyles.chooseThemeColor[props.theme].colorButton };
    color:white;
    border-radius: 30px;
    box-shadow: -3px 3px 12px #8B8B8B41;
    transition:left 0.3s ;
    z-index:9;
`

