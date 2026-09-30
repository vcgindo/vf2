import styled from 'styled-components';

export const FilterGroup = styled.div`
    min-height:80px;
    background-color:white;
    display:flex;
    align-items: flex-start;
    gap:20px;
    padding: 0;
    margin-top: -10px;
    margin-left: 5px;
    margin-right: 5px;
    flex-wrap: wrap;
`

export const FilterColumn = styled.div`
  flex: 1;
  flex-direction: column;
  min-width: 250px;
  max-width: none;
`;

export const MultiSelectCheckBoxComponent = styled.div<{theme:string}>`
margin-bottom:16px;
display:flex;
justify-content:flex-start;
align-items:center;
gap:6px;
accent-color:${(props)=>props.theme==="REGALBLAZE"?"#C7810E":"#82104C"};
`

export const FilterTitle = styled.h3<{ subTitle?: boolean }>`
  margin: 0 0 0.5rem 0;
  color: ${props => props.subTitle ? '#666' : '#333'};
  font-weight: ${props => props.subTitle ? '400' : '500'};
  font-size: ${props => props.subTitle ? '13px' : '14px'};
  font-style: ${props => props.subTitle ? 'italic' : 'normal'};
  font-family: 'Roboto', sans-serif;
`;

export const DropDownRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;          // Reduced gap to save space
  flex-wrap: nowrap;  
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 0.5px;
`;
export const DropDownWrapper = styled.div`
    flex: 1;           
    min-width: 0px;      
    height: 50px;
    box-sizing: border-box;
`

export const TextWrapper = styled.div`
    display: flex;
    font-family:Roboto;
    font-weight:500;
    font-size:14px;
    line-height:24px;
    margin: 0 0 0.5rem 0;
    align-items:center;
`

export const IconWrapper = styled.div<{ disabled?: boolean; theme_ui: string; }>`
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8px;
  margin-bottom: 11px;
  gap: 8px;
  
  img {
    display: block;
    height: 24px;
    width: 24px;
    cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
    opacity: ${props => props.disabled ? '0.3' : '0.7'}; // Reduced opacity further for disabled state
    padding: 4px;
    border: 1px solid ${props => props.disabled ? '#757575' : 'transparent'};
    border-radius: 4px;
    background-color: ${props => props.disabled ? '#9e9e9e' : 'transparent'};
    box-sizing: content-box;
    transition: all 0.2s ease;
    
    &:hover {
      background-color: ${props => props.disabled ? '#9e9e9e' : 'white'};
      border: 1px solid ${props => props.disabled ? '#757575' : props.theme_ui === "REGALBLAZE" ? "#FCA311" : '#B93B7E'};
      opacity: ${props => props.disabled ? '0.3' : '1'}; // Keep low opacity for disabled even on hover
    }
    
    &:active {
      border-color: ${props => props.disabled ? '#757575' : props.theme_ui === "REGALBLAZE" ? "#FCA311" : '#B93B7E'};
    }
  }
`;

export const CheckboxWrapper = styled.div`
  border: 1px solid #c7c0c0ff;
  border-radius: 10px;
  min-height: 40px;
  width: auto;
  padding: 2px 10px;
  font-size: 14px;
  font-family: Roboto, sans-serif;
  display: flex;
  align-items: center;
  background-color: white;
  
  
  &:hover {
    border-color: #BC3D80;
    box-shadow: 0 2px 4px rgba(188, 61, 128, 0.1);
  }
  
  &:focus-within {
    border-color: #BC3D80;
    border-width: 2px;
    outline: none;
  }
`;

export const InputField = styled.input`
  width: 100%;
  height: 40px;
  border-radius: 12px;
  border: 2.5px solid #000000;
  padding: 0.75rem;
  border: 1px solid #ddd;
  background: white;
  font-size: 14px;
  transition: border-color 0.2s ease;

  &:focus {
    outline: none;
    border-color: #B93B7E;
    box-shadow: 0 0 0 2px rgba(185, 59, 126, 0.1);
  }

  &::placeholder {
    color: #999;
  }
`;

export const SelectField = styled.select`
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  transition: border-color 0.2s ease;

  &:focus {
    outline: none;
    border-color: #B93B7E;
    box-shadow: 0 0 0 2px rgba(185, 59, 126, 0.1);
  }
`;

export const NoFiltersContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  height: 100%;
  width: 100%;
  margin-top: -70px;
`;

export const NoFiltersIcon = styled.div`
  margin-bottom: 24px;
  
  svg {
    transition: transform 0.3s ease;
    
    &:hover {
      transform: scale(1.05);
    }
  }
`;

export const NoFiltersSubText = styled.div<{ theme_ui: string }>`
  font-size: 14px;
  color: #000000;
  line-height: 1.4;
  max-width: 300px;
  font-family: 'Segoe UI', Roboto, Arial, sans-serif;
`;