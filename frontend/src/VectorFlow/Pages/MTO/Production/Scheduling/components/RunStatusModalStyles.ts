import styled from "styled-components";

export const ModalWrapper = styled.div`
  height: fit-content;
  width: 50vw;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 10px 10px;
`;

export const ModalHeader = styled.div`
  display: flex;
  justify-content: end;
  align-items: center;
`;
export const CloseButton = styled.button`
  background: transparent;
  border: none;
  font-size: 18px;
  cursor: pointer;
`;

export const ImageWrapper = styled.img`
  height: 40vh;
  margin: 20px 0;
`;

export const FooterWrapper = styled.div`
  display: flex;
  height: 40px;
  width: 100%;
  padding: 12px;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
`;
export const ProgressWrapper = styled.div`
  width: 80%;
  margin: 8px auto;
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  justify-content: center;
`;

export const ProgressContainer = styled.div`
  width: 40vw;
  margin: 0 auto;
  height: 14px;
  //   background-color:rgba(124, 123, 123, 0.56);
  border-radius: 50px;
  border: 1.5px solid rgba(124, 123, 123, 0.56);
  overflow: hidden;
`;

export const ProgressFill = styled.div<{ value: number }>`
  height: 100%;
  width: ${({ value }) => value}%;
  background: linear-gradient(
    90deg, /* left → right */
    #b52670,
    #ff69b4,
    #b52670
  );
  background-size: 200% 200%;
  animation: gradientFlow 3s linear infinite;

  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50px;
  color: white;
  font-weight: bold;
  font-size: 1rem;
  transition: width 0.3s ease-in-out;

  @keyframes gradientFlow {
    0% {
      background-position: 0% 50%;
    }
    100% {
      background-position: 200% 50%; /* move rightward */
    }
  }
`;


export const ProgressMessage = styled.div`
  margin: 0 auto;
  font-size: 1.1rem;
  font-weight: 500;
  color: rgb(56, 54, 54);
`;

export const DateTimeWrapper = styled.span`
  display: flex;
  width: fit-content;
  justify-content: center;
  align-items: center;
  gap: 10px;
  font-size: 1.1rem;
`;