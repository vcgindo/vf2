import { useTranslation } from "react-i18next";
import {
  WrapperChart,
  ChartLeft,
  ChartRight,
  WrapperColumnRed,
  WrapperColumnGreen,
  WrapperColumnWhite,
  TextColumn,
} from "./styles";

const ColumnChart = ({ themeUi }: any) => {
  const { t } = useTranslation();

  return (
    <WrapperChart>
      <ChartRight>
        <ChartLeft themeUi={themeUi}>{t("columnChart.textLeft")}</ChartLeft>
        <WrapperColumnRed themeUi={themeUi}>
          <TextColumn>{t("columnChart.red")}</TextColumn>
        </WrapperColumnRed>
        <WrapperColumnGreen themeUi={themeUi}>
          <TextColumn>{t("columnChart.green")}</TextColumn>
        </WrapperColumnGreen>
        <WrapperColumnWhite themeUi={themeUi}>
          <TextColumn>{t("columnChart.white")}</TextColumn>
        </WrapperColumnWhite>
      </ChartRight>
    </WrapperChart>
  );
};

export default ColumnChart;
