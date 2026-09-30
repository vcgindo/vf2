import styled from 'styled-components';

export const ModalContent = styled.div`
  padding: 0;
  background: #fff;
  margin-top: 16px;
  border-radius: 0px 0px 12px 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
`;

export const FilterLayout = styled.div`
  display: flex;
  flex: 1;
  min-height: 680px;
  min-width: 980px;
  overflow: hidden;
`;

export const SidebarSection = styled.div`
  width: 180px;
  background: #f8f9fa;
  border-right: 1px solid #e9ecef;
  padding: 1rem 0;
  display: flex;
  flex-direction: column;
`;

export const SidebarItem = styled.div<{ active: boolean; theme_ui: string }>`
  padding: 0.875rem 1.5rem;
  cursor: pointer;
  background: ${props => props.active ? props.theme_ui === 'REGALBLAZE' ? '#fca2113d' : '#fce4f0' : 'transparent'};
  color: ${props => props.active
    ? (props.theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80")
    : '#000000ff'};
  transition: all 0.2s ease;
  font-size: 15px;
  font-weight: ${props => props.active ? '480' : '400'};
  margin-right: ${props => props.active ? '-1px' : '0'};

  &:hover {
    background: ${props => props.active ? props.theme_ui === 'REGALBLAZE' ? '#fca2111b' : '#fce4f0'  : '#e9ecef'};
    color: ${props => props.theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80"};
  }
`;

export const ContentSection = styled.div`
  flex: 1;
  padding: 1.5rem 2rem;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
`;

export const FooterSection = styled.div`
  background: #ffffff;
  padding: 0.5rem 1.6rem;
  border-top: 1px solid #e9ecef;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  box-shadow: 0px -2px 16px -1px rgba(0, 0, 0, 0.1);
`;

export const FooterButtons = styled.div`
  display: flex;
  gap: 1.5rem;
  justify-content: flex-end;
  align-items: center;
`;
