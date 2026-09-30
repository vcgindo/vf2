import { UsePutItemTerminate, useGetParticularsForced } from '../../../services/forced'
import { useState, useEffect } from 'react'
import { Forced } from '../../../services/forced/api'
import { notifySuccess, notifyError } from '../../../helpers/notify'
import ModalContact from '../ModalContact'
import Modal from '../ModalForced'
import { useUserData } from '../../../context'
import TableItem from './tableItem'
import { useTranslation } from 'react-i18next'

interface TableProps {
  listTable: any
  refetch: any
  listCheckAll: any
  setListCheckAll: any
}

const TableForced = ({
  listTable,
  refetch,
  listCheckAll,
  setListCheckAll
}: TableProps) => {
  const { t } = useTranslation()
  const { user } = useUserData()
  const themeUi = user?.user?.theme_ui;
  
  const [listContactDetail, setListContactDetail] = useState<any>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isOpenTerminal, setIsOpenTerminal] = useState(false)
  const [indexTerminal, setIndexTerminal] = useState<number>(0)
  const [terminate, setTerminate] = useState<string>('Stock is not available')
  const [listRequest, setListRequest] = useState([] as number[])

  const information = (infomation: any) => [
    {
      name: t('ISTForcedClosure.table.donorLocation'),
      value: infomation.donor_wh_name
    },
    {
      name: t('ISTForcedClosure.table.locationCode'),
      value: infomation.donor_wh_code
    },
    {
      name: t('ISTForcedClosure.table.city'),
      value: infomation.donor_wh_city
    },
    {
      name: t('ISTForcedClosure.table.locationType'),
      value: infomation.donor_wh_type
    },
    {
      name: t('ISTForcedClosure.table.channel'),
      value: infomation.donor_wh_subtype
    }
  ]

  const setCheckAllTable = (status: any, i: number) => {
    const temp = [...listCheckAll]
    temp[i] = status
    setListCheckAll(temp)
  }

  const checkColorAge = (age: number) => {
    if (age < 3) {
      return '#04b504'
    } else if (age <= 6) {
      return '#f2b40a'
    } else {
      return '#F24242'
    }
  }

  const { refetch: refetchTablePar } = useGetParticularsForced();
  const { mutateAsync: putItemTerminate } = UsePutItemTerminate()
  const handleTerminate = async () => {
    if (terminate) {
      const newListRequest = listTableTerminate(indexTerminal)

      const formData = {
        ids: newListRequest,
        status: 'TERMINATED',
        termination_reason: terminate
      }
      putItemTerminate(formData, {
        onSuccess: (data: any) => {
          refetch()
          refetchTablePar()
          if (data?.status === 400) {
            notifyError(data?.response?.msg)
          } else {
            notifySuccess(data?.data?.msg)
          }
          setIsOpenTerminal(false)
        },
        onError: (error: any) => {
          notifyError(error.response.msg || error.message)
        }
      })
    } else {
      notifyError(t('ISTForcedClosure.notify.enterTheReason'))
    }
  }

  const contactDetail = (id: any) => {
    const data = {
      wh_code: id
    }
    // const { data: contactDetail } = useGetContactDetail(data)
    Forced.getContactDetail(data).then((res: any) => {
      setListContactDetail(res?.data?.data)
      return res?.data
    })
    setIsOpen(true)
  }

  const onClickModalTerminal = (index: number) => {
    const newListRequest = listTableTerminate(index)

    if (newListRequest.length > 0) {
      setIndexTerminal(index)
      setIsOpenTerminal(true)
    } else {
      notifyError(t('ISTForcedClosure.notify.noRecordsSelected'))
    }
  }

  const onCloseModal = () => {
    setIsOpen(false)
    setIsOpenTerminal(false)
  }

  useEffect(() => {
    if (listTable) {
      const temp = listTable?.map(() => false)
      setListCheckAll(temp)
    }
  }, [listTable])

  const listTableTerminate = (index: number) => {
    const newListRequest = listTable[index].list_items
      .filter((item: any) => listRequest.includes(item.id))
      .map((item: any) => item.id)

    return newListRequest
  }

  const dataTable =
    listTable &&
    listTable.map((item: any, idx: number) => {
      return (
        <TableItem
          item={item}
          setListCheckAll={setCheckAllTable}
          listCheckAll={listCheckAll[idx]}
          index={idx}
          onClickModalTerminal={onClickModalTerminal}
          checkColorAge={checkColorAge}
          contactDetail={contactDetail}
          information={information}
          setListRequest={setListRequest}
          listRequest={listRequest}
          user={user}
          themeUi={themeUi}
        />
      )
    })

  return (
    <>
      {dataTable}
      <ModalContact
        modalTitle={t('ISTForcedClosure.modal.detail.title')}
        openModal={isOpen}
        closeModal={onCloseModal}
        data={listContactDetail}
      />
      <Modal
        closeModal={onCloseModal}
        setTerminate={setTerminate}
        openModal={isOpenTerminal}
        modalTitle={t('ISTForcedClosure.modal.terminate.title')}
        user={user}
        onClickModal={async () => {
          await handleTerminate()
        }}
      />
    </>
  )
}

export default TableForced
