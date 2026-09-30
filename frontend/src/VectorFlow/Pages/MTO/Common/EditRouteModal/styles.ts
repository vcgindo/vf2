import styled from "styled-components";

export const RouteContentWrapper = styled.div`
  margin: 2rem;
  width: 70vw;
  height: 60vh;
  overflow: auto;

  & .chart-wrapper {
    width: 100%;
    max-height: 35vh; // or whatever height you want
    height: 35vh;
    padding: 0px 20px 0px 10px;

    > div{
      height: 100% !important;
      & .ag-charts-wrapper{
        max-height: 100% !important;
        .ag-charts-canvas{
          height: 100%;
          >canvas{
            height:100% !important;
          }
        }
      }
    }

    & .chart-scroll{
      height:95% !important;
      width:"100%";
    }
  }
`;

export const Text = styled.div`
  font-size: 14px;
  font-weight: 300;
`;

export const FOLGapCalculateContentWrapper = styled.div`
  display: flex;
  margin: 5px 0px;
  flex-direction: row;
  justify-content: space-between;
`;

export const DueDateContentWrapper = styled.div`
  display: flex;
  flex-direction: row;
  gap: 5rem;
  padding: 0px 15px; 
  background: #F8F8F8;
  border: 1px solid #EBEBEB;
  border-radius: 2px;
  box-shadow: -5px 4px 5px #EBEBEB;
`;

export const DueDateOptionLabel = styled.label<{isCRDDDisabled:boolean}>`
  align-items: center;
  display: flex;
  gap: 5px;
  cursor: pointer;
  pointer-events: ${(props) => props.isCRDDDisabled ? "none" : "auto" };
  opacity: ${(props) => props.isCRDDDisabled ? "0.5" : ""};
`;


export const DueDateOptionLabelText = styled.span<{ theme: string }>`
  display: flex; 
  align-items: center;
  gap: 1rem;
  font: normal normal 500 12px/16px Roboto;
  color: #585858;
`;

export const DueDateOptionDateText = styled.span<{ theme: string }>`
    align-items: center;
    font: normal normal 500 12px/16px Roboto;
    color: #000000;
`;

export const FolGapContentWrapper = styled.div`
  display: flex;
  flex-direction: column;
  margin: 2rem;
  width: 50vw;
  height: 50vh;
  overflow: auto;    
  align-items: center;
`;

export const FolGapDetailHeader = styled.span`
  text-align: center;
  font: normal normal 300 20px/40px Roboto;
  color: #000000;
`;

export const FolGapDetailHeaderInfo = styled.span`
  text-align: center;
  font: normal normal 500 16px/40px Roboto;
  color: #BC3D81;
`;

export const FolGapDetailDiv = styled.div`
  display:flex;
  flex-direction: column;
  background: #ffffff 0% 0% no-repeat padding-box;
  border: 1px solid #EBEBEB;
  border-radius: 8px;
  opacity: 1;
  height:50vh;
  width: 40vw;
  align-item: center;
  padding: 20px 30px;
`;

export const FolGapDetailHeaderInfoMain = styled.span`
  text-align: center;
  font: normal normal 500 16px/40px Roboto;
  letter-spacing: 0px;
  color: #000000;
`;