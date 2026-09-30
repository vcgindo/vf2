import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import './styles.css'
import { useTranslation } from 'react-i18next'

interface ModalProps {
  modalTitle: string
  openModal: boolean
  closeModal: () => void
  data: any
}

const ModalContact = ({
  modalTitle,
  openModal,
  closeModal,
  data
}: ModalProps) => {
  const { t } = useTranslation()
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
                <Dialog.Panel className="modal-contact--block">
                  <Dialog.Title as="h3" className="modal-title--contact">
                    <div className="wrap-title--contact">
                      <img
                        className="avatar_contact"
                        src="/assets/img/ist/avatar_contact.png"
                        alt="user"
                      />
                      {modalTitle}
                    </div>
                    <img
                      className="close-modal--contact"
                      src="/assets/img/check/deline.svg"
                      alt="X"
                      onClick={closeModal}
                    />
                  </Dialog.Title>
                  <div className="">
                    <p className="modal-content--text">
                      {data &&
                        data.map((e: any) => (
                          <ul className="contact_list--item">
                            <li className="contact_list">
                              <span className="contact_span">
                                {t('ISTForcedClosure.modal.detail.name')}
                              </span>{' '}
                              {e.contact_name}
                            </li>
                            <li className="contact_list">
                              <span className="contact_span">
                                {t('ISTForcedClosure.modal.detail.phone')}
                              </span>{' '}
                              {e.contact_phone}
                            </li>
                            <li className="contact_list">
                              <span className="contact_span">
                                {t('ISTForcedClosure.modal.detail.email')}
                              </span>{' '}
                              {e.contact_email}
                            </li>
                          </ul>
                        ))}
                    </p>
                  </div>

                  <div className="mt-4">
                    {/* <button
                          type="button"
                          className="button_reject"
                          onClick={onClickModal}
                        >
                          {text}
                        </button>
                        <button
                          type="button"
                          className="button_cancel"
                          onClick={closeModal}
                        >
                          Cancel
                        </button> */}
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </>
  )
}

export default ModalContact
