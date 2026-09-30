import {
  SCWrap,
  SCLeft,
  SCRight,
  SCWrapLogo,
  SCLogo,
  SCWrapBreadcrumb,
  SCBreadCrumb,
  SCImg,
  SCTxt,
  SCImgLink,
  SCVerticalPartitions,
} from "./styles";
import { useUserData } from "../../../context";
import BreadCrumb from "../BreadCrumb";
import { useState } from "react";
import { ModalReportIssue, ModalSuccess } from "../../index";
import {  useNavigate} from "react-router-dom";


const NavbarTop = ({
  setIsOpenNavbarRight,
  setIsLoadSpinner,
  isLoadSpinner,
}: any) => {
  const { user } = useUserData();
  const colorTheme = user?.user?.theme_ui;
  const [isOpenReportIssue, setIsOpenReportIssue] = useState<boolean>(false);
  const [isOpenReportSuccess, setIsOpenReportSuccess] =
    useState<boolean>(false);

  const openNavbarRight = () => {
    setIsOpenNavbarRight(true);
  };

  const openReportIssue = () => {
    setIsOpenReportIssue(true);
  };

  const onCloseReportIssue = () => {
    setIsOpenReportIssue(false);
  };

  const onCloseModalSuccess = () => {
    setIsOpenReportSuccess(false);
  }

  const navigate = useNavigate();

  const handleClick = () => {
    navigate("/landing-page"); // Navigating to the desired route
  };

  return (
    <>
      <SCWrap colorTheme={colorTheme}>
        <SCLeft>
          <SCWrapLogo>
            <SCLogo
              src={
                colorTheme === "PUREELEGANCE"
                  ? "/assets/img/header/VectorFlowLogoBlackNew.svg"
                  : "/assets/img/header/VectorFlowLogoWhite.svg"
              }
              onClick={handleClick}
            />
          </SCWrapLogo>

          <SCVerticalPartitions />

          <SCWrapBreadcrumb>
            <SCBreadCrumb colorTheme={colorTheme}>
              <BreadCrumb />
            </SCBreadCrumb>
          </SCWrapBreadcrumb>
        </SCLeft>
        <SCRight>
            <SCImg
              src={`/assets/img/header/${
                colorTheme === "REGALBLAZE"
                  ? "notifications_yellow"
                  : "notifications_purple"
              }.svg`}
            />
          <SCImg
            src="/assets/img/header/icon_theme_colors.svg"
            onClick={openNavbarRight}
          />
          <SCImg
            src="/assets/img/header/report-bug.svg"
            onClick={openReportIssue}
          />

          <SCImgLink to="/profile">
            <SCImg src="/assets/img/header/profile_new.svg" />
          </SCImgLink>
          <SCTxt colorTheme={colorTheme}>{user?.user?.name}</SCTxt>
        </SCRight>
      </SCWrap>
      {isOpenReportIssue && (
        <ModalReportIssue
          openModal={isOpenReportIssue}
          closeModal={onCloseReportIssue}
          setIsLoadSpinner={setIsLoadSpinner}
          isLoadSpinner={isLoadSpinner}
          setIsOpenReportSuccess={setIsOpenReportSuccess}
        />
      )}
      <ModalSuccess
        openModal={isOpenReportSuccess}
        closeModal={onCloseModalSuccess}
        setIsOpenReportIssue={setIsOpenReportIssue}
        colorTheme={colorTheme}
      />
    </>
  );
};

export default NavbarTop;
