import styled from "styled-components";


export const FilterBody = styled.div`
margin:0px 47px 0px 47px;
display:flex;
justify-content:center;
overflow-y:auto;
gap:10px;  //25px

}
`
export const FilterCardWrapper = styled.div`
width:270px;
margin:47px 0px 47px 0px;
background-color:white;
box-shadow: 0px 6px 12px #95959529;
border-radius: 6px;
height:max-content;
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
margin-right:46px;
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

export const SkeletonWrapper = styled.div`
    display:flex;
    justify-content:center;
    flex-direction:column;
    width:1200px;
    max-width:100%;
`
export const SkeletonContainer = styled.div`
    display:flex;
    justify-content:center;
    width:100%;
`

export const SkeletonGroup = styled.div`
    width:270px;
    margin:47px 10px;
`

export const SkeletonFooter = styled.div`
    width:100%;
    display:flex;
    justify-content:flex-end;
    margin-top:10px;
    padding:30px 20px;
`