import { useState } from "react";
import { useGetParticularsForced } from "../../../services/forced";
import { TableParticulars } from "../../index";
import { useTranslation } from "react-i18next";

const ParticularForced = ({ themeUi }: any) => {
  const { t } = useTranslation();
  const [pcs, setPcs] = useState(false);
  const { data: dataFetchParForced } = useGetParticularsForced();
  const listTitle = [
    t("ISTForcedClosure.tableParticulars.particulars"),
    t("ISTForcedClosure.tableParticulars.>7days"),
    t("ISTForcedClosure.tableParticulars.total"),
  ];
  const listData = [
    {
      name: t("ISTForcedClosure.tableParticulars.totalOpenIsts"),
      column1: dataFetchParForced?.data["Total Open ISTs"]["> 7days"],
      column2: dataFetchParForced?.data["Total Open ISTs"]["Total"],
    },
    {
      name: t("ISTForcedClosure.tableParticulars.terminated"),
      column1: dataFetchParForced?.data["Terminated"]["> 7days"],
      column2: dataFetchParForced?.data["Terminated"]["Total"],
    },
  ];
  const total = {
    name: t("ISTForcedClosure.tableParticulars.total"),
    column1: dataFetchParForced?.data["Total"]["> 7days"],
    column2: dataFetchParForced?.data["Total"]["Total"],
  };
  return (
    <>
      <TableParticulars
        themeUi={themeUi}
        listTitle={listTitle}
        listData={listData}
        totalData={total}
        pathname="/ist-forced-closure"
        pcs={pcs}
        setPcs={setPcs}
      />
    </>
  );
};

export default ParticularForced;
