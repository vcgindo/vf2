
import styled from 'styled-components'

export const VFMasterCardContainer = styled.div`
min-width: 345px;
height: 419px;
display:flex;
flex-direction:column;
background: #FFFFFF 0% 0% no-repeat padding-box;
box-shadow: 0px 6px 12px #95959529;
border-radius: 6px;
opacity: 1;

`

export const VFMasterCardHeader = styled.div`
    display:flex;
    align-items:center;
    text-align: left;
    font-size:20px;
    font-family:'Roboto';
    letter-spacing:0px;
    font-weight:500;
    letter-spacing: 0px;
    color: #313131;
    opacity: 1;
    height:60px;
    width:100%;
    padding:20px 16px;
    border-bottom:solid 0.5px #ECECEC;

    justify-content:space-between;
`

export const VFMasterCardListContainer = styled.div`
    display:flex;
    flex-direction:column;
    width:100%;
    overflow-y:overlay;
    &::-webkit-scrollbar{
        width: 7px;       
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

export const VFMasterCardListItem = styled.div<{isSelected:boolean,themeUi:string}>`
background-color:${props=> props.isSelected ?props.themeUi==="REGALBLAZE"? 'rgb(252, 163, 17,0.3) ':'#bc3d814d' : ''};
display:flex;
align-items:center;
height: 33px;
padding:7px 16px;
width:100%;
/* UI Properties */
text-align: left;
font-weight:400;
font-size:16px;
font-family:Roboto;
letter-spacing: 0px;
color: #313131;
opacity: 1;
border-bottom:solid 0.5px #ECECEC;
`


export const VFMasterCardCheckBox = styled.input<{themeUi: string}>`
appearance:none;
width:20px !important;
height:20px !important;
border-radius:50%;
outline:none;
border:1px solid grey;  
    &:checked {
        // background-color: #bc3d81; 
        background:${(props) => props.themeUi==="REGALBLAZE"?"#FCA311": "#BC3D80"  };
        border:none;
            &::after { 
                content: '✓';
                color:white;
                margin-left:5px;
            }
    }
 
`
