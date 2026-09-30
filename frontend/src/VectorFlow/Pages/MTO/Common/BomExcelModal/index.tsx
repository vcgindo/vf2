import React from "react";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";

type BomExcelModalProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  onCancel: () => void;
  themeUi: any;
  messageText: string;
  headerText: string;
};

const BomExcelModal: React.FC<BomExcelModalProps> = ({
  open,
  onClose,
  onConfirm,
  onCancel,
  themeUi,
  messageText,
  headerText,
}) => {
  return (
    <VFModalCard
      openModal={open}
      closeModal={onClose}
      headerText={headerText}
      headerIcon=""
      headerBgColor="white"
      headerTextColor="black"
      closeIcon="/assets/img/VectorFLOW/NMS/close-dark.svg"
      paddingLeftAndRight={27}
    >
      <div
        style={{
          fontSize: "16px",
          padding: "1rem",
          textAlign: "center",
          height: "125px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {messageText}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "13px",
          padding: "15px 1.5rem 15px 1.5rem",
          boxShadow: "0px -4px 10px rgba(0, 0, 0, 0.06)",
        }}
      >
        <VFButtonOutline themeUi={themeUi} onClick={onConfirm}>
          Yes
        </VFButtonOutline>
        <VFButton themeUi={themeUi} onClick={onCancel}>
          No
        </VFButton>
      </div>
    </VFModalCard>
  );
};

export default BomExcelModal;
