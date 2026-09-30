import styled, { keyframes } from "styled-components";

export const FinalResultSectionWrapper = styled.div`
  height: fit-content;
  postion: relative;
`;

export const GridWrapper = styled.div`
  position: relative; /* important for absolute positioning of the tab */
  overflow: hidden;
  display: flex;
  padding-left: 20px;
  padding-top: 15px;
  flex-direction: column;
  gap: 16px;
  height: 78vh;

  & > .ag-theme-alpine {
    flex: 1;
    }

   & .ag-theme-alpine .ag-header-row:nth-child(2){
    background-color: black;
    color: white;
  }
  & .ag-theme-alpine .ag-header-row:nth-child(1):hover{
    background-color: black;
    color: white;
  }
  & .ag-theme-alpine .ag-header-row:nth-child(3), & .ag-theme-alpine .ag-header-row-column-filter{
    background-color: #f7f7f7 !important;
    color: black !important;
  }
`;

export const SectionWrapper = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px 0 16px 16px;
`;

export const ChartWrapper = styled.div`
  flex: 1;
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 16px;
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
`;

export const shimmer = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`;

export const SkeletonBlock = styled.div<{ width?: string; height?: string }>`
  background: #eee;
  background-image: linear-gradient(90deg, #eee 0px, #f5f5f5 40px, #eee 80px);
  background-size: 200px 100%;
  animation: ${shimmer} 1.5s infinite linear;
  border-radius: 4px;
  margin: 6px 0;
  width: ${(p) => p.width || "100%"};
  height: ${(p) => p.height || "20px"};
`;

export const ResourceViewWrapper  = styled.div`
display: flex;
flex-direction: column;
`

export const StatusBarWrapper = styled.div`
    position: sticky;
    bottom: 0;
    width: calc(100% + 24px);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px 24px 12px 12px;
    background: white;
    shadow: 0px -2px 6px rgba(0, 0, 0, 0.4);
    border-top: 1px solid #E0E0E0;
`

export const LeftSection = styled.span`
    display: flex;
    align-items: center;
    gap: 24px;
    margin-left: 20px;
`
export const MainSection = styled.div`
  display: flex;
  height: 100%;
  flex-direction: column;
  justify-content: space-between;

`