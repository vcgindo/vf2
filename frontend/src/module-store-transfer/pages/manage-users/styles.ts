import styled from 'styled-components'
import * as globalStyles from '../../../styles/global'
import * as GridSystem from '../../../styles/gridSystem'

export const SCProfileOverView = styled.div`
  background: ${globalStyles.white};
  margin-bottom: 20px;
  border-radius: 6px;
`

export const SCProfileOverViewCol = styled.div`
  background: ${globalStyles.white};
  margin-bottom: 20px;
  border-radius: 6px;
  width: 47%;
`

export const SCProfilePad = styled.div`
  display: flex;
  align-items: center;
  padding: 28px 50px;
`

export const SCProfileImg = styled.img`
  border-radius: 6px;
  border: 3px solid ${globalStyles.white};
  box-shadow: 0px 10px 20px #c4c8d066;
  width: 100%;
  max-width: 95px;
`

export const SCProfileName = styled.span`
  font-size: 1.8rem;
  font-weight: 500;
  padding-left: 30px;
`

export const SCProfileTab = styled.div`
  padding: 0 50px;
`

export const SCOverviewTab = styled.span`
  font-size: 1.8rem;
  font-weight: 500;
  margin-right: 40px;
  color: ${globalStyles.mainColor};
  border-bottom: 1px solid ${globalStyles.mainColor};
  cursor: pointer;
`

export const SCSubTitleBox = styled.div`
  border-bottom: 1px solid ${globalStyles.secondaryColor};
`

export const SCSubTitlePad = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 17px 50px;
`

export const SCSubTitlePadItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  column-gap: 2rem;
`

export const SCItemBtn = styled.div`
  width: 164px;
  height: 50px;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    width: 150px;
    height: 40px;
  }
`

export const SCSubTitleSpan = styled.span`
  font-size: 2rem;
  font-weight: 500;
  line-height: 2.6rem;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`
