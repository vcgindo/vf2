import { useEffect, useState } from "react";
import {
  listColorTheme,
  SCWrap,
  SCWrapTop,
  SCTopText,
  SCClose,
  SCWrapContent,
  SCWrapItem,
  SCInputRadio,
  SCItemText,
  SCListColor,
  SCColor,
  SCIconClose,
  SCButton,
  SCWrapItemLeft
} from "./styles";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import LoadingSpinner from "../../../components/commons/LoadingSpinner";
import { useChangeThemeUser } from "../../../services/profile";
import OverlayPage from "../../../components/commons/OverlayPage";
import { useUserData } from "../../../context";
import { useTranslation } from "react-i18next";

const NavbarRight = ({
  isOpenNavbarRight,
  setIsOpenNavbarRight,
  setColorTheme,
  isLoadSpinner,
  setIsLoadSpinner
}: any) => {
  const { t } = useTranslation();
  const handleClose = () => {
    setIsOpenNavbarRight(false);
  };

  const { mutateAsync: mutateChangeTheme } = useChangeThemeUser();
  const { user, changeColorTheme } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const [listTheme, setListTheme] = useState<any>(listColorTheme);

  useEffect(() => {
    const newListColorTheme = listColorTheme.map((item: any) => {
      if (themeUi === item.textColor) {
        item.status = true;
      }
      return item;
    });
    setListTheme(newListColorTheme);
    setColorTheme(themeUi);
  }, []);

  const handleClick = (index: number) => {
    const newListColorTheme: any = [...listColorTheme];
    newListColorTheme.forEach((item: any) => {
      item.status = false;
    });
    newListColorTheme[index].status = true;

    setListTheme(newListColorTheme);
  };

  const handleChangeColor = () => {
    setIsLoadSpinner(true);
    const getTheme = listTheme.filter((item: any) => item.status);

    const formData = {
      theme_ui: getTheme[0].textColor,
    };
    setTimeout(() => {
      mutateChangeTheme(formData, {
        onSuccess: (res: any) => {
          if(res?.status === 400) {
            notifyError(res?.response?.msg)
          } else {
            notifySuccess(res?.data?.msg);
          }
          setIsLoadSpinner(false);
        },
        onError: (error: any) => {
          console.log("error", error);
          setIsLoadSpinner(false);
          notifyError(error.msg);
        },
      });
      changeColorTheme(getTheme[0].textColor);
      setColorTheme(getTheme[0].textColor);
    }, 500);
  };

  return (
    <div>
      <SCWrap isOpenNavbarRight={isOpenNavbarRight}>
        <SCWrapTop>
          <SCTopText>{t('theme.chooseThemeColor')}</SCTopText>
          <SCClose onClick={handleClose}>
            <SCIconClose src="/assets/img/navRight/icon_close.svg" />
          </SCClose>
        </SCWrapTop>
        <SCWrapContent>
          {listTheme.map((item: any, index: number) => (
            <SCWrapItem key={index} onClick={() => handleClick(index)} isActive={item.status}>
              <SCWrapItemLeft>
                <SCInputRadio
                  type="radio"
                  checked={item.status}
                  readOnly
                  onClick={() => handleClick(index)}
                  themeUi={themeUi}
                />
                <SCItemText>{item.title}</SCItemText>
                <div style={{ margin: "0 10px" }}></div>
              </SCWrapItemLeft>
              <SCListColor>
                {item.colorTheme.map((color: any) => (
                  <SCColor color={color} key={color} />
                ))}
              </SCListColor>
            </SCWrapItem>
          ))}

          <div style={{display:'flex',justifyContent:'flex-end'}}>
            <SCButton onClick={handleChangeColor} themeUi={themeUi}>{t('theme.applyTheme')}</SCButton>
          </div>
        </SCWrapContent>
      </SCWrap>
      {isOpenNavbarRight && <OverlayPage onClick={handleClose} />}
      {isLoadSpinner && <LoadingSpinner />}
    </div>
  );
};

export default NavbarRight;
