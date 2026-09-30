import { useTranslation } from "react-i18next";
import { SwapperText, TextInPage, TextAllPage } from "./styles";

interface SelectAllPageProps {
  inPage: number;
  total: number;
  themeUi: string;
  handleAction: () => void;
  isCheckAllPage: boolean;
}

const SelectAllPage = ({
  inPage,
  total,
  themeUi,
  handleAction,
  isCheckAllPage,
}: SelectAllPageProps) => {
  const { t } = useTranslation();

  return (
    <SwapperText>
      <TextInPage>
        {isCheckAllPage
          ? t("pendingISTRequests.selectCheckAll.textAllPageSelected", {
              total: total,
            })
          : t("pendingISTRequests.selectCheckAll.textInPage", {
              in_page: inPage,
            })}
      </TextInPage>
      <TextAllPage themeUi={themeUi} onClick={handleAction}>
        {isCheckAllPage
          ? t("pendingISTRequests.selectCheckAll.clearSelection")
          : t("pendingISTRequests.selectCheckAll.textAllPage", {
              total: total,
            })}
      </TextAllPage>
    </SwapperText>
  );
};

export default SelectAllPage;
