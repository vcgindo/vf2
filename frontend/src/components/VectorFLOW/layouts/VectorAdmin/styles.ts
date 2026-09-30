import styled from 'styled-components'

import * as globalStyles from "../../../../styles/global";

export const LoginWrapper = styled.div`
    width:100%;
    height:100vh;
    background-color:#e8e6e6;
    display:flex;
    align-items:center;
    justify-content:center;
`

export const LoginForm = styled.form`
    max-width:100%;
    width:400px;
    box-shadow: rgba(17, 17, 26, 0.1) 0px 0px 16px;
    padding:15px 10px;
    display:flex;
    flex-direction:column;
    background-color:white;
    gap:10px;
    border-radius:10px;
`

export const FormLogo = styled.img`
    background-color:white;
    height:60px;
`

export const FormSection = styled.div`
    display:flex;
    justify-content:center;
    margin-top:10px;
`

export const InputArea = styled.div<{themeUi:string}>`
    display:flex;
    width:100%;
    align-items:center;
    outline:solid 2px transparent;
    border-radius: 16px;
    box-shadow: rgba(0, 0, 0, 0.02) 0px 1px 3px 0px, rgba(27, 31, 35, 0.15) 0px 0px 0px 1px;
    background: #F7F7F7 0% 0% no-repeat padding-box;
    opacity: 1;
    padding: 0 15px;
    transition:0.3s ease;
    &:focus-within{
        outline-color:${(props)=>globalStyles.chooseThemeColor[props.themeUi]?.color4};
    }
`

export const PasswordInput = styled.input`
    border:none;
    width:100%;
    outline:none;
    outline:solid 2px transparent;
    border-radius: 6px;
    background: #F7F7F7 0% 0% no-repeat padding-box;
    opacity: 1;
    padding: 0 15px;
    height:39px;
    &:disabled{
        opacity:0.7;
        cursor:not-allowed;
    }
    /* cursor:pointer; */
    transition:0.2s ease-in-out;
`



//Admin Components



export const AdminLayoutWrapper = styled.div`
    padding:20px;
    height:100vh;
    background-color:rgb(10,10,10,0.04);
`

export const AdminLayoutContent = styled.div`
    background-color:white;
    height:100%;
    width:100%;
    border-radius:16px;
    box-shadow: rgba(9, 30, 66, 0.25) 0px 4px 8px -2px, rgba(9, 30, 66, 0.08) 0px 0px 0px 1px;
    /* box-shadow: rgba(0, 0, 0, 0.16) 0px 3px 6px, rgba(0, 0, 0, 0.23) 0px 3px 6px; */
`

export const ToolsWrapper = styled.div`
    display:flex;
    justify-content:flex-start;
    padding:10px;
`

export const ToolCard = styled.div`
    padding:20px;
    border-radius:7px;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 0px 5px 0px, rgba(0, 0, 0, 0.1) 0px 0px 1px 0px;
    background-color:rgba(1,1,1,0.06);
`