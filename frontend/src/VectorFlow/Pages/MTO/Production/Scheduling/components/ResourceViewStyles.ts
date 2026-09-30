import styled, { keyframes } from "styled-components";

export const SectionWrapper = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px 0 16px 16px;
  position: relative;
  margin-top: 24px;
`;

export const GridWrapper = styled.div`
  position: relative; /* important for absolute positioning of the tab */
  border: 1px solid #ccc;
  border-radius: 0 8px 8px 8px;
  padding: 16px 16px 25px 16px; /* top padding increased so content doesn't overlap with the tab */
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 400px;

  & > .ag-theme-alpine {
    flex: 1;
    }
`;

export const WorkStationDropDown = styled.select`
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: fit-content;
  font-size: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  background-color: white;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #9c0d64;
    box-shadow: 0 0 5px rgba(156, 13, 100, 0.5);
  }

  option {
    background-color: white; /* default option background */
    color: #333;

    &:checked {
      background-color: #b52670; /* selected */
      color: white;
    }

    &:hover {
      background-color: #ffb6c1; /* pink shade on hover */
      color: #333;
    }
  }
`;


export const Tab = styled.div`
  position: absolute;
  top: -25px;
  left: 16px;
  height: 40px;
  padding: 10px 80px 10px 20px;
  display: flex;
  align-items: center;
  color: white;
  font-weight: 500;
  font-size: 1.2rem;
  background: linear-gradient(135deg, #9c0d64, #c71585);
  border-top-left-radius: 8px;
  clip-path: polygon(0 0, 75% 0, 100% 100%, 0% 100%);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
`;

export const FilterSection = styled.div`

  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
`

export const ToggleWrapper = styled.div`
  display: flex;
  background: #fff;
  border-radius: 50px;
  padding: 4px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  width: fit-content;
  gap: 6px;
`;

export const ToggleButton = styled.button<{ active?: boolean }>`
  flex: 1;
  padding: 8px 16px;
  border-radius: 50px;
  border: none;
  cursor: pointer;
  background: ${({ active }) => (active ? "#b23a7d" : "transparent")};
  color: ${({ active }) => (active ? "#fff" : "#555")};
  font-size: 0.85rem;
  font-weight: 500;
  min-width: fit-content;
  transition: all 0.3s ease;

  &:hover {
    background: ${({ active }) => (active ? "#b23a7d" : "#f0f0f0")};
  }
`;

export const ResourceSectionWrapper = styled.div`
  width: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px 0 16px 16px;
  position: relative;
`;

export const ChartWrapper = styled.div`
  position: relative; /* so child can be positioned */
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
  background-image: linear-gradient(
    90deg,
    #eee 0px,
  #f5f5f5 40px,
    #eee 80px
  );
  background-size: 200px 100%;
  animation: ${shimmer} 1.5s infinite linear;
  border-radius: 4px;
  margin: 6px 0;
  width: ${(p) => p.width || "100%"};
  height: ${(p) => p.height || "20px"};
`;



