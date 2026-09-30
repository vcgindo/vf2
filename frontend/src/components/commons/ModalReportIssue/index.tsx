import { Dialog, Transition } from "@headlessui/react";
import "./styles.css";
import { Fragment, useEffect, useState } from "react";
import { FileUploader } from "react-drag-drop-files";
import { notifyError } from "../../../helpers/notify";
import { useTranslation } from "react-i18next";
import { useUserData } from "../../../context";
import { MainService } from "../../../services/profile/api";
import { SelectOptionLevel } from "../../index";
import {
  SCModalContent,
  SCTextTitle,
  SCCloseModal,
  SCWrapperContent,
  SCText,
  SCTextarea,
  SCWrapperText,
  SCTextThin,
  SCItem,
  SCWrapperImg,
  SCImg,
  SCPlaceholderImg,
  SCModalBottom,
  SCButtonGoBack,
  SCButtonSubmit,
  SCWrapperContentImg,
  SCWrapperItemImg,
  SCItemText,
  SCItemImg,
} from "./styles";

interface ModalProps {
  openModal: boolean;
  closeModal: () => void;
  setIsLoadSpinner: any;
  isLoadSpinner: boolean;
  setIsOpenReportSuccess: any;
}

const ModalReportIssue = ({
  openModal,
  closeModal,
  setIsLoadSpinner,
  isLoadSpinner,
  setIsOpenReportSuccess,
}: ModalProps) => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const [listIssueComponent, setListIssueComponent] = useState<any>({});
  const [listIssueType, setListIssueType] = useState<any>({});
  const [valueComponent, setValueComponent] = useState<any>();
  const [valueIssueType, setValueIssueType] = useState<any>();
  const [fileUpload, setFileUpload] = useState<any>();
  const [description, setDescription] = useState<string>("");

  useEffect(() => {
    MainService.getIssueReport()
      .then((res: any) => {
        const dataIssueComponent = res?.data?.issue_component;
        const dataIssueType = res?.data?.issue_type;
        const optionsIssueComponent: any = [];
        dataIssueComponent &&
          Object.keys(dataIssueComponent).forEach((keyComponent: any) => {
            optionsIssueComponent.push({
              label: keyComponent,
              value: keyComponent,
              isParent: true,
              isDisabled: true,
              color: "#000000",
              paddingLeft: "20px",
            });
            dataIssueComponent[keyComponent].forEach(
              (itemIssueComponent: string) => {
                optionsIssueComponent.push({
                  label: itemIssueComponent,
                  value: itemIssueComponent,
                  isParent: false,
                  color: "#7C7C7C",
                  paddingLeft: "50px",
                  data: `${keyComponent} - ${itemIssueComponent}`,
                });
              }
            );
          });

        const optionsIssueType = dataIssueType?.map((item: any) => ({
          label: item,
          value: item,
          isParent: false,
          color: "#7C7C7C",
          paddingLeft: "20px",
        }));
        setListIssueComponent(optionsIssueComponent);
        setListIssueType([...optionsIssueType]);
      })
      .catch((error) => {
        console.log("error", error);
      });
  }, []);

  const handleReportIssue = () => {
    if (!valueComponent) {
      notifyError(t("reportAnIssue.error.pleaseSelectComponent"));
    } else if (!valueIssueType) {
      notifyError(t("reportAnIssue.error.pleaseSelectIssueType"));
    } else if (!fileUpload) {
      notifyError(t("reportAnIssue.error.pleaseSelectTheFileToUpload"));
    } else {
      setIsLoadSpinner(true);
      const formData = new FormData();

      formData.append("component", valueComponent?.data);
      formData.append("_type", valueIssueType?.value);
      formData.append("description", description);
      for (const file of fileUpload) {
        formData.append("attachment", file, file?.name);
      }      

      MainService.postIssueReport(formData)
        .then(() => {
          setIsLoadSpinner(false);
          closeModal();
          setIsOpenReportSuccess(true);
        })
        .catch((error: any) => {
          console.log("error", error);
          setIsLoadSpinner(false);
          closeModal();
        });
    }
  };

  const handleChooseFile = (file: any) => {
    if (file.length < 1) {
      return;
    }

    if (file.length + fileUpload?.length > 5) {
      notifyError(t("reportAnIssue.error.DontSendMore5File"));
      return;
    }
    const listFile: any = fileUpload ? [...fileUpload] : [];
    for (const item of file) {
      const extension = item.name.split(".").pop().toLowerCase();
      if (
        extension === "png" ||
        extension === "jpg" ||
        extension === "jpeg" ||
        extension === "gif"
      ) {
        listFile.push(item);
      } else {
        notifyError(t("reportAnIssue.error.allowedToSendFile"));
      }
    }
    setFileUpload(listFile);
  };

  const handleDelete = (index: number) => {
    const newUploadFile = [...fileUpload];
    newUploadFile.splice(index, 1);
    setFileUpload(newUploadFile);
  };

  return (
    <>
      {
        <Transition appear show={openModal} as={Fragment}>
          <Dialog as="div" className="modal-box" onClose={closeModal}>
            <Transition.Child
              as={Fragment}
              enter="transition"
              enterFrom="opa-0"
              enterTo="opa"
              leave="leave-modal"
              leaveFrom="opa"
              leaveTo="opa-0"
            >
              <div className="modal-bg inset" />
            </Transition.Child>
            <SCModalContent>
              <div className="modal-content--box">
                <Transition.Child
                  as={Fragment}
                  enter="transition"
                  enterFrom="opa-0 tranlate "
                  enterTo="opa translate-y-0 "
                  leave="leave-modal"
                  leaveFrom="opa translate-y-0"
                  leaveTo="opacity-0 tranlate"
                >
                  <Dialog.Panel className="modal-forced--block">
                    <Dialog.Title as="h3" className="modal-title-forced">
                      <SCTextTitle>{t("reportAnIssue.title")}</SCTextTitle>
                      <SCCloseModal onClick={closeModal}>x</SCCloseModal>
                    </Dialog.Title>
                    <SCWrapperContent>
                      <SCItem>
                        <SCText htmlFor="choose-component">
                          {t("reportAnIssue.chooseComponent")}
                        </SCText>
                        <SelectOptionLevel
                          value={valueComponent}
                          setValue={setValueComponent}
                          options={listIssueComponent}
                          placeholder={t(
                            "reportAnIssue.placeholderSelectAnOption"
                          )}
                          isDisabled={isLoadSpinner}
                        />
                      </SCItem>

                      <SCItem>
                        <SCText htmlFor="select-issue-type">
                          {t("reportAnIssue.selectIssueType")}
                        </SCText>
                        <SelectOptionLevel
                          value={valueIssueType}
                          setValue={setValueIssueType}
                          options={listIssueType}
                          placeholder={t(
                            "reportAnIssue.placeholderSelectAnOption"
                          )}
                          isDisabled={isLoadSpinner}
                        />
                      </SCItem>

                      <SCItem>
                        <SCText htmlFor="issue-description">
                          {t("reportAnIssue.issueDescription")}
                        </SCText>
                        <SCTextarea
                          id="issue-description"
                          maxLength={2000}
                          rows={5}
                          placeholder={
                            t("reportAnIssue.placeholderDescription") || ""
                          }
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          disabled={isLoadSpinner}
                        />
                      </SCItem>

                      <SCWrapperImg>
                        <SCWrapperText>
                          <SCText>{t("reportAnIssue.attachments")}</SCText>
                          <SCTextThin>
                            {` (${t("reportAnIssue.anyFileUpto4Mb")})`}
                          </SCTextThin>
                        </SCWrapperText>
                        <FileUploader
                          classes="content-file"
                          multiple
                          name="file"
                          handleChange={handleChooseFile}
                          disabled={isLoadSpinner}
                        >
                          <SCImg
                            src="/assets/img/reportIssue/plus.svg"
                            alt=""
                          />
                          <SCPlaceholderImg>
                            {t("reportAnIssue.placeholderAttachments")}
                          </SCPlaceholderImg>
                        </FileUploader>
                        <SCWrapperContentImg>
                          {fileUpload?.map((item: any, index: number) => (
                            <SCWrapperItemImg key={index}>
                              <SCItemText>{item?.name}</SCItemText>
                              <SCItemImg
                                src="/assets/img/reportIssue/delete.svg"
                                onClick={() => handleDelete(index)}
                              />
                            </SCWrapperItemImg>
                          ))}
                        </SCWrapperContentImg>
                      </SCWrapperImg>
                    </SCWrapperContent>

                    <SCModalBottom>
                      <SCButtonGoBack
                        type="button"
                        onClick={closeModal}
                        disabled={isLoadSpinner}
                      >
                        {t("reportAnIssue.goBack")}
                      </SCButtonGoBack>
                      <SCButtonSubmit
                        className={"btn_submitReport " + themeUi}
                        onClick={handleReportIssue}
                        disabled={isLoadSpinner}
                        themeUi={themeUi}
                      >
                        {t("reportAnIssue.submit")}
                      </SCButtonSubmit>
                    </SCModalBottom>
                  </Dialog.Panel>
                </Transition.Child>
              </div>
            </SCModalContent>
          </Dialog>
        </Transition>
      }
    </>
  );
};

export default ModalReportIssue;
