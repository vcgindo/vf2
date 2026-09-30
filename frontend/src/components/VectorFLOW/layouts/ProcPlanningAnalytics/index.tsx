import { useState } from "react";
import { TableParticulars } from "../../../../../src/components/index";
import { useTranslation } from "react-i18next";
import useProcPlanning from "../../../../VectorFlow/Pages/MTO/Procurement/Planning/useProcPlanning";
const ProcPlanningAnalytics = ({ themeUi }: any) => {
    const { GetCount } = useProcPlanning({});
    const { t } = useTranslation();
    const [pcs, setPcs] = useState(false);
    const listTitle = [
        t("ProcPlanning.Analytics")
    ];
    const listData = [
        {
            name: t("ProcPlanning.cntshort"),
            column1: GetCount.short,
        },
        {
            name: t("ProcPlanning.cntfa"),
            column1: GetCount.complete,
        },
    ];
    const total = {
        name: t("ProcPlanning.total"),
        column1: GetCount.total,
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

export default ProcPlanningAnalytics;
