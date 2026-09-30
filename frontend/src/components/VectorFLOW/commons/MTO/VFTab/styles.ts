import styled from 'styled-components'
import * as globalStyles from '../../../../../styles/global'
import * as GridSystem from '../../../../../styles/gridSystem'



export const SCTabArea = styled.div`
  display: flow-root;
  position: relative;
  height:100%;
`


export const SCTabHeader = styled.div`
  display: flex;
  align-items: center;
  place-content: space-between;
  overflow: overlay;


  &::-webkit-scrollbar{
    width: 7px;
    height:5px;       
  }

  &::-webkit-scrollbar-track{
      border-radius: 30px;
      opacity: 1;
  }

  &::-webkit-scrollbar-thumb{
      width: 7px;
      /* UI Properties */
      background: #CBCBCB 0% 0% no-repeat padding-box;
      box-shadow: 0px 6px 9px #41414129;
      border-radius: 30px;
      opacity: 1;
  }
`

export const SCTabHeaderLeft = styled.div`
  display: flex;
  position: relative;
  z-index: 1;
`

export const SCTabHeaderRight = styled.div`
  display: flex;
  align-items: center;

  .view-mode {
    width: 2.6rem;
    margin-left: 1rem;
    cursor: pointer;
  }
`

export const SCTabView = styled.p`
  font-size: 1.8rem;
  color: #292c2e;
  margin-left: 10px;
`


export const SCTabButton = styled.div<{
  status: string
  zIndex: number
  marLeft: true | false
  themeUi: string
}>`
  color: ${(props) => (props.status==='active' ? '#FFFFFF' : '')};
  opacity: 1;
  min-height: 60px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.6rem;
  position: relative;
  z-index: ${(props) => props.zIndex};
  margin-left: ${(props) => (props.marLeft ? '-1.5em' : '0')};
  padding-left: ${(props) => (props.marLeft ? '1.5em' : '0')};

  cursor:default ;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.2rem;
    height: 3.5vw;
    margin-left:${(props) => (props.marLeft ? '-2.5em' : '0')};
  }
  
  // pointer-events:${(props)=>props.status === 'completed' ? 'none' : 'all'};

  ::before {
    border: 0.5px solid #cccccc;
    content: "";
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: -1;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    // background: ${(props) => (props.status === 'active' ? globalStyles.chooseThemeColor[props.themeUi]?.color5 : props.status==='completed' ? 'yellow' : 'blue')} 

      background: ${(props) =>
        props.status === "active"
          ? props.themeUi==="REGALBLAZE"?"transparent linear-gradient(261deg, #FCA311 0%, #CB830E 100%) 0% 0% no-repeat padding-box":'linear-gradient(74deg, rgb(130, 15, 76) 0%, rgb(188, 61, 129) 100%) 0% 0% no-repeat padding-box padding-box transparent' : props.status==='completed' 
          ? "#898989 0% 0% no-repeat padding-box;"
        :'white'};
        no-repeat padding-box;
    box-shadow: 0px 5px 25px #9d9d9d29;
    transform: scale(1.2, 1.3) perspective(0.5em) rotateX(2.5deg);
    transform-origin: bottom left;
  }
`
export const SCTabContent = styled.div`
  margin-left: 60px;
  margin-right: 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`

export const SCTabTitle = styled.p<{status:string}>`
  margin-right: 50px;
  color: ${(props) => (props.status === 'active' || props.status==='completed' ? '#FFFFFF' : '#6C696A')};
  font-family:'Roboto';
  font-weight:500;
  font-size:16px;
  white-space:nowrap;
`

export const SCTabBody = styled.div`
  display: flex;
  flex-direction: column;
  height:100%;
  background: #ffffff 0% 0% no-repeat padding-box;
  border: 0.5px solid #cccccc;
  border-radius: 0px 15px 15px 15px;
  padding-bottom:10px;
`

