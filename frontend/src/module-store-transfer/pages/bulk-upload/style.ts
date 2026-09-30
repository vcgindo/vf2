import styled, { css, keyframes } from 'styled-components'

export const UploadSectionWrapper = styled.div`
    width: 100%;
    display: flex;
    height: 100%;
    overflow: hidden;
`

export const NoData = styled.div`
    width: 50%;
    height: 80%;
    display: flex;
    justify-content: center;
    align-items: center;
    
`

// Left section styles
export const LeftSectionWrapper = styled.div`
    width: 50%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 6rem;
    margin-top: 5rem;
    padding-left: 5rem;
    padding-bottom: 10rem;
`


export const LeftCommonComWrapper = styled.div`
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: start;
    gap: 1.2rem;
`

export const LeftStep = styled.div`
    display: inline-block;
  background-color: #870d48; /* Deep purple/pink */
  color: white;
  padding: 8px 25px 8px 15px;
  font-weight: bold;
  border-radius: 6px 0 0 6px;
  font-size: 0.8rem;
  clip-path: polygon(0 0, 80% 0, 100% 50%, 80% 100%, 0 100%, 0% 50%);
`

export const LeftCommonComUploadWrapper = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 90%;
    background-color: #fff;
    border: 1.8px dashed rgba(249, 28, 28, 0.5);
    border-radius: 2px;
    padding: 1rem 3rem;
    height:8rem;
`
export const HeaderSection = styled.div`
    display: flex;
    flex-direction: column;
    text-align:center;
    align-items: start;
    vertical-align: middle;
`

type HeaderTextProps = {
    fontSize?: string;
    fontWeight?: string;
}

type SubTextProps = {
    fontSize?: string;
    fontWeight?: string;
}


export const HeaderText = styled.div<HeaderTextProps>`
    font-size: ${props => props.fontSize || '1.35rem'};
    font-weight: ${props => props.fontWeight || '600'};
    display: flex;
    align-items: center;
    gap: 8px;
`
export const SubText = styled.div<SubTextProps>`
    font-size: ${props => props.fontSize || '1.15rem'};
    font-weight:  ${props => props.fontWeight || '300'};
    color: #666;
`
// Right section styles
export const RightSectionWrapper = styled.div`
    width: 50%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 2rem;

`

export const ProgressBoxWrapper = styled.div`
    width : 20rem;
    height: 20rem;
    border-radius: 10px;
    background-color: #fff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 0.4rem;
`

export const Svg = styled.svg`
  display: block;
`;

export const Circle = styled.circle<{ strokeWidth?: number }>`
  transition: stroke-dashoffset 0.5s ease;
`;

export const Text = styled.text`
  font-size: 1.4rem;
  fill: #bd2c84;
  font-weight: bold;
  text-anchor: middle;
  dominant-baseline: middle;
`;

export const LabelText = styled.div`
  margin-top: 0.8rem;
  font-size: 1.4rem;
  color: #888;
`;


export const FilePanel = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border-radius: 0.5rem;
    background-color:rgb(239, 239, 239);
    width:50rem;
    &:hover{
        background-color:rgb(215, 211, 211);
        cursor: pointer;
    }
`

export const FileName = styled.div`
    display: flex;
    align-items: center;
    gap: 1rem;


    `

export const ActionButton = styled.div`
  width: 100px;
  height: 27px;
  padding-left: 10px;
  border: 1px solidrgba(206, 206, 206, 0.5);
  cursor: pointer;
  align-content: center;

  &:hover {
    background-color: #cecece;
  }
`;

export const SectionContainer = styled.div`
  border: 1px dotted #ccc;
  border-radius: 6px;
  padding: 12px 16px;
  margin-bottom: 16px;
  zoom: 0.85;
`;

export const TitleContainer = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-between;
`;

export const SectionTitle = styled.h4`
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
`;

export const SelectContainer = styled.div`
  display: flex;
  flex-direction: column;
`;

export const Label = styled.label`
  font-size: 12px;
  color: #333;
  margin-bottom: 6px;
`;

export const SelectAllWrapper = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
  gap: 6px;
`;

export const ToggleContainer = styled.div`
  display: flex;
  background-color: #fff;
  border: 1.5px solid #d08ba5;
  border-radius: 999px;
  overflow: hidden;
  width: fit-content;
  padding: 2px;
  gap: 12px;
  font-size: 8px;
`;

export const ToggleButton = styled.button<{ active: boolean }>`
  padding: 3px 14px;
  border: none;
  background-color: ${({ active }) => (active ? "#f1d2e0" : "transparent")};
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

export const ModalContainer = styled.div`
  width: 45vw;
  height: fit-content;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 0;
  max-height: 90vh;
  flex-direction: column;
`;

export const ModalContent = styled.div`
  width: 95%;
  height: 80%;
  background-color: #fff;
  padding: 20px;
  //   border-radius: 8px;
  //   box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
`;

export const Section = styled.div`
  margin-bottom: 20px;
  border-top: 1px solid #e0e0e0;
  padding: 12px;
  border-radius: 8px;
  overflow-y: auto;
  box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
`;

export const SectionHeader = styled.div`
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 8px;
  display: flex;
  padding-bottom: 4px;
  border-bottom: 1px solid #e0e0e0;
  justify-content: space-between;
  cursor: pointer;
`;

export const RolesGrid = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 5px 20px;
`;

export const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
`;

export const ButtonSection = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  gap: 20px;
  width: 100%;
`;

type ScrollContainerProps = {
    isScroll: boolean;
  };
  
  export const Container = styled.div`
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding: 4px;
    overflow: hidden;
    width: 100%;
    gap: 5px;
    height: 100%
  `;
  export const scrollAnimation = keyframes`
    0% {
      transform: translateX(0%);
    }
    100% {
      transform: translateX(-100%);
    }
  `;
  
  export const ScrollWrapper = styled.div`
    overflow: hidden;
    width: 100%;
  `;
  
  export const ScrollContainer = styled.div<ScrollContainerProps>`
    display: flex;
    gap: 8px;
    width: 100%;
    will-change: transform;
  
    ${({ isScroll }) =>
      isScroll &&
      css`
        animation: ${scrollAnimation} 30s linear infinite;
  
        &:hover {
          animation-play-state: paused;
        }
      `}
  `;
  
  export const RoleTab = styled.div`
    padding: 2px 6px;
    background-color: rgb(44, 43, 43);
    color: white;
    border-radius: 12px;
    white-space: nowrap;
    font-size: 8px;
  `;

  export const ImageSpan = styled.span`
    width: 10%;
    height: 100%;
  `;
  
  export const RoleTile = styled.div`
    background-color: rgb(44, 43, 43);
    color: white;
    padding: 4px 6px;
    border-radius: 8px;
    font-size: 10px;
    text-align: center;
    white-space: nowrap;
  `;
  
  export const ContainerDrop = styled.div`
    width: 240px;
    font-size: 11px;
    border: 1px solid #ccc;
    padding: 8px;
    background: white;
  `;
  
  export const CheckboxRow = styled.div`
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-weight: 420;
  
    &:hover{
      font-size: 12px;
      font-weight: 400;
    }
  `;
  
  export const CategoryHeader = styled.div`
    font-weight: bold;
    padding: 6px;
    margin-top: 6px;
    display: flex;
    justify-content: space-between;
    cursor: pointer;
    &:hover {
      background: #f0f0f0;
      font-size: 12.5px;
    }
  `;
  
  export const SubItem = styled.div`
    padding-left: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 4px 0;
    &:hover {
      background: #f0f0f0;
  
      }
  `;
  
  export const BottomButtons = styled.div`
    display: flex;
    justify-content: space-between;
    margin-top: 16px;
  `;
  
  export const OptionsSection = styled.div`
    max-height: 200px;
    overflow-y: auto;
    margin-top: 8px;
    border-top: 1px solid #eee;
    padding-top: 8px;
  `
  