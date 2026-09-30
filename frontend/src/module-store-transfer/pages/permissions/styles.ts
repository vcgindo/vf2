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
  padding: 34px 50px 20px 50px;
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

export const SCSubTitleSpanItem = styled.div`
  display: flex;
  width: 100%;
`

export const SCOverviewInfo = styled.div`
  padding: 15px 50px 24px 50px;
  display: flex;
  width: 100%;
  gap: 5rem;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    gap: 2rem;
  }
`

export const SCOverviewInfoPermis = styled.div`
  padding: 0px 50px 24px 50px;
  display: block;
  width: 100%;
`

export const SCOverviewItem = styled.div<{ checkBorderBottom: boolean }>`
  display: flex;
  align-items: center;
  min-width: 50%;
  padding: 15px;
  background: #f8f8f8 0% 0% no-repeat padding-box;

  :nth-child(1) {
    border-bottom: ${(props) =>
      props.checkBorderBottom
        ? `1px dashed ${globalStyles.secondaryColor}`
        : ''};
  }
  :nth-child(2) {
    border-bottom: ${(props) =>
      props.checkBorderBottom
        ? `1px dashed ${globalStyles.secondaryColor}`
        : ''};
  }
`

export const SCOverviewItemTitle = styled.div`
  font-size: 1.6rem;
  color: #000000;
  font-weight: 500;
  flex: 0 0 100%;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.4rem;
  }
`

export const SCOverviewItemPerTitle = styled.div`
  font-size: 2rem;
  min-width: 10rem;
  color: #000000;
  font-weight: 300;
  align-items: center;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    min-width: 8rem;
  }
`

export const SCOverviewItemPerTitleLoca = styled.div`
  font-size: 2rem;
  min-width: 17rem;
  color: #000000;
  font-weight: 300;
  align-items: center;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
    min-width: 13rem;
  }
`

export const SCOverviewItemContent = styled.div`
  font-size: 2rem;
  color: #000000;
  font-weight: 500;
  align-items: center;
  margin: 0 10px;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    font-size: 1.6rem;
  }
`

export const SCOverViewSignItem = styled.div`
  display: block;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px dashed ${globalStyles.secondaryColor};
  padding: 16px 0 20px 0;
  :last-child {
    border: unset;
    padding: 16px 0 0 0;
  }
`

export const SCButtonSignIn = styled.button`
  border-radius: 4px;
  color: ${globalStyles.secondaryColor};
  background: ${globalStyles.gray};
  padding: 14px;
  font-size: 2rem;
  width: 192px;
`

export const SCBoxChangePassword = styled.div`
  display: flex;
  align-items: center;
  padding-top: 50px;
`

export const SCChangePasswordLabel = styled.label`
  font-size: 2rem;
  font-weight: 500;
  display: block;
  padding-bottom: 14px;
`

export const SCChangePasswordInput = styled.input`
  background: ${globalStyles.beige};
  height: 36px;
  border-radius: 6px;
  outline: none;
  border: none;
  font-size: 1.8rem;
  padding: 0 16px;
  width: 100%;
`
export const SCChangePasswordBox = styled.div`
  padding-right: 50px;
  flex: 1 0 25%;
`

export const SCChangePasswordFlex = styled.div`
  display: flex;
  align-items: center;
  margin-top: 30px;
`

export const SCChangePasswordSubmit = styled.button`
  font-size: 1.8rem;
  font-weight: 300;
  color: ${globalStyles.white};
  padding: 14px 20px;
  border-radius: 6px;
  background: linear-gradient(180deg, #bc3d81 0%, #820f4c 100%);
`

export const SCChangePasswordCancel = styled.button`
  background: transparent;
  color: #121418;
  font-size: 1.6rem;
  margin-left: 45px;
`

export const SCTabs = styled.div`
  padding: 0 50px;
`

export const SCIconChecked = styled.img`
  margin-right: 15px;
`

export const SCOverviewWrap = styled.div`
  width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  @media (min-width: ${GridSystem.size.laptop}) and (max-width: ${GridSystem
      .size.laptopL}) {
    width: 50%;
  }
`

export const SCOverviewWrapTitle = styled.div`
  font-size: 1.6rem;
  margin-bottom: 10px;
  font-weight:500;
  padding: 1rem 0;
  border-bottom: 1px solid black;
`

export const SCOverviewWrapItem = styled.div<{ checkBackGround: boolean }>`
  display: flex;
  flex-wrap: wrap;
  ${(props) =>
    props.checkBackGround
      ? 'background: #F8F8F8 0% 0% no-repeat padding-box;'
      : ''}
`

export const SCOverviewFlex = styled.div`
  display: flex;
  justify-content: space-between;
`
