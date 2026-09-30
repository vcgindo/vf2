import styled from "styled-components";

export const VFTableWrapper = styled.div<{ height?: string, disableZoomScaling?: boolean }>`
    height:${(props) => props.height ? props.height : 'auto'};
    // max-height:90%;
    // margin:20px 0;
    zoom: 1 !important;
    width:1200px,

    & > .ag-theme-alpine{
      margin: 0 !important;
    }
    & > .ag-theme-noir-fusion{
      margin: 0 !important;
    }

    & > .ag-header-cell-resize {
      position: absolute;
      z-index: 0;
      height: 100%;
      width: 8px;
      top: 0;
      cursor: ew-resize;
    }

    
   
` 