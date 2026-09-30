import { useState, useRef } from "react";
import * as ManualStyle from "./styles";
import axios from "axios";
import { FileUploader } from "react-drag-drop-files";
import { notifyError } from "../../../helpers/notify";
import { Modal } from "../../../components";
import { handleDownload } from "../../../helpers/utils";
import { useTranslation } from "react-i18next";
import { useUserData } from "../../../context";

declare global {
  interface Navigator {
    msSaveBlob: (blob: Blob, fileName: string) => boolean;
  }
}
const ManualUpload = () => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const [fileUpload, setFile] = useState<any>(null);
  const [isLoading, setIsloading] = useState(true);
  const [isShowPopup, setShowPopup] = useState(false);
  const [isShowSuccess, setIsShowSuccess] = useState<boolean>(false);
  const nameApi = "/api/manual-upload/template-view/";

  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = (): void => {
    if (inputRef.current != null) {
      inputRef.current.click();
    }
  };

  const handleFileChange = (e: any) => {
    if (e.target.files.length < 1) {
      return;
    }

    const file = e.target.files[0];
    switch (file.type) {
      case "text/csv":
        setFile(file);
        break;
      default:
        notifyError(t("manualUpload.csvError"));
    }
  };

  const handleFiles = (e: any) => {
    switch (e[0].type) {
      case "text/csv":
        setFile(e[0]);
        break;
      default:
        notifyError(t("manualUpload.csvError"));
    }
  };

  const exportToCsv = (filename: string, log: string) => {
    const blob = new Blob([log], { type: "text/csv;charset=utf-8;" });
    if (navigator.msSaveBlob) {
      // IE 10+
      navigator.msSaveBlob(blob, filename);
    } else {
      const link = document.createElement("a");
      if (link.download !== undefined) {
        // feature detection
        // Browsers that support HTML5 download attribute
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = "hidden";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    }
  };

  const handleSubmit = async (event: any) => {
    setShowPopup(!isShowPopup);
    event.preventDefault();
    const formData = new FormData();

    formData.append("file", fileUpload);

    setIsloading(false);
    try {
      const response: any = await axios.post(
        "/api/manual-upload/import-csv/",
        formData
      );

      if (response.status === 201) {
        setTimeout(() => {
          setIsloading(true);
          setShowPopup(false);
          setIsShowSuccess(true);
          // Run after 3000 milliseconds
        }, 1500);
      } else if (response.status === 200) {
        notifyError(t("manualUpload.updateError"));
        exportToCsv(fileUpload?.name, response.data);
        setTimeout(() => {
          setIsloading(true);
          setShowPopup(false);
          // Run after 3000 milliseconds
        }, 1500);
      } else if (response.status === 400) {
        notifyError(response?.response?.msg);
        setShowPopup(false);
        setIsloading(true);
      }

      setFile(null);
    } catch (error: any) {
      notifyError(error?.response?.msg);
      setTimeout(() => {
        setIsloading(true);
        setShowPopup(false);
        // Run after 3000 milliseconds
      }, 3000);
    }
  };

  const closeModalSuccess = () => {
    setIsShowSuccess(false);
  };

  return (
    <ManualStyle.SCManualBoxCenter>
      <ManualStyle.SCManualBox>
        <ManualStyle.SCManualText>
          {t("manualUpload.title")}
        </ManualStyle.SCManualText>
        <ManualStyle.SCManualDrag>
          <FileUploader
            id="fileInput"
            classes="drop_area"
            type="file"
            name="file"
            multiple
            hoverTitle=" "
            // types={["CSV"]}
            handleChange={(e: any) => {
              handleFiles(e);
            }}
          >
            <div style={{ paddingTop: 20 }}>
              <ManualStyle.SCManualExcel>
                <img src="/assets/img/manual/excel.png" />
              </ManualStyle.SCManualExcel>
              <ManualStyle.SCManualDragText>
                {t("manualUpload.dragDrop")}
              </ManualStyle.SCManualDragText>
            </div>
          </FileUploader>
          <ManualStyle.SCManualDowload>
            <ManualStyle.SCManualDowloadText>
              {t("manualUpload.template")}
            </ManualStyle.SCManualDowloadText>
            <img
              src={`/assets/img/manual/${
                themeUi === "REGALBLAZE"
                  ? "download-icon-yellow"
                  : "download-icon"
              }.svg`}
              height="100%"
              style={{ cursor: "pointer" }}
              onClick={() => {
                handleDownload(nameApi, "MANUAL UPLOAD TEMPLATE");
              }}
            />
          </ManualStyle.SCManualDowload>
          <ManualStyle.SCManualUpload>
            <ManualStyle.SCManualUploadButton
              className="file-upload"
              onClick={handleClick}
            >
              <img src="/assets/img/manual/plus.png" width={30} />
              <ManualStyle.SCManualUploadInput
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                ref={inputRef}
                value=""
                style={{ display: "none" }}
              />
            </ManualStyle.SCManualUploadButton>
            <ManualStyle.SCManualUploadText
              style={{ color: `${fileUpload ? "black" : "#C8C5C5"}` }}
            >
              {fileUpload ? (
                <div>
                  {`${fileUpload.name}`}
                  <button
                    onClick={() => {
                      setFile(null);
                    }}
                    style={{ marginLeft: "20px", padding: "5px" }}
                  >
                    {t("manualUpload.deleteBtn")}
                  </button>
                </div>
              ) : (
                t("manualUpload.uploadTitle")
              )}
            </ManualStyle.SCManualUploadText>
          </ManualStyle.SCManualUpload>
        </ManualStyle.SCManualDrag>
        <ManualStyle.SCManualUploadBtn
          onClick={(e) => {
            handleSubmit(e);
          }}
          disabled={!(fileUpload && isLoading)}
          style={{ cursor: `${fileUpload && isLoading ? "" : "not-allowed"}` }}
          themeUi={themeUi}
        >
          <ManualStyle.SCManualImgUpload src="/assets/img/manual/iconmonstr-upload-17.svg" />
          {isLoading
            ? t("manualUpload.uploadBtn")
            : t("manualUpload.uploadingBtn")}
        </ManualStyle.SCManualUploadBtn>
      </ManualStyle.SCManualBox>
      <Modal
        fileJson="/assets/data.json"
        modalTitle={t("manualUpload.uploadInProcess")}
        modalContent=""
        openModal={isShowPopup && !isLoading}
        // eslint-disable-next-line @typescript-eslint/no-empty-function
        closeModal={() => {}}
        // eslint-disable-next-line @typescript-eslint/no-empty-function
        onClickModal={() => {}}
        text={t("manualUpload.modalTitle")}
      />

      {isShowSuccess && (
        <Modal
          fileJson="/assets/img/manual/upload-success.json"
          modalTitle={t("manualUpload.uploadedSuccessfully")}
          modalContent=""
          openModal={!isShowPopup && isShowSuccess}
          // eslint-disable-next-line @typescript-eslint/no-empty-function
          closeModal={closeModalSuccess}
          // eslint-disable-next-line @typescript-eslint/no-empty-function
          onClickModal={() => {}}
          text={t("manualUpload.modalTitle")}
        />
      )}
    </ManualStyle.SCManualBoxCenter>
  );
};

export default ManualUpload;
