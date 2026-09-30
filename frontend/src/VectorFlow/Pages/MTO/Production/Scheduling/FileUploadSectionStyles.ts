import styled from "styled-components";

export const Wrapper = styled.div`
  position: relative;
  margin: 0 100px;
  padding-bottom: 55px;
`;

export const GridContainer = styled.div`
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 40px; /* left padding for side tab space */
  padding-left: 40px;
  margin-top: 20px;
  background: rgba(246, 206, 233, 0.28);
  border-radius: 6px;
`;

export const SideTab = styled.div`
  position: absolute;
  top: 50%;
  left: 0;
  transform: translate(-50%, -50%) rotate(180deg); /* make it overlap border */
  background: linear-gradient(180deg, #b03775, #993366);
  color: white;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 12px;
  font-weight: bold;
  padding: 12px 8px;
  height: 130px;
  border-radius: 5px;
  cursor: default;
  box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.25);

  &::after {
    content: "";
    position: absolute;
    left: -8px;
    top: 50%;
    transform: translateY(-50%) rotate(180deg);
    width: 0;
    height: 0;
    border-top: 8px solid transparent;
    border-bottom: 8px solid transparent;
    border-left: 8px solid #993366;
  }
`;

export const CheckUpdatesWrapper = styled.div`
  display: flex;
  justify-content: flex-end;
  padding: 0 40px;
  align-items: center;
  gap: 22px;
  margin-top: 15px;
`;
export const LastUpdateStatus = styled.span`
  font-size: 1rem;
  color: rgb(96, 93, 93);
  padding: 4px;
`;

export const FileUploadSkeletonTile = styled.div`
  height: 120px;
  border-radius: 6px;
  background: linear-gradient(90deg, #eee 25%, #ddd 50%, #eee 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;

  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }
`;