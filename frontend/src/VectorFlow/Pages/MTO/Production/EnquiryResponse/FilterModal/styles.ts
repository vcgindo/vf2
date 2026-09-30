import styled from "styled-components";

export const BackgroundCover = styled.div`
    position: fixed;
    z-index: 99999;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    background-color: #0000004a;
    display: flex;
    justify-content: center;
    align-items: center;
`;

export const ModalWrapper = styled.div`
    overflow: auto;
    height : 78vh;
    width: 690px;
`;

export const ModalHeader = styled.div` 
    border-radius: 8px 8px 0px 0px;
    height: 50px;
    background-color: black;
    display: flex;
    justify-content: center;
    align-items: center;
`;

export const Heading = styled.div` 
    color: white;
    font-size: 1.5rem;
    letter-spacing: 0.15rem;
`;

export const ModalBody = styled.div` 
 min-height: 100px;
 display: flex;
 align-items: center;
 justify-content: center;
 padding: 40px 100px;
`;

export const ModalFooter = styled.div` 
    border-top: 1px dashed #868585;
    display: flex;
    justify-content: end;
    gap: 20px;
    padding: 50px;
`;

export const CloseIcon = styled.div`
    color: white;
    padding: 20px;
    position: absolute;
    right: 10px;
    cursor: pointer;
`;

export const CloseBtn = styled.div` 
    border: 1px solid #868585;
    color: #868585;
    display: flex;
    font-size: 1rem;
    padding: 10px 50px;
    border-radius: 4px;
    align-items: center;
    justify-content: center;
    cursor: pointer;
`;

export const ApplyBtn = styled.button` 
    color: white;
    border: none;
    font-size: 1rem;
    padding: 10px 50px;
    border-radius: 4px;
    cursor: pointer;
    background-image: linear-gradient(to right, #8D2E61, #BB3F81, #DB6BA7);
`;

export const FilterContainer = styled.div`
    background-color: white;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    width: 422px;
    border-radius: 8px;
    font-size: 1.5rem;
    box-shadow: 0px 6px 12px #95959529;
`;

export const FilterHeading = styled.div` 
    display: flex;
    justify-content: center;
    padding: 20px;
    font-family: 'Roboto', sans-serif;
    font-weight: 500; /* Medium */
    font-size: 20px;
    color: #313131;
    letter-spacing: 0;
    line-height: 24px;
`;

export const SearchBar = styled.div` 
    display: flex;
    -webkit-box-align: center;
    align-items: center;
    padding: 10px 20px;
    border-radius: 40px;
    background: rgb(242, 242, 242);
    width: 80%;
    margin: 10px auto;
    width: 403px;
    height: 55px;
    background: #F2F2F2 0% 0% no-repeat padding-box;
    border-radius: 40px;
    opacity: 1;
    
`;

export const FilterAccordianWrapper = styled.div` 
    width: 100%;
`;

export const PlantInput = styled.input`
background: #F2F2F2;
border: none;
outline: none;
height: 50px;
width: 100%;
font-size: 2rem;
`;

export const HorizontalLine = styled.div`
height: 2px;
width: 100%;
background-color: #F4F4F4;
`;

export const ButtonFilterWrapper = styled.div`
border-top: 1px dashed #A0A0A0;
opacity:1px;
height:109px;
width:100%;
display:flex;
justify-content:flex-end;
flex-direction:row;
align-items:center;
background-color:#F4F4F4;
border-radius: 0px 0px 12px 12px;
`

export const ButtonContainer = styled.div`
margin-right:46px;
gap:40px;
display:flex;
`
export const OptionsWrapper = styled.div`
    display: flex;
    flex-direction: column;
    margin-left: 20px;
`;

export const Option = styled.div`
    width: 100%;
    display: flex;
    gap: 10px;
    padding: 5px 10px;
    font-family: 'Roboto';
    font-weight: 300;
    font-size: 16px;
    letter-spacing: 0px;
    color:#313131;

     &:hover{
    background-color:rgb(249, 249, 249)
    }
    
`;

export const AccordianContainer = styled.div`
    padding : 20px;
    border-top: 3px solid rgb(244, 244, 244);
`