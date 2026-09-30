import styled from "styled-components";

export const Rectangle = styled.div<{text?:string , theme?:string}>`

  display: flex;
  width: 98%;
  height: 30vh;
  background-color: #f0f0f0;
  justify-content: left;
  gap : 4rem;
  align-items: center;
  margin: 0 auto;
  margin-left: 3rem;
  border-radius: 12px;
  box-shadow: 0px 6px 12px #9a9a9a40;
  position: relative;
  font-weight: 600;
  font-size : 1.2rem;
  &::before {
    content: "${props => props.text ? props.text : ""}";
    display: flex;
    -webkit-box-pack: center;
    justify-content: center;
    height: 36px;
    -webkit-box-align: center;
    text-align: center;
    align-items: center;
    color: white;
    position: absolute;
    padding: 0.5rem 1rem 0.5rem;
    width: 104px;
    right: calc(100% - 44px);
    border-radius: 12px 12px 0px 0px;
    transform: rotate(-90deg);
    z-index: -1;
    background: ${(props)=>props.theme==="REGALBLAZE"?"#CB830E":"rgb(188, 61, 129)"};
}
  &::after {
    content: "";
    display: block;
    position: absolute;
    width: 0px;
    height: 0px;
    left: -6px;
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-bottom: 10px solid ${(props)=>props.theme==="REGALBLAZE"?"#CB830E":"rgb(188, 61, 129)"};;
    transform: rotate(90deg);
    z-index : 3; 
}
`;

export const CardContainer  = styled.div`
  overflow: auto;
  display: flex;
  width: 100%;
  gap: 3rem;
  height: 100%;
  padding:   2rem;
`;

export const LandingContainer = styled.div`
  padding: 2rem;
  /* overflow: auto; */
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  font-family: "Roboto";
  margin-left : 2rem;
`;

export const LandingPageDivider = styled.div`
  width: 98%;
  border: 1.3px dashed #a8a5a5;
  opacity: 1;
  gap: 5rem;
  margin: 1rem 0 1rem 3rem;
`;

export const AppBox = styled.div`
  height: 100%;
  min-width: 275px;
  border-radius: 12px;
  background: #FFFFFF 0% 0% no-repeat padding-box;
  box-shadow: 0px 6px 12px #9A9A9A26;
  opacity: 1;
  float: left;
  width: 25%;
  position: relative; 
  z-index : 1;
`;

export const ImageHolder =  styled.div<{theme: string}>`
 position: relative;
 display: flex;
 align-items: center;
 z-index : 2;  
 height: 40%;
 margin-left: 10%;
 padding-top: 1rem;
 &::before {
    content: "";
    height: 90%; 
    width: 27%; 
    background: ${(props)=>props.theme==="REGALBLAZE"?"#FFEED3 0% 0% no-repeat padding-box":"#FFEFF7 0% 0% no-repeat padding-box"};
   
    border-radius: 50%;
    position: absolute;
    top: 20%;
    opacity: 1;
    z-index : 2;
  }
`;
export const  Image = styled.img`
  position: relative;
  height: 80%;
  z-index:3;
  margin-left : 12%;
  margin-top : 5%;
`;

export const AppBoxDivider = styled.div`
  width: 100%;
  border: 1.3px dashed #a8a5a5;
  opacity: 1;
  gap: 5rem;
  /* margin: 1rem 0 1rem 3rem; */
`;

export const ClickBox = styled.div`
  display: flex;
  /* position:  relative; */
  justify-content : right;
  margin-right : 1rem;
  align-items : center;
  cursor : pointer;
  flex: 1;
  align-items: center;
`

export const AppBoxDiv = styled.div`
   height: 100%;
   padding-top:0.5rem;
   display: flex;
   flex-direction: column;
`;
