import styled from 'styled-components'

export const Wrapper = styled.div`
    height: 85%;
    margin-left: 2rem;
    margin-top: 2rem;
    & > .ag-theme-alpine{
        height: 100%;
    }
    & div[data-testid="vf_pagination"]{
        padding: 0 !important;
        // margin-top: -20px !important;
    }

`

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

export const VFChilWrapper = styled.div`
 width: 100%;
 height: 100%;
 & .ag-theme-alpine{
 --ag-header-background-color: rgb(255, 255, 255) !important;
 --ag-header-foreground-color:rgb(0,0,0) !important;
 }
 & .ag-theme-noir-fusion{
  --ag-header-background-color: rgb(255, 255, 255) !important;
  --ag-header-foreground-color:rgb(0,0,0) !important;
 }
}
`