import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import './styles.css'
import CheckboxAvailability from '../Checkbox/CheckboxAvailability'
import Spinner from '../Spinner'
import { useTranslation } from 'react-i18next'

interface ModalProps {
  modalTitle: string
  openModal: boolean
  closeModal: () => void
  startExport: (data: any) => void
  exportInprogress: boolean
  selectedItem: any
  setSelectedItem: (data: any) => void
  dataTable: any
}

const ModalAvailabilityComparison = ({
  modalTitle,
  openModal,
  closeModal,
  exportInprogress,
  selectedItem,
  setSelectedItem,
  startExport,
  dataTable
}: ModalProps) => {
  const { t } = useTranslation()
  const selectItem = (e: any, item: any) => {
    let arr = [...selectedItem]
    if (!e.target.checked) {
      arr.push(`${item.before}X${item.after}`)
      setSelectedItem(arr)
    } else {
      arr = arr.filter((x: any) => x !== `${item.before}X${item.after}`)
      setSelectedItem(arr)
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
                  <Dialog.Panel className="modal-availability--block">
                    <Dialog.Title as="h3" className="modal-title-availability">
                      <img
                        src="/assets/img/availability/download.svg"
                        className="download"
                      />
                      {modalTitle}
                    </Dialog.Title>
                    {exportInprogress && (
                      <div className="loading-area">
                        <div className="overlay"></div>
                        <Spinner />
                      </div>
                    )}
                    <div className="mt-availability table-export">
                      {dataTable.map((item: any) => {
                        return (
                          <div className="item-panel">
                            {item.data.map((child: any) => {
                              return (
                                <div className="item-panel-header">
                                  <CheckboxAvailability
                                    value={item.id}
                                    defaultChecked={false}
                                    name="availability-item"
                                    onChange={(e) => {
                                      selectItem(e, child)
                                    }}
                                  />
                                  <img
                                    src="/assets/img/availability/black-arrow.svg"
                                    alt="arrow"
                                  />
                                  <div className="item-panel-header-content">
                                    <span
                                      className={child.before.toLowerCase()}
                                    >
                                      {child.before.charAt(0)}
                                    </span>
                                    <span className={child.after.toLowerCase()}>
                                      {child.after.charAt(0)}
                                    </span>
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        )
                      })}
                    </div>
                    <div className="mt-availability btn-group">
                      <button
                        type="button"
                        className="button_availability"
                        onClick={closeModal}
                      >
                        {t('availabilityComparison.button.cancel')}
                      </button>
                      <button
                        type="button"
                        className="button_availability button_availability_download"
                        onClick={() => {
                          startExport(selectedItem)
                        }}
                      >
                        {t('availabilityComparison.button.downloadToExcel')}
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

export default ModalAvailabilityComparison
