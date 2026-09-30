import React, { useEffect, useState } from "react";
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline";
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard";
import VFSelect from "../../../../../components/VectorFLOW/commons/MTO/VFSelect";
import Checkbox from "../../../../../components/VectorFLOW/commons/MTO/Checkbox";

type DownloadOptionValue = "completely_available" | "shortage" | "all";

type OptionType = {
  label: string;
  value: DownloadOptionValue;
};

type ConfirmationModelProps = {
  open: boolean;
  onClose: () => void;
  onConfirm: (option: DownloadOptionValue, includeDetails: boolean) => void;
  themeUi: any;
  messageText: string;
  headerText: string;
};

const downloadOptions: OptionType[] = [
  { label: "All", value: "all" },
  { label: "Shortage", value: "shortage" },
  { label: "Completely Available", value: "completely_available" },
];

const ConfirmationModel: React.FC<ConfirmationModelProps> = ({
  open,
  onClose,
  onConfirm,
  themeUi,
  messageText,
  headerText,
}) => {
  const [selectedOption, setSelectedOption] = useState<OptionType | null>(null);
  const [isChecked, setIsChecked] = useState(false);

  const handleConfirm = () => {
    if (selectedOption) {
      onConfirm(selectedOption.value, isChecked);
    }
  };

  useEffect(() => {
    if (!open) {
      setSelectedOption(null);
      setIsChecked(false);
    }
  }, [open]);

  return (
    <VFModalCard
      openModal={open}
      closeModal={onClose}
      headerText={headerText}
      headerIcon=""
      headerBgColor="white"
      headerTextColor="black"
      closeIcon="/assets/img/VectorFLOW/NMS/close-dark.svg"
      paddingLeftAndRight={0}
    >
      <div
        style={{
          fontSize: "16px",
          padding: "1.5rem 8rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1.5rem",
          minHeight: "125px",
        }}
      >
        {/* Dropdown Row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            width: "100%",
            justifyContent: "space-between",
            gap: "1rem"
          }}
        >
          <span style={{ fontSize: "1.7rem", fontWeight: 400 }}>
            Select the excel which you want to download :
          </span>
          
          <div style={{ width: "200px" }}> 
            <VFSelect
              themeUi={themeUi}
              options={downloadOptions}
              value={selectedOption}
              onChange={(option: OptionType) => setSelectedOption(option)}
              placeholder="Select Option"
              isClearable={false}
              styles={{
                menuPortal: (base: any) => ({ ...base, zIndex: 99999 }),
                menu: (base: any) => ({ ...base, zIndex: 99999 })
              }}
            />
          </div>
        </div>

        {/* Checkbox + Message Row */}
        <div 
            style={{ 
                display: "flex", 
                alignItems: "center", 
                width: "100%",         
                justifyContent: "flex-start",
                gap: "10px" 
            }}
        >
            <span style={{ fontSize: "1.7rem", fontWeight: 400 }}>
            {messageText}
          </span>
            <Checkbox 
                theme={themeUi}
                type="checkbox"
                checked={isChecked}
                onChange={(e) => setIsChecked(e.target.checked)}
                style={{ cursor: "pointer" }}
            />
        </div>
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
        <VFButtonOutline
          themeUi={themeUi}
          onClick={handleConfirm}
          disabled={!selectedOption} 
          style={{
            opacity: !selectedOption ? 0.5 : 1,
            cursor: !selectedOption ? "not-allowed" : "pointer",
          }}
        >
          Okay
        </VFButtonOutline>
      </div>
    </VFModalCard>
  );
};

export default ConfirmationModel;