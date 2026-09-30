import styled from 'styled-components'

export const SCButtonOutline = styled.button<{ icons: true | false }>`
  border: 1px solid #929292;
  border-radius: 6px;
  font-size: 1.2rem;
  line-height: 1.6rem;
  padding: 8px 16px;
  margin: 0 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  max-height: 46px;
  background: ${(props) =>
    props.icons
      ? 'linear-gradient(180deg, #BC3D81 0%, #820F4C 100%)'
      : '#F9F9F9'};
  color: ${(props) => (props.icons ? '#fff' : '#929292')};
  border: ${(props) => (props.icons ? 'none' : '1px solid #929292')};
`
