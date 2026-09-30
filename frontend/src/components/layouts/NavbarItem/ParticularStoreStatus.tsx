import { useState } from "react";
import { useGetTotalParticulars } from "../../../services/store-status";
import { TableParticulars } from "../../index";
import { useTranslation } from "react-i18next";

const ParticularStoreStatus = ({ themeUi }: any) => {
  const { t } = useTranslation();
  const [pcs, setPcs] = useState(false);
  const { data: dataFetchParStoreStatus } = useGetTotalParticulars();
  const listTitle = [
    t("storeStatus.tableParticulars.particulars"),
    t("storeStatus.tableParticulars.count"),
  ];
  const listData = [
    {
      name: t("storeStatus.tableParticulars.inactiveStores"),
      column1: dataFetchParStoreStatus?.data["Inactive Stores"],
    },
    {
      name: t("storeStatus.tableParticulars.activeStores"),
      column1: dataFetchParStoreStatus?.data["Active Stores"],
    },
  ];
  const total = {
    name: t("storeStatus.tableParticulars.total"),
    column1: dataFetchParStoreStatus?.data["Total"],
  };

  return (
    <>
      <TableParticulars
        themeUi={themeUi}
        listTitle={listTitle}
        listData={listData}
        totalData={total}
        pathname=""
        pcs={pcs}
        setPcs={setPcs}
      />
    </>
  );
};

export default ParticularStoreStatus;
