import styled from 'styled-components'

export const VFFilterWrapper = styled.div`
    display:flex;
    flex-direction:row;
    align-items:center;
    padding:10px 24px;
    width:100%;
    height: 56px;
    background: #E8E8E8 0% 0% no-repeat padding-box;
    border-radius: 6px;
`


export const VFFilterSeperator = styled.div`
    width: 0px;
    height: 40px;
    outline: 1px solid #9F9F9F;
    margin:0 35px;
`

export const VFFilterInputField = styled.input`
    width: 100%;
    height: 37px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    border:none;
    outline:none;
    color: #313131;
    font-size:13px:
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-family:Roboto;
    letter-spacing: 0px;
    line-height:15px;
    padding:0 16px;
    border-radius: 6px;
`

export const VFFilterDustbinIcon = styled.img`
    width: 30px;
    height: 30px;
    cursor:pointer;
`