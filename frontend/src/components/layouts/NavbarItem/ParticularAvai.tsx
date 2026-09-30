import { useEffect, useState } from "react";
import { TableParticulars } from "../../index";
import { useGetParticularsAvai } from "../../../module-store-transfer/services/AvailabilityComparison";
import { useTranslation } from "react-i18next";

const ParticularAvai = ({ themeUi }: any) => {
  const { t } = useTranslation();
  const [listTitle, setListTitle] = useState<any>([]);
  const [listData, setListData] = useState<any>([]);
  const [total, setTotal] = useState<any>({});
  const [pcs, setPcs] = useState<boolean>(true);
  const { mutateAsync: mutateParAvai } = useGetParticularsAvai();

  useEffect(() => {
    mutateParAvai(
      { pcs: pcs },
      {
        onSuccess: (res) => {
          setListTitle([
            t("availabilityComparison.tableParticulars.particulars"),
            t("availabilityComparison.tableParticulars.surplus"),
            t("availabilityComparison.tableParticulars.shortage"),
          ]);
          setListData([
            {
              name: t("availabilityComparison.tableParticulars.S-B"),
              column1: res?.data["S-B"]["Surplus"],
              column2: res?.data["S-B"]["Shortage"],
            },
            {
              name: t("availabilityComparison.tableParticulars.S-B-S"),
              column1: res?.data["S - B - S"]["Surplus"],
              column2: res?.data["S - B - S"]["Shortage"],
            },
            {
              name: t("availabilityComparison.tableParticulars.S-B-S-C"),
              column1: res?.data["S - B - S - C"]["Surplus"],
              column2: res?.data["S - B - S - C"]["Shortage"],
            },
          ]);
          setTotal({
            name: "Total",
            column1: res?.data["Total"]["Surplus"],
            column2: res?.data["Total"]["Shortage"],
          });
        },
        onError: (error) => {
          console.log("error", error);
        }
      }
    );
  }, [pcs]);

  return (
    <>
      <TableParticulars
        themeUi={themeUi}
        listTitle={listTitle}
        listData={listData}
        totalData={total}
        pathname="/availability-comparison"
        pcs={pcs}
        setPcs={setPcs}
      />
    </>
  );
};

export default ParticularAvai;
