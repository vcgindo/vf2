import styled from "styled-components";


export const Container = styled.div`
    display:flex;
    flex-direction:column;
`

export const SCButtonContainer = styled.div`
    display:flex;
    gap:25px;
    margin-top:72px;
`

export const SCCardContainer = styled.div`
    display:flex;
    flex-direction:row;
    gap:30px;
    margin-top:46px;
    overflow-x:overlay;
    padding-bottom:2px;

    &::-webkit-scrollbar{
        width: 7px;
        height:8px;       
    }
    
    &::-webkit-scrollbar-track{
        border-radius: 30px;
        opacity: 1;
    }
    
    &::-webkit-scrollbar-thumb{
        width: 7px;
    /* UI Properties */
    background: #D1D1D1 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 9px #41414129;
    border-radius: 30px;
    opacity: 1;
    }
`

export const SCLoaderContainer = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    height:85%;
    // margin-top:25%;
`

export const PanelGridWrapper = styled.div`
    width:100%;
    display:flex;
    flex-direction:column;
`

export const PanelGrid = styled.div`
    width:100%;
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
    gap:111px;
    margin-bottom:5rem;
`

export const QuickFilterHeader = styled.h1`
    width:205px;
    text-align: left;
    font-size:normal;
    font-variant:normal;
    font-weight:700;
    font-size:20px;
    line-height:30px;
    font-family:Verdana;
    letter-spacing: 0px;
    color: #000000;
`