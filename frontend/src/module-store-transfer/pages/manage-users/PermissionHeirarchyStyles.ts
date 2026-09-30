import styled from "styled-components";

export const ToggleContainer = styled.div`
  display: flex;
  background-color: #fff;
  //   border: 1.5px solid #d08ba5;
  border-radius: 999px;
  overflow: hidden;
  width: fit-content;
  padding: 3px;
  gap: 8px;
  font-size: 8px;
`;

export const ToggleButton = styled.button<{ active: boolean }>`
  padding: 4px 14px;
  border: none;
  background-color: ${({ active }) => (active ? "#f1d2e0" : "#f5f5f5")};
  color: ${({ active }) => (active ? "#c72e64" : "#000")};
  font-weight: ${({ active }) => (active ? "bold" : "normal")};
  border-radius: 999px;
  cursor: pointer;
  font-size: 10px;
  transition: background 0.3s ease, color 0.3s ease;

  &:hover {
    background-color: ${({ active }) => (active ? "#f1d2e0" : "#f5f5f5")};
  }
`;

export const ChartWrapper = styled.div`
  & .react-flow__attribution {
    display: none;
  }
`
