import styled from "styled-components";

export const AvailabiltyCellRendererWrapper = styled.div`
    height:100%;
    /* width:150px; */
    width: 100%;
    display:flex;
    padding-right: 40px;
    align-items:center;
    justify-content: right;
    gap: 10px;
`


export const AvailabiltyCellRenderer = styled.div<{ value: number , themeUi:string }>`
    position: relative;
    height: 100%;
    max-height: 15px;
    width: 45px;
    max-width: 45px;
    background: #DEDEDE 0% 0% no-repeat padding-box;
    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        max-width: 45px;
        width: ${(props) => props.value}%;
        //  background:  ${(props)=>props.themeUi==="REGALBLAZE"?"transparent linear-gradient(270deg, #FCA311  0%, #CB830E 100%) 0% 0% no-repeat padding-box" :"transparent linear-gradient(270deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box"};
        background: ${(props) =>props.themeUi === "REGALBLAZE"? "linear-gradient(90deg, #FCA311 0%, #CB830E 100%) 0% 0% no-repeat padding-box": "linear-gradient(90deg, #EB73B3 0%, #820F4C 100%) 0% 0% no-repeat padding-box"};
    }
`;
