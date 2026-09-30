import { Dialog, Transition } from '@headlessui/react'
import { Fragment, useEffect } from 'react'
import { Player } from '@lottiefiles/react-lottie-player'
import './styles.css'
import { useTranslation } from 'react-i18next'
import { useUserData } from "../../../context";

interface ModalProps {
  fileJson: string
  modalTitle: string
  modalContent: string
  openModal: boolean
  closeModal: () => void
  onClickModal: () => void
  text: string
}

const Modal = ({
  fileJson,
  modalTitle,
  modalContent,
  openModal,
  closeModal,
  onClickModal,
  text
}: ModalProps) => {
  const { t } = useTranslation()
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  useEffect(() => {
    if(fileJson === "/assets/img/manual/upload-success.json") {      
      setTimeout(() => {
        closeModal();
      }, 2000);
    }
  },[])

  return (
    <>
      {text == 'MANUAL_UPLOAD' ? (
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

              <div className="modal-content">
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
                    <Dialog.Panel
                      className="modal-content--block"
                      style={{ height: '350px', width: '530px' }}
                    >
                      {/* <img src="/assets/img/ist/warning.svg" className='warning_img' style={{ marginTop: '70px' }} /> */}
                      <Player
                        src={fileJson}
                        background="transparent"
                        style={{
                          width: '148px',
                          height: '148px',
                          marginTop: '50px'
                        }}
                        loop
                        autoplay
                      ></Player>
                      <Dialog.Title
                        as="h3"
                        className="modal-title"
                        style={{
                          fontSize: '23px',
                          fontFamily: 'Roboto',
                          marginTop: '20px'
                        }}
                      >
                        {modalTitle}
                      </Dialog.Title>
                      {/* <div className="mt-2">
                          <p className="modal-content--text">
                            {modalContent}
                          </p>
                        </div> */}
                    </Dialog.Panel>
                  </Transition.Child>
                </div>
              </div>
            </Dialog>
          </Transition>
        </>
      ) : (
        <Transition appear show={openModal} as={Fragment}>
          <Dialog style={{zoom: 0.7}} as="div" className="modal-box" onClose={closeModal}>
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

            <div className="modal-content">
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
                  <Dialog.Panel className="modal-content--block">
                    <img
                      src="/assets/img/ist/warning.svg"
                      className="warning_img"
                    />
                    <Dialog.Title as="h3" className="modal-title">
                      {modalTitle}
                    </Dialog.Title>
                    <div className="mt-2">
                      <p className="modal-content--text">{modalContent}</p>
                    </div>

                    <div className="mt-4">
                      <button
                        type="button"
                        className={"button_reject " + themeUi}
                        onClick={onClickModal}
                      >
                        {text}
                      </button>
                      <button
                        type="button"
                        className="button_cancel"
                        onClick={closeModal}
                      >
                        {t('pendingISTRequests.button.cancel')}
                      </button>
                    </div>
                  </Dialog.Panel>
                </Transition.Child>
              </div>
            </div>
          </Dialog>
        </Transition>
      )}
    </>
  )
}

export default Modal
