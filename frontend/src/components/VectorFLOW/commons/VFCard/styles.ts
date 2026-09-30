import styled from "styled-components";

export const Card = styled.div<{imgSrc:string}>`
    display:flex;
    justify-content:center;
    align-items:center;
    background: rgba(0, 0, 0, 0.01) url(${props => props.imgSrc}) center center no-repeat padding-box;
    background-size: cover;
    border: 1px solid rgb(178, 167, 167,0.1);
    border-radius: 16px;
    padding:45px 36px;
    width:100%;
    
`

export const IconCardContainer = styled(Card)`
    aspect-ratio:1.824;
    cursor: pointer;
    :hover {
        transform: scale(1.02);
    }

    
`

export const ButtonCardContainer = styled(Card)`
    aspect-ratio: 2.75;

    & > *:nth-child(2),
    & > *:nth-child(3) {
        opacity: 0;
        visibility: hidden;
    }
`;

export const CardText = styled.p<{themeUi:string}>`
    cursor:pointer;
    margin-right:65px;
    height: 68px;
    text-align: left;
    display:flex;
    align-items:center;
    font-style:normal;
    font-variant:normal;
    font-size:20px;
    line-height:40px;
    font-family:'Roboto';
    font-weight:500;
    letter-spacing: 0.34px;
    color: #6C696A;
    &:hover{
        color:${(props)=>props.themeUi==="REGALBLAZE"?"#FCA311":"#BC3D81"};
        transform:scale(1.1);
    }
    transition:0.3s ease-in-out;
    @media (max-width: 1280px){
        font-size:18px;
        line-height:30px;
    }
`


export const CardButton = styled.button<{themeUi:string}>`
    width: 100%;
    height: 50px;
    border-radius:6px;
    font-size:20px;
    line-height:28px;
    font-family:Roboto;
    font-weight:500;
    letter-spacing: 0.34px;
    color: #6C696A;
    box-shadow: inset 0px 0px 2px #00000029, 0px 3px 6px #00000029;
    border: 1px solid #9A9A9A;
    opacity: 1;
    background-color:transparent;
    &:hover{
        color:#FFFFFF;
        background:${(props)=>props.themeUi==="REGALBLAZE"?"transparent linear-gradient(261deg, #FCA311 0%, #CB830E 100%) 0% 0% no-repeat padding-box":"transparent linear-gradient(180deg, #BC3D81 0%, #820F4C 100%) 0% 0% no-repeat padding-box"} ;
        border:none;
    }
    transition: 0.3s ease-in-out;
    @media (max-width: 1280px){
        font-size:16px;
        line-height:30px;
        letter-spacing:0px;
    }
`

export const CardIconWrapper = styled.div`
    // cursor:pointer;
    width: 44px;
    height: 44px;
`