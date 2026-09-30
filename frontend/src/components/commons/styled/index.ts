import styled,{keyframes} from 'styled-components'

import * as globalStyles from "../../../styles/global";

export const skeletonFade = keyframes`

    50%{
        opacity:0.5;
    }
`

export const Input = styled.input<{themeUi:string}>`
    border:none;
    outline:none;
    outline:solid 2px transparent;
    border-radius: 6px;
    background: #F7F7F7 0% 0% no-repeat padding-box;
    opacity: 1;
    padding: 0 15px;
    height:39px;
    font-size:12px;
    &:disabled{
        opacity:0.7;
        cursor:not-allowed;
    }
    &:active, &:focus{
        outline-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi]?.color4} ;
        /* background-color:white; */
    }
    transition:0.2s ease-in-out;
`
export const TextArea = styled.textarea<{themeUi:string}>`
     border:none;
    outline:none;
    outline:solid 2px transparent;
    border-radius: 6px;
    background: #F7F7F7 0% 0% no-repeat padding-box;
    opacity: 1;
    width:100%;
    max-width:100%;
    min-width:100%;
    padding: 5px 15px;
    font-family:inherit;
    font-size:12px;
    min-height:100px;
    transition:0.3s ease-in;
    /* box-shadow: rgba(0, 0, 0, 0.2) 0px 0px 0px 1px; */
    &:active, &:focus{
        outline-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi]?.color4};
    }   
`

export const Skeleton = styled.div`
    background-color:#e2e2e2;
    animation:${skeletonFade} 3s ease-in-out infinite;
    border-radius:4px;
`

export const Button = styled.button<{themeUi:string}>`
    height:30px;
    padding:4px 10px;
    opacity:0.8;
    border-radius:4px;
    display:flex;
    align-items:center;
    justify-content:center;
    box-shadow: rgba(0, 0, 0, 0.2) 0px 0px 0px 1px;
    transition:0.2s ease-in-out;
    outline:solid 1px transparent;
    &:hover{
        opacity:1;
    }
    &:disabled{
        opacity:0.5 !important;
        cursor:not-allowed;
    }
    &:active,&:focus{
        opacity:0.9;
    }
   
`

export const PrimaryButton = styled(Button)`
     background-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi]?.color5};
     color:white;
     &:focus{
        outline:solid 1px #dee2e6;
    }
`
export const SecondaryButton = styled(Button)`
    box-shadow:none;
    /* &:hover{
        background-color:transparent;
    } */
`