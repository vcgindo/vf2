import styled from 'styled-components'
import * as globalStyles from "../../../../styles/global";

export const ContentWrapper=styled.div`
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 3px 6px #00000029;
    border: 1px solid #E0E0E0;
    border-radius: 8px;
    opacity: 1;
    // height:110vh;        //955
    margin-left:25px;
    margin-bottom:40px;
`
export const TextContainer=styled.div`
    //background-color:grey;
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-size:24px;
    line-height:40px;
    font-family:Roboto;
`
export const TextFilterWrapper=styled.div`
    padding:19px 25px 29px 25px ;
    display:flex;
    justify-content:space-between;
`
export const VFMasterGroupCard=styled.div`
    width: 440px;
    height:586px;
    // aspect-ratio:0.5;
    display:flex;
    flex-direction:column;
    align-items:center;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    box-shadow: 0px 3px 6px #00000029;
    border-radius: 7px;
    opacity: 1;
    margin-left:30px;
    zoom:0.8;
    // overflow:overlay;
    overflow: hidden;
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
    background: #CBCBCB 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 9px #41414129;
    border-radius: 30px;
    opacity: 1;
    }
    padding-bottom:15px;


`  
export const VFMasterGroupCardHeader= styled.div`
height: 60px;
width:100%;
background: black;
border-radius: 8px 8px 0px 0px;
opacity: 1;
`
export const VFMasterGroupCardHeaderText=styled.div`
text-align: center;
padding-top:10px;
font-style:normal;
font-variant:normal;
font-weight:400;
font-size:20px;
line-height:40px;
font-family:Roboto;
letter-spacing: 0px;
color: white;
opacity: 1;
height:70px;
`
export const VFButtonWrapper=styled.div`
margin-top:12px;
margin-left:54px;
margin-bottom:12px;
display: flex;
`
export const VFMasterGroupCardContent=styled.div<{theme:any}>`
width: 100%;
height: 80px;
margin-top:16px;
background: #FFFFFF 0% 0% no-repeat padding-box;
border: 1px solid #EBEBEB;
border-radius: 7px;
opacity: 1;
display:flex;
flex-direction:row;
text-align: left;
color: #6C696A;
opacity: 1;
cursor:pointer;

&:hover{
    background-color: ${(props) => globalStyles.chooseThemeColor[props.theme]?.color5};
    & > div:nth-child(1){
        background-color: ${(props) => globalStyles.chooseThemeColor[props.theme]?.color5};
        border: 1px solid white;
    }
    // & > div:nth-child(2){
    //     color: white;
    // }  
}
`

export const VFMasterGroupCardImage=styled.div`
    display:inline block;
    margin-left:10px;
    width: 65px;
    height: 65px;
    background: #F4F4F4 0% 0% no-repeat padding-box;
    margin-top:7px;
    margin-left:8px;   
    opacity: 1;
    border-radius: 50px;
    display: flex;
    align-items: center;
    justify-content:center;
    margin-bottom:7px;
`
export const VFMasterGroupCardText=styled.div`
    text-align: left;
    font-style:normal;
    font-variant:normal;
    font-weight:400;
    font-size:20px;
    line-height:40px;
    font-family:Roboto;
    letter-spacing: 0px;
    color: #6C696A;
    opacity: 1;
    padding-left:8px;
    display: flex;
    align-items: center;
    justify-content:center;


`
export const VFMasterGroupCardContainer=styled.div`
    display: flex;
    align-items: center;
    justify-content:flex-start;
    overflow-y: scroll;
    padding-bottom:15px;
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
    background: #CBCBCB 0% 0% no-repeat padding-box;
    box-shadow: 0px 6px 9px #41414129;
    border-radius: 30px;
    opacity: 1;
    }

    margin-left:30px;
    margin-right:30px;
    border-radius:8px;

`
