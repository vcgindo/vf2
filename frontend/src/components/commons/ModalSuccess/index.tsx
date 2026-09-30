import { Dialog, Transition } from "@headlessui/react";
import { Fragment } from "react";
import {
  SCModalContent,
  SCModalBox,
  SCWrapper,
  SCImg,
  SCTextAbove,
  SCTextBelow,
  SCBtnClose,
  SCBtnBack,
} from "./styles";
import { useTranslation } from "react-i18next";

interface ModalProps {
  openModal: boolean;
  closeModal: () => void;
  setIsOpenReportIssue: any;
  colorTheme: string;
}

const ModalSuccess = ({
  openModal,
  closeModal,
  setIsOpenReportIssue,
  colorTheme,
}: ModalProps) => {
  const { t } = useTranslation();

  const handleBack = () => {
    setIsOpenReportIssue(true);
    closeModal();
  };

  const handleClose = () => {
    closeModal();
  };
  return (
    <>
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
            <SCModalBox>
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
                  <SCWrapper>
                    <SCImg
                      src="/assets/img/reportIssue/tick-success.svg"
                      alt="tick"
                    />
                    <SCTextAbove>
                      {t("reportAnIssue.msgSuccessAbove")}
                    </SCTextAbove>
                    <SCTextBelow>
                      {t("reportAnIssue.msgSuccessBelow")}
                    </SCTextBelow>
                    <SCBtnClose onClick={handleClose} colorTheme={colorTheme}>
                      {t("reportAnIssue.btnClose")}
                    </SCBtnClose>
                    <SCBtnBack onClick={handleBack} colorTheme={colorTheme}>
                      {t("reportAnIssue.btnBack")}
                    </SCBtnBack>
                  </SCWrapper>
                </Dialog.Panel>
              </Transition.Child>
            </SCModalBox>
          </SCModalContent>
        </Dialog>
      </Transition>
    </>
  );
};

export default ModalSuccess;
