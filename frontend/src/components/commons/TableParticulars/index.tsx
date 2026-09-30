import * as NavStyle from "./styles";
import { useTranslation } from "react-i18next";

interface TableParticularsProps {
  listTitle: any;
  themeUi: string;
  listData: any;
  totalData: any;
  pathname: string;
  pcs: boolean;
  setPcs: any;
}
const TableParticulars = ({
  themeUi,
  listTitle,
  listData,
  totalData,
  pathname,
  pcs,
  setPcs,
}: TableParticularsProps) => {
  const { t } = useTranslation();

  const handleClickLeft = () => {
    setPcs(true);
  };

  const handleClickRight = () => {
    setPcs(false);
  };

  const getIcon = () => {
    let iconLeft: string;
    let iconRight: string;
    if (themeUi === "PUREELEGANCE") {
      iconLeft = pcs
        ? "disabled-PureElegance-icon"
        : "enabled-PureElegance-icon";

      iconRight = !pcs
        ? "disabled-PureElegance-icon"
        : "enabled-PureElegance-icon";
    } else {
      iconLeft = pcs ? "disabled-icon" : "enabled-icon";

      iconRight = !pcs ? "disabled-icon" : "enabled-icon";
    }

    return (
      <>
        <NavStyle.BtnLeft
          src={`/assets/img/nav/tableParticulars/${iconLeft}.svg`}
          alt=""
          pcs={pcs}
          onClick={handleClickLeft}
        />
        <NavStyle.BtnRight
          src={`/assets/img/nav/tableParticulars/${iconRight}.svg`}
          alt=""
          pcs={pcs}
          onClick={handleClickRight}
        />
      </>
    );
  };

  return (
    <NavStyle.SCCount pathname={pathname}>
      <NavStyle.SCNavCount themeUi={themeUi}>
        {pathname === "/availability-comparison" && (
          <NavStyle.SCNavCountHeader themeUi={themeUi}>
            <span>
              {pcs
                ? t("availabilityComparison.tableParticulars.inPcs")
                : t("availabilityComparison.tableParticulars.inStyle")}
            </span>
            <span>{getIcon()}</span>
          </NavStyle.SCNavCountHeader>
        )}
        <NavStyle.SCNavCountHeader themeUi={themeUi}>
          {listTitle?.map((item: any, idx: number) => (
            <span key={idx}>{item}</span>
          ))}
        </NavStyle.SCNavCountHeader>
        <NavStyle.SCNavCountList>
          {listData?.map((item: any, idx: number) => (
            <NavStyle.SCNavCountItem key={idx} themeUi={themeUi}>
              {Object.entries(item)?.map((data: any, index: number) => (
                <NavStyle.SCTotalValue
                  key={index}
                  index={index}
                  length={listTitle.length}
                  pathname={pathname}
                >
                  {data[1]}
                </NavStyle.SCTotalValue>
              ))}
            </NavStyle.SCNavCountItem>
          ))}
        </NavStyle.SCNavCountList>
      </NavStyle.SCNavCount>
      <NavStyle.SCNavCountFooter themeUi={themeUi}>
        {Object.entries(totalData)?.map((data: any, index: number) => (
          <NavStyle.SCTotalValue
            key={index}
            index={index}
            length={listTitle.length}
            pathname={pathname}
          >
            {data[1]}
          </NavStyle.SCTotalValue>
        ))}
      </NavStyle.SCNavCountFooter>
    </NavStyle.SCCount>
  );
};

export default TableParticulars;
