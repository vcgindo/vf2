import { DBMGraphCellRendererWrapper,DBMSleepCellRendererWrapper } from "./styles";
import {useGetDBMUpdateSleepTbl} from "../../../../Services/MTA/DBM"
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import { useState } from "react";
import ConfirmationDataModal from "./ConfirmationModal";

export const DBMGraphCellRenderer = (params: any) => {
  const onChartClick = () => {
    params.onShowChart(params.data);
  };

  return (
    <DBMGraphCellRendererWrapper>
      <img
        src="/assets/img/VectorFLOW/NMS/seasonality-graph-icon.svg"
        height={28}
        width={28}
        onClick={onChartClick}
        data-testid="graph-icon"
      />
    </DBMGraphCellRendererWrapper>
  );
};

export const DBMSleepCellRenderer = (params: any) => {
  const { mutateAsync: getDBMUpdateSleepTbl, isLoading: isDBMUpdateSleepTbl } =
    useGetDBMUpdateSleepTbl();
  const [iconEnabled, setIconEnabled] = useState(true);
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState(false);

  if (isDBMUpdateSleepTbl) {
    return <VFLoader />;
  }

  const onSleepClick = () => {
    if (!iconEnabled) return;
    setIsConfirmationModalOpen(true);
  };

  const closeModal = () => {
    setIsConfirmationModalOpen(false);
    setIconEnabled(true);
  };

  const handleSuccess = async () => {
    const SKUCode = params.data.SKUCode;
    const WHCode = params.data.LocCode;
    const dataObject = { SKUCode, WHCode };

    await getDBMUpdateSleepTbl({
      data: [dataObject],
    });
    params.callBack();
    closeModal();
  };

  const handleFailure = () => {
    closeModal();
  };

  return (
    <DBMSleepCellRendererWrapper>
      <img
        src="/assets/img/SleepIconDBM.svg"
        height={14}
        width={14}
        onClick={onSleepClick}
        style={{ opacity: iconEnabled ? 1 : 0.3 }}
      />
      {isConfirmationModalOpen && (
        <ConfirmationDataModal
          mode="sleep"
          onSuccess={handleSuccess}
          onFailure={handleFailure}
          onCloseModal={closeModal}
        />
      )}
    </DBMSleepCellRendererWrapper>
  );
};
