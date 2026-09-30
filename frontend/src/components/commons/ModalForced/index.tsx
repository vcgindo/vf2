import { Dialog, Transition } from '@headlessui/react'
import { Fragment, useState } from 'react'
import './styles.css'
import { useTranslation } from 'react-i18next'

interface ModalProps {
  modalTitle: string
  openModal: boolean
  closeModal: () => void
  onClickModal: () => void
  user: any
  setTerminate: any
}

const Modal = ({
  modalTitle,
  openModal,
  closeModal,
  onClickModal,
  user,
  setTerminate
}: ModalProps) => {
  const { t } = useTranslation()
  const themeUi = user?.user?.theme_ui;
  const [other, setOther] = useState(false)
  const [isChecked, setIsCheck] = useState(true)
  const handChangeValue = (item: number) => {
    if (item === 1) {
      setTerminate(t('ISTForcedClosure.modal.terminate.stockIsNotAvailable'))
      setIsCheck(true)
      setOther(false)
    } else if (item === 2) {
      setTerminate(
        t('ISTForcedClosure.modal.terminate.stockIsNotInASaleableCondition')
      )
      setIsCheck(false)
      setOther(false)
    } else if (item === 3) {
      setTerminate(
        t('ISTForcedClosure.modal.terminate.stockIsReservedForOnlineOrder')
      )
      setIsCheck(false)
      setOther(false)
    } else if (item === 4) {
      setTerminate('')
      setIsCheck(false)
      setOther(true)
    }
  }
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
                  <Dialog.Panel className="modal-forced--block">
                    <Dialog.Title as="h3" className="modal-title-forced">
                      <span>
                        {' '}
                        {modalTitle}{' '}
                        <span className="modal-user">{user?.user?.name}</span>
                      </span>
                      <span onClick={closeModal} className="close-forced">
                        x
                      </span>
                    </Dialog.Title>
                    <div className="mt-forced">
                      <p className="modal-forced--text">
                        {t('ISTForcedClosure.modal.terminate.header')}
                      </p>
                      <div className={"modal-input--box " + themeUi}>
                        <input
                          onClick={() => {
                            handChangeValue(1)
                          }}
                          className="modal-input"
                          name="age"
                          type="radio"
                          checked={isChecked}
                        />
                        <label className="modal-label">
                          {t(
                            'ISTForcedClosure.modal.terminate.stockIsNotAvailable'
                          )}
                        </label>
                      </div>
                      <div className={"modal-input--box " + themeUi}>
                        <input
                          onClick={() => {
                            handChangeValue(2)
                          }}
                          className="modal-input"
                          name="age"
                          type="radio"
                        />
                        <label className="modal-label">
                          {t(
                            'ISTForcedClosure.modal.terminate.stockIsNotInASaleableCondition'
                          )}
                        </label>
                      </div>
                      <div className={"modal-input--box " + themeUi}>
                        <input
                          onClick={() => {
                            handChangeValue(3)
                          }}
                          className="modal-input"
                          name="age"
                          type="radio"
                        />
                        <label className="modal-label">
                          {t(
                            'ISTForcedClosure.modal.terminate.stockIsReservedForOnlineOrder'
                          )}
                        </label>
                      </div>
                      <div className={"modal-input--box " + themeUi}>
                        <input
                          onClick={() => {
                            handChangeValue(4)
                          }}
                          className="modal-input"
                          name="age"
                          type="radio"
                        />
                        <label className="modal-label">
                          {t('ISTForcedClosure.modal.terminate.others')}
                        </label>
                      </div>
                      <div className="modal-input--box">
                        {other
                          ? (
                            <textarea
                              className="modal-forced--textarea"
                              maxLength={255}
                              onChange={(e) => setTerminate(e.target.value)}
                              cols={3}
                            />
                          )
                          : (
                            ''
                          )}
                      </div>
                    </div>
                    <div className="mt-forced">
                      <button
                        type="button"
                        className={"button_forced " + themeUi}
                        onClick={onClickModal}
                      >
                        {t('ISTForcedClosure.button.submitBtn')}
                      </button>
                    </div>
                  </Dialog.Panel>
                </Transition.Child>
              </div>
            </div>
          </Dialog>
        </Transition>
      }
    </>
  )
}

export default Modal
