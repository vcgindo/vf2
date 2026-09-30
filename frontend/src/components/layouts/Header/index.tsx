import { ISTStatusContext } from '../../../context/ISTStatusContext'
import { useUserData } from '../../../context'
import * as HeaderStyled from './style'
import { useContext, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

interface HeaderProps{
  urlExcludeHeader:Array<string>
}

const Header = (props:HeaderProps) => {

  const {
    urlExcludeHeader
  } = props

  const { t } = useTranslation()
  const { user } = useUserData()
  const themeUi = user?.user?.theme_ui;
  const [isHideLogo, setIsHideLogo] = useState<boolean>(true);
  let timeoutId: any;

  const renderNamePage = () => {
    if (location.pathname === '/profile') {
      if (user.user.is_admin || user?.roles?.permission?.includes('IST Admin')) {
        return <span>{t('header.userAdministration')}</span>
      } else {
        return <span>{t('header.myProfile')}</span>
      }
    }
  }

  const {
    currentAction,
    setCurrentAction,
    setExportView,
    currentViewName,
    currentViewCount,
    currentDataCount
  } = useContext(ISTStatusContext)

  const hideLogo = () => {
    setIsHideLogo(false);
  }

  useEffect(() => {
    timeoutId = setTimeout(() => {
      hideLogo();
    }, 3000);

    return () => clearTimeout(timeoutId);
  }, []);

  const onMouseEnterLogo = () => {
    setIsHideLogo(true);
    clearTimeout(timeoutId);
  }

  const onMouseLeaveLogo = () => {
    timeoutId = setTimeout(() => {
      hideLogo()
    }, 300);
  }
 
const CLIENT_LOGO_PATH = "/client/logo.svg";

  
  const CLIENT_NAME = user?.config_data?.CLIENT_NAME
 

  const renderHeader = () => {
    if (location.pathname === '/ist-status') {
      return (
        <>
          <HeaderStyled.SCHeaderBoxIst>
            <HeaderStyled.SCHeaderText>
              {t('header.ISTStatus')}{' '}
              {currentDataCount > 0 && <HeaderStyled.SCHeaderSubTextIst>
                ({currentViewName})
              </HeaderStyled.SCHeaderSubTextIst>}{' '}
            </HeaderStyled.SCHeaderText>
            {currentViewCount > 0 && currentDataCount > 0 && (
              <HeaderStyled.SCHeaderContent>
                <HeaderStyled.SCExportAllBox
                  onClick={() => {
                    setExportView(true)
                  }}
                >
                  <HeaderStyled.SCExportAllBoxButton>
                    <img src="/assets/img/forced/excel.png" alt="and" />
                    <HeaderStyled.SCExportAllBoxSpan>
                      {t('header.exportAllBtn')}
                    </HeaderStyled.SCExportAllBoxSpan>
                    <img src="/assets/img/forced/export.svg" alt="and" />
                  </HeaderStyled.SCExportAllBoxButton>
                </HeaderStyled.SCExportAllBox>
                {currentAction === 'view' && (
                  <HeaderStyled.SCHeaderButtonIst
                    onClick={() => {
                      setCurrentAction('edit')
                    }}
                    themeUi={themeUi}
                  >
                    {t('header.editBtn')}
                  </HeaderStyled.SCHeaderButtonIst>
                )}
                {currentAction === 'edit' && (
                  <HeaderStyled.SCHeaderButtonIstDelete
                    onClick={() => {
                      setCurrentAction('deleting')
                    }}
                  >
                    {t('header.deleteBtn')}
                  </HeaderStyled.SCHeaderButtonIstDelete>
                )}
                {currentAction === 'edit' && (
                  <HeaderStyled.SCHeaderButtonIst
                    onClick={() => {
                      setCurrentAction('saving')
                    }}
                    themeUi={themeUi}
                  >
                    {t('header.saveBtn')}
                  </HeaderStyled.SCHeaderButtonIst>
                )}
                {currentAction === 'saving' && (
                  <HeaderStyled.SCHeaderButtonIstSaving>
                    {t('header.savingBtn')}
                  </HeaderStyled.SCHeaderButtonIstSaving>
                )}
                {currentAction === 'deleting' && (
                  <HeaderStyled.SCHeaderButtonIstSaving>
                    {t('header.deletingBtn')}
                  </HeaderStyled.SCHeaderButtonIstSaving>
                )}
              </HeaderStyled.SCHeaderContent>
            )}
          </HeaderStyled.SCHeaderBoxIst>
          <HeaderStyled.SCWrapperImg isHideLogo={isHideLogo} onMouseEnter={onMouseEnterLogo} onMouseLeave={onMouseLeaveLogo} style={{ right: 0, marginTop: "-110px" }}>
            <HeaderStyled.SCImg src="/assets/VectorFlow_black.svg" alt="logo" isHideLogo={isHideLogo} />
          </HeaderStyled.SCWrapperImg>
        </>
      )
    }

    return (
      <>
        {
          !urlExcludeHeader.includes(location.pathname) &&
          <HeaderStyled.SCHeaderBox
            style={{
              position: 'sticky',
              top: 0,
              zIndex: 2,
              paddingTop: 15
            }}
          >
            <HeaderStyled.SCHeaderText>
              {renderNamePage()}
            </HeaderStyled.SCHeaderText>
          </HeaderStyled.SCHeaderBox>
        }
        
        <HeaderStyled.SCWrapperImg isHideLogo={isHideLogo} onMouseEnter={onMouseEnterLogo} onMouseLeave={onMouseLeaveLogo} style={{ display: 'flex', alignItems: 'center' }}>
          {!CLIENT_LOGO_PATH && !CLIENT_NAME &&
            <HeaderStyled.SCImg
              marginLeft={"20px"}
              src="/assets/img/header/VectorFlowLogoBlackNew.svg"
              alt="logo"
              isHideLogo={isHideLogo}
            />
          }
          {!CLIENT_LOGO_PATH && (
            <HeaderStyled.SCImg
            marginLeft={"20px"}
            src="/assets/img/header/VectorFlowLogoBlackNew.svg"
            alt="logo"
            isHideLogo={isHideLogo}
          />
          )
          }
          {CLIENT_LOGO_PATH && (
            <HeaderStyled.SCImg
              src={CLIENT_LOGO_PATH}
              alt="logo"
              isHideLogo={isHideLogo}
              onError={(e: any) => {
                e.currentTarget.src = "/assets/img/header/VectorFlowLogoBlackNew.svg";
              }}
            />
          )}
          {CLIENT_NAME && (
            <HeaderStyled.ClientNameText marginLeft={!CLIENT_LOGO_PATH && "15px"} isHideLogo={isHideLogo}>
              {CLIENT_NAME}
            </HeaderStyled.ClientNameText>
          )}
        </HeaderStyled.SCWrapperImg>
      </>
    )
  }
  

  return <>{renderHeader()}</>
}

export default Header