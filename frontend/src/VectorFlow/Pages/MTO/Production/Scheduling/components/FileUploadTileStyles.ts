import styled from "styled-components";

export const Container = styled.div`
  border: 1.5px dashed #d17ca0; /* Pink dashed border */
  padding: 14px 16px;
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  border-radius: 8px;
  background: #fff;
  max-width: 500px;
`;

export const LeftSection = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 1.1rem;
  cursor: pointer;
`;

export const ButtonsWrapper = styled.div`
  display: flex;
  gap: 10px;
`;

export const ButtonContentWrapper = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 1.1rem;
  color: #ffffff;
`;