import styled from 'styled-components'


export const OrderCoverageCellRendererWrapper = styled.div`
    width:100%;
    height:100%;
    display:flex;
    justify-content:center;
    align-items:center;
`

export const CoverageColorBox = styled.div<{color:string}>`
    width:16px;
    height:16px;
    background-color:${props => props.color};
    margin-right:5px;
`