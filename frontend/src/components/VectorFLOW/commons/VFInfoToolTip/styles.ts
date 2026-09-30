import styled,{keyframes} from 'styled-components'

const fadeIn = keyframes`
    from{
        opacity:0;
    }
    to{
        opacity:1;
    }
`

export const Wrapper = styled.div`
    position:relative;
    // z-index:200;
`

export const Icon = styled.img`
    width: 15px;
    height: 15x;
    cursor:pointer;
`
export const TextWrapper = styled.ul`
    position:fixed;
    color:white;
    background: #2E2E2E 0% 0% no-repeat padding-box;
    padding-top:10px;
    padding-bottom:10px;
    padding-right:10px;
    border-radius:6px;
    max-width:700px;
    z-index:200;
    animation:${fadeIn} 0.3s ease-in-out;
`

export const Text = styled.li`
    font-size:16px;
    font-family:Roboto;
    font-weight:400;
    line-height:30px;
    list-style:circle;
`