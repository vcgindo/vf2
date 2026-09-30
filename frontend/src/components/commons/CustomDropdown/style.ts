import styled from "styled-components";

export const DropdownWrapper = styled.div<{ topPos: any, leftPos: any }>`
  position: absolute;
  top: ${(props) => props.topPos };
  left: ${(props) => props.leftPos };
  background-color: #fff;
  border: 1px solid #ccc;
  z-index: 9999;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  max-height: 300px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;

`;
