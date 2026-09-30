import { useTranslation } from "react-i18next";
import { LogoIcon, WelcomeText, LogoVector } from "./styles";


function WelcomeBoard() {
  const { t } = useTranslation();
 
  return (
    <LogoVector>
      <LogoIcon src="/assets/img/auth/VectorFlowLogoWhite.svg" />
      <WelcomeText>{t("loginPage.welcome")}</WelcomeText>
    </LogoVector>
  );
}

export default WelcomeBoard;