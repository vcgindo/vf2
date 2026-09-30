import styled,{keyframes} from 'styled-components'

const fadeIn = keyframes`
    from{
        opacity:0;
    }
    to{
        opacity:1;
    }
`

export const Icon = styled.img`
    height: 60px;
    cursor:pointer;
    display: flex;
`
export const TextWrapper = styled.div`
    position: absolute;
    color:white;
    max-width:700px;
    z-index:200;
    animation:${fadeIn} 0.4s ease-in-out;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 2px;
    border-radius: 4px;
`

export const Tag = styled.div`
  font-size: 16px;
  font-family: Roboto;
  font-weight: 900;
  line-height: 24px;
  list-style: circle;
  color: white;
  background: rgb(254, 162, 54);
  width: 150px;
  text-align: center;
  border-radius: 8px;
  padding: 5px 20px;
`