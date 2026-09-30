import styled from "styled-components";
import * as globalStyles from "../../../../../../styles/global";


export const FilterWrapper = styled.div`
  height: 78vh;
  width: 75vw;
  background-color: white;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
`;

export const FilterHeaderWrapper = styled.div`
  height: 35px;
  width: 100%;
  border-bottom: 1px solid #ccc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  align-items: center;
  background: white;
  font-size: 1.2rem;
  font-weight: 500;
`;

export const FilterHeaderTitle = styled.div`
  font-size: 1.2rem;
  font-weight: 500;
  display: flex;
  gap: 8px;
  align-items: center;
`;
export const CloseButton = styled.button`
  background: none;
  border: none;
  font-size: 2.6rem;
  font-weight: 200px;
`;

export const FilterContent = styled.div`
  height: 80%;
  width: 100%;
  overflow: auto;
`;

export const FilterTabLayout = styled.div`
    display: flex;
    gap: 26px;
    padding: 16px 40px;
    width: fit-content;
    height; fit-content;
`;

export const FilterTab = styled.div`
  padding: 8px 0;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  width: 220px;
  border: 1px solid #ccc;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease-in-out;
  &:hover {
    transform: scale(1.01);
  }
  &.active {
    background: #9c0d64;
    color: white;
  }
`;

export const FilterTabHeader = styled.div`
  font-size: 1.1rem;
  font-weight: 500;
  padding: 4px 8px 4px 16px;
  text-align: left;
  border-bottom: 1px solid #ccc;
`;

export const FilterSearchBar = styled.input`
  width: 90%;
  margin: 12px auto;
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 18px;
  font-size: 1rem;
  background: #f9f9f9;
  display: block;
  &:focus {
    outline: none;
    border-color: #9c0d64;
    box-shadow: 0 0 5px rgba(156, 13, 100, 0.5);
  }
`;

export const FilterList = styled.div`
  max-height: 220px;
  overflow-y: auto;
  margin-top: 8px;
  padding: 0 8px;
`;

export const FilterBottomSection = styled.div`
  width: 100%;
  display: flex;
  padding: 12px 20px;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #ccc;
`;

export const FilterBottomLeft = styled.div``;
export const FilterBottomRight = styled.div`
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
`;

export const Checkbox = styled.input<{theme:string}>`
    width: 2.5rem !important;
    height: 2.5rem !important;
    border-radius: 2px;
    border: 2px solid rgb(148, 154, 171);
    background-color: white;
    appearance: none;
    cursor: pointer;
    &:checked {
        background-color: ${props => globalStyles.chooseThemeColor[props.theme]?.color4};
        border-color: ${props => globalStyles.chooseThemeColor[props.theme]?.color4};
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        background-image: url(/assets/img/mto/dueDateQuotation/checked.svg);
    }
`



export const DateRow = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
`;

export const DateWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 8px;
  flex: 1;
`;

export const DateLabel = styled.label`
  font-size: 0.9rem;
  font-weight: 500;
`;

Checkbox.defaultProps = {
    type: "checkbox"
}
