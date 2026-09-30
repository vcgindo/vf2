import styled from "styled-components";

export const TableWrapper = styled.div`
height: 85vh;
display: flex;
margin-left: 20px;
flex-direction: column;
gap: 10px;
   & > .ag-theme-alpine{
        flex: 1;
        height: 100%;
    }

     & .ag-paging-panel {
       z-index: 1; 
      font-size: 11px !important;
      font-family:'Roboto' !important;
      position: relative !important;
    }

    & .ag-status-bar{
      z-index: 2 !important; 
      display: flex  !important; 
      justify-content: space-between !important;
      align-items: center !important;
      border:none !important;
      width: calc(100% - 230px) !important;
      position: absolute !important;
      bottom: -0px !important; 
    }    
`