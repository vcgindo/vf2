import styled from 'styled-components'

export const BTRTableWrapper = styled.div`
    display:flex;
    flex-direction:column;
    height:400px;
    width:100%;
    margin-top:20px;
    margin-bottom:20px;
    height:100%;
`
export const BTRAllomentSection = styled.div`
    display:flex;
    flex-direction:column;
    height:100%;
    max-height:100%;
`

export const HorizontalViewWrapper = styled.div`
    //   display:flex;
      width:100%;
`

export const SCChartContainer = styled.div<{ height?: string }>`
    padding:5px;
    border-radius:12px;
    background: #FFFFFF 0% 0% no-repeat padding-box;
    // box-shadow: -5px 5px 25px #86868633;
    box-shadow: rgba(0, 0, 0, 0.1) 0px 4px 12px;
    margin: 20px;
    // height:547px;
    height:${props => props.height ? props.height : 'auto'}
`

export const SCHorizontalDivider = styled.hr`
    width:100%;
    border: none;
    border-top:1px solid #B2B2B2;
`
export const BPRColorCellRendererWrapper = styled.div`
    display:flex;
    justify-content:center;
    align-items:center;
    width: 100%;
    height: 90%;
    box-shadow: 0px 6px 12px #8D8D8D29;
    border-radius: 4px;
    position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`
