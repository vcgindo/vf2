import styled from 'styled-components'


export const SeasonalityGrapCellRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    justify-content:center;
    align-items:center;
    cursor:pointer;
`



export const SeasonalityColorCellRendererWrapper = styled.div<{stateColor:string}>`
    width:8px;
    height:100%;
    position:absolute;
    left:0px;
    background-color:${(props)=>props.stateColor};
`