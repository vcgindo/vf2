import styled from 'styled-components';

export const InfoWrapper=styled.div`
height:auto;
width:100%;
border: 1px dashed #BC3D81;
border-radius: 6px;
// box-shadow: -5px 5px 15px #0000000F;
`
export const IconTextContainer=styled.div <{ gap: string }>`
margin:13px 10px 12px 20px;
display:flex;
align-items:center;
gap: ${(props) => props.gap};
`

export const InfoIcon=styled.div`
height:auto;
width:20px;
`
export const Infotext=styled.div`
margin-left:10px;
font-style:normal;
font-variant:normal;
font-weight:400;
font-size:14px;
line-height:20px;
font-family:Roboto;
`