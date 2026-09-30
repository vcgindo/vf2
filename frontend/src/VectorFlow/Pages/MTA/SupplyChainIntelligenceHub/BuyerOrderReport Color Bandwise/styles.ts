import styled from "styled-components";

export const BORLayout = styled.div`
    // margin-top:25px;
    margin-left:15px;
`


export const BORTaskBar  = styled.div`
    position:fixed;
    width:97%;
    right:0;
    top:13vh;
    height:70px;
    background-color:white;
    display:flex;
    flex-direction:row;
    justify-content:flex-end;
    align-items:center;
    gap:20px;
    padding:16px;
    z-index:2;
    transition:0.3s ease 0s;
`
export const BORColorCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 97px;
    height: 34px;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 4px;
    position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`

// export const BPRViewTableWrapper = styled.div`
//     width:100%;
//     display:flex;
//     margin-top:20px;
// `

// export const BPRViewTablePrefix = styled.img`
//     width: 52px;
//     height: 150px;
//     transform:translateX(11px);
// `

// export const BPRViewTableGrid = styled.div`
//     display:flex;
//     flex-direction:column;
//     width:100%;
//     background: #FFFFFF 0% 0% no-repeat padding-box;
//     box-shadow: 0px 6px 12px #9B9B9B29;
//     border-radius:8px;
//     overflow-y:scroll;
//     scrollbar-gutter: stable both-edges;
//     &::-webkit-scrollbar{
//         width: 7px;       
//     }
    
//     &::-webkit-scrollbar-track{
//         border-radius: 30px;
//         opacity: 1;
//     }
    
//     &::-webkit-scrollbar-thumb{
//         width: 7px;
//     /* UI Properties */
//     background: #313131 0% 0% no-repeat padding-box;
//     box-shadow: 0px 6px 9px #41414129;
//     border-radius: 30px;
//     opacity: 1;
//     }
// `

// export const BPRViewTableHeaderContainer = styled.div`
//     display:flex;
//     flex-direction:row;
//     position:sticky;
//     top:0;
//     background-color: white;
//     z-index:100;
// `

// export const BPRViewTableHeader = styled.div`
//     position:relative;
//     width:100%;
//     height:45px;
//     padding:10px;
//     font-style:normal;
//     font-variant:normal;
//     font-weight:500;
//     font-size:16px;
//     line-height:21px;
//     font-family:Roboto;
//     letter-spacing: 0px;
//     color: #000000;
//     text-align:center;
//     &::after{
//         content:'';
//         position:absolute;
//         right:0;
//         top:4px;
//         bottom:4px;
//         background-color:#898585;
//         width:1px;
//     }
//     &:last-child::after {
//         display: none;
//     }
// `

// export const BPRViewTableRowContainer = styled.div`
//     width:100%;
//     display:flex;
//     flex-direction:column;
//     max-height:250px;
// `

// export const BPRViewTableRow = styled.div`
//     width:100%;
//     display:flex;

// `

// export const BPRViewTableRowCell = styled.span`
//     width:100%;
//     height:50px;
//     padding:6px;
//     text-align:center;
//     font-style:normal;
//     font-variant:normal;
//     font-weight:medium;
//     font-size:14px;
//     line-height:24px;
//     font-family:Roboto;
//     letter-spacing: 0px;
//     color: #000000;
//     white-space:nowrap;
//     text-overflow:ellipsis;

// `

// export const ReadMoreToolTip = styled.div`
//     position:absolute;
//     top:0;
// `


// export const BPRTagsCellRendererWrapper = styled.div`
//     display:flex;
//     justify-content:center;
//     align-items:center;
//     width: 55px;
//     height: 25px;
//     background: #8E8E8E 0% 0% no-repeat padding-box;
//     color: #FFFFFF;
//     box-shadow: 0px 6px 12px #8D8D8D29;
//     border-radius: 2px;
//     font-style:normal;
//     font-variant:normal;
//     font-weight:medium;
//     font-size:14px;
//     line-height:19px;
//     font-family:Roboto;
//     letter-spacing: 0px;
//     position: absolute;
//   top: 50%;
//   left: 50%;
//   transform: translate(-50%, -50%);

// `


// export const BPRRemarksCellRendererWrapper = styled.div`
//     position:relative;
//     width:100%;
//     height:100%;
// `

// export const BPRRemarksToolTipWrapper = styled.div`
//     position:absolute;
//     height:400px;
//     width:400px;
//     background-color:red;
//     z-index:100000;
// `