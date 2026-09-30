import styled,{keyframes} from 'styled-components'

const fadeIn = keyframes`
    from{
        opacity:0.7;
        transform:translateY(10px);
        /* box-shadow: rgba(0, 0, 0, 0.1) 0px 5px 15px 20000px; */
    }
    to{
        opacity:1;
    }
`

export const SCToolTipWrapper = styled.div<{themeUi:string}>`
    position:fixed;
    padding:1px 5px;
    border: 1px solid #BC3D81;
    background-color:rgba(255,255,255);
    color:#820F4C;
    border-radius:4px;
    width:170px;
    max-height:280px;
    z-index:100000;
    /* box-shadow: #BC3D81 0px 5px 15px; */
    animation:${fadeIn} 0.3s ease;
`

export const SCContainer = styled.div<{themeUi:string}>`
    height:25px;
    border-radius: 5px;
    background: ${(props)=>props.themeUi==="REGALBLAZE"?"#FFEED3  0% 0% no-repeat padding-box": "#bc3d811a 0% 0% no-repeat padding-box"};
    border: 1px solid #BC3D81;
    color: #820F4C;
    font-size:10px;
    /* line-height:18px; */
    font-family:'Roboto'
    font-style:normal;
    font-weight:500;
    /* margin-top:2px; */
    margin-bottom:auto;
    display:flex;
    align-items:center;
    white-space:nowrap;
    overflow:visible;
`

export const ErrorText = styled.span<{themeUi:string}>`
  display: inline-block; /* Ensures proper rendering for inline elements */
  max-width: 200px; /* Adjust this to set the width constraint */
  white-space: nowrap; /* Prevents text from wrapping to the next line */
  overflow: hidden; /* Hides the overflowed content */
  color:${(props)=>props.themeUi==="REGALBLAZE"?"rgb(199, 129, 14)":"rgb(130, 15, 76)"};
  text-overflow: ellipsis; /* Adds the ellipsis ('...') to indicate overflow */
`;


export const SCErrorToolTipUl = styled.ul<{themeUi:string}>`
    font-size:9px;
    width:100%;
    padding-inline:0px;
    margin-block-start:0;
    margin-block-end:0;
    margin-inline:0;
    padding:0px 0px 10px 15px;
    color:${(props)=>props.themeUi==="REGALBLAZE"?"rgb(199, 129, 14)":"rgb(130, 15, 76)"}
`

export const SCErrorToolTipLi = styled.li<{themeUi:string}>`
    margin-top:5px;
    list-style-type:circle;
    &::before{
        color: red
    }
`

