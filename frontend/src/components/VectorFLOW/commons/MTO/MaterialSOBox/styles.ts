import styled from 'styled-components';

export const PercentBorderContainer = styled.div`
    height: 100%;
    width: 100%;
    font-size: 8px;
    display: flex;
    justify-content: center;
    align-items: center;
`

export const Percentborder = styled.div` 
    border: 3px solid #F0F0F0;
    border-radius: 50%;
    background-color:#CDCDCD;
    height: 38px;
    width: 38px;
    margin-left: auto;
    margin-right: auto;
    position: relative;
`

export const Percent = styled.h3`
    text-align: center;
`
export const BtnGroup = styled.div`
    height: 60px;
    width:100%;
    display: flex;
    //padding-top: 0;
    //background-color:#EBEBEB
    
`

export const Btns = styled.button`
    width: 100%;
    padding-top:5px;
    padding-right:5px;
    display: flex;
    font-size: 10px;
    justify-content: center;
    align-items: center;
`

export const ViewOrder = styled.button<{theme:string}>`
    font-size:8px;
    color:${(props) =>
        props.theme === 'REGALBLAZE'
          ? "#CB830E"
          : "#BC3D81"};
    margin-bottom:22px;
    background-color: ${(props) =>
      props.theme === 'REGALBLAZE'
        ? "#fcf4f0"
        : "#fcf0f7"};
    width:70%;
    padding:7px;
    text-align:center;
    border-radius:8px;
`
export const TextOnBox = styled.div`
    position:absolute;
    bottom:100%;
    left:0;
    background-color:#E0E0E0;
    width:90px;
    zoom: 0.8;
    padding: 4px;
    border-radius:8px 8px 0 0;
    fontColor:#000;
    justify-content:'center';
    display:flex;
    align-items: center;
    justify-content: center;
`
export const ImgDiv = styled.div`
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: center;
    padding:1px;
    font-weight:bold;
`

export const ColorOnLeft = styled.div<{ color: string, height: string }>`
    position:absolute;
    right:100%;
    border-radius: 8px 0 0 8px;
    background-color: ${props => props.color};
    width:15px;
    height:${props => props.height};

    &:nth-of-type(1){
        top:0px;
        z-index: 0;
    }
    &:nth-of-type(2){
        top:11px;
        z-index:1;

    }
    &:nth-of-type(3){
        top:21px;
        z-index:2;
    }
`

export const Separator = styled.div<{ color: any }>`
    border-right:1px solid ${(props) => props.color};
    height:85%;
    margin:auto
    `


export const BTRLayoutTabsWrapper = styled.div`
    display:flex;
    justify-content:center;
    margin-bottom:15px;
`

export const ButtonImg = styled.img`
    justify-content:center;
    align-item:center;
    margin-right:2px;
    transition:0.3s ease-in-out;
    &:hover{
        transform:scale(1.3);
    }
`
export const Btncount = styled.div`
    justify-content:center;
    align-item:center;
    width:100%;
`
export const diviLine = styled.div`
    width:"400" 
    style:"border: 2px dashed #C0C0C0" 
    color:"#FFFFFF" 
    size:"6"
`

export const TextOnColor = styled.h3`
    font-size: 10px;
    transform: rotate(-90deg);
    text-wrap: nowrap;
    color: white;
`
export const underLine = styled.div`
    width:"400" 
    style:"border: 1px solid #000" 
    color:"#000"    
`
export const ProcurementLayout = styled.div`
    height: '100%';
    width: 1200px;
`

export const ColoronLeftWrapper = styled.div`
    position:absolute;
    right:100%;
    border-radius: 8px 0 0 8px;
    transition:0.3s ease-in-out;
    &:hover{
      border:2px solid transparent;
    }
`
