import styled from "styled-components";


export const FilterBody = styled.div`
    // margin:0px 47px 0px 47px;
    display:flex;
    justify-content:center;
    gap:20px;  //25px
    height: max-content;
    max-height: 95vh;
    padding: 0 47px;
    // overflow: auto;

    input {
        padding: 9px;
    }
}
`
export const FilterCardWrapper = styled.div`
    width:400px;
    margin:47px 0px 47px 0px;
    background-color:white;
    // box-shadow: 0px 6px 12px #95959529;
    // border-radius: 6px;

      border: 1px solid #ccc;
      border-radius:8px;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 1px 3px;

   &:hover {
    transform: scale(1.01);
    transition: all 0.2s ease-in-out;
  }
`

export const FilterWrapper = styled.div`
height: max-content;
max-height: 600px;
overflow: visible;
`

export const NoFilterWrapper = styled.div`
height: 300px;
display: flex;
justify-content: center;
align-items: center;
font-size: 18px;
`
export const OptionsWrapper = styled.div`
display: flex;
justify-content: flex-start;
padding-left: 20px;
gap: 40px;
`

export const FilterHeader = styled.div`
height:60px;
font-style:normal;
font-variant:normal;
font-weight:500;
font-size:20px;
line-height:26px;
font-family:Roboto;
display:flex;
align-items:center;
padding-left:10px;
`

export const FilterComponent = styled.div`
background-color:white;
color: #313131;
min-height:50px;
font-style:normal;
font-variant:normal;
font-weight:300;
font-size:16px;
line-height:20px;
font-family:Roboto;
display:flex;
// align-items:center;
justify-content:center;
flex-direction:column;

`
export const SearchComponent = styled.div`
background: #F2F2F2 0% 0% no-repeat padding-box;
border-radius: 20px;
height:30px;
width:90%;
display:flex;
align-items:center;
justify-content:center;
gap:4px;

input:focus {
    outline: none;
}

`

export const ButtonContainer = styled.div`
padding: 0px 46px;
gap:40px;
display:flex;
`

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
border-radius:0px 0px 12px 12px;
`
export const DropdownGroupWrapper = styled.div`
margin:3px 9px;
display:flex;
justify-content:center;
gap:5px;

`

export const SelectDropdownComponent = styled.div`
width:60px;
flex-grow: 1;
text-align:center;
`
export const MultiSelectCheckBoxComponent = styled.div<{theme:string}>`
margin-bottom:16px;
display:flex;
justify-content:flex-start;
align-items:center;
gap:6px;
accent-color:${(props)=>props.theme==="REGALBLAZE"?"#C7810E":"#82104C"};
`

export const TextFieldHeader=styled.div`
font-style:normal;
font-variant:normal;
font-weight:300;
font-size:17px;
line-height:20px;
font-family:Roboto;
letter-spacing: 0px;
color: #313131;
text-align:left;
width:100%;
padding: 0 1rem;
box-sizing:border-box;
`
export const VFHorizonText=styled.div`
font-style:normal;
font-variant:normal;
font-weight:500;
font-size:20px;
line-height:26px;
font-family:Roboto;
display: block; 
text-align: center; 
align-items:center;
//padding-top:15px;
`
export const RangeSliderComponent=styled.div`
// border-bottom:0.5px solid #707070;
//height:100px;
padding-top:15px;
padding-bottom:15px;
display:flex;
align-items: center; 
flex-direction:column;
`

export const TextBtn=styled.div<{theme:string}>`
font-family: 'Roboto';
font-weight: 300;
font-size: 20px;
line-height: 24px;
// color: #82104C;
color:${(props)=>props.theme==="REGALBLAZE"?"#C7810E":"#82104C"};
display: flex;
align-items: center;
cursor: pointer;

&:hover {
    transform: scale(1.01);
    transition: all 0.2s ease-in-out;
  }
`

export const ConfirmationText=styled.div`
font-family: Roboto;
font-weight: 500;
font-size: 20px;
line-height: 24px;
color: rgb(0, 0, 0);
display: flex;
-webkit-box-align: center;
align-items: center;
height: 150px;
justify-content: center;
`