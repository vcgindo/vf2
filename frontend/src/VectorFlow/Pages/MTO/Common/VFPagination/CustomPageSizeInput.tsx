import React, { useEffect, useState } from "react";
import { CustomPageSize, PageSizeInput, PageSizeInputDiv } from "./styles";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import { useUserData } from "../../../../../context";
import { notifyError } from "../../../../../helpers/notify";

interface props {
  savePageSize?: any;
  userPageSize: any;
}

const CustomPageSizeInput = ({ savePageSize, userPageSize }: props) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const [customPageSize, setCustomPageSize] = useState<number | undefined>();
  const minPageSize = 1;
  const maxPageSize = 5000;

  useEffect(() => {
    setCustomPageSize(userPageSize);
  }, [userPageSize]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    try {
      const inputValue = parseInt(e.target.value);
      setCustomPageSize(inputValue);
    } catch (e) {
      console.error(e);
    }
  };

  const validatePageSize = () => {
    if (customPageSize === undefined ||  isNaN(customPageSize)) {
      notifyError("Invalid page size");
    } else {
      if (customPageSize < minPageSize) {
        notifyError("Page size can not be less than " + minPageSize);
      } else if (customPageSize > maxPageSize) {
        notifyError("Page size can not exceed " + maxPageSize);
      } else {
        savePageSize && savePageSize(customPageSize);
      }
    }
  };

  return (
    <CustomPageSize>
      Page Size:
      <PageSizeInputDiv>
        <PageSizeInput
          className="no-arrows"
          type="number"
          themeUi={themeUi}
          value={customPageSize ?? ""}
          onChange={handleChange}
        />
        <VFButton
          onClick={validatePageSize}
          themeUi={themeUi}
          disabled={false}
          style={{
            height: "100%",
            width: "30%",
            borderRadius: "0px 3px 3px 0px",
            boxShadow: "none",
          }}
        >
          <img
            src="/assets/img/rightArrowHorizontal.svg"
            height={13}
            width={7}
          />
        </VFButton>
      </PageSizeInputDiv>
    </CustomPageSize>
  );
};

export default CustomPageSizeInput;
