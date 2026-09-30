import * as Tab from './style'
import { ButtonOutlineStoreStatus } from './../../index'
import { UsePutStoreStatus, useGetTotalParticulars } from '../../../services/store-status'
import { notifyError, notifySuccess } from '../../../helpers/notify'
import Spinner from '../../../components/commons/Spinner'
import { useTranslation } from 'react-i18next'

interface TableSore {
  listTable: any
  refetch: any
}
const TableStore = ({ listTable, refetch }: TableSore) => {
  const { t } = useTranslation()

  const { mutateAsync: usePutStoreStatus } = UsePutStoreStatus()
  const { refetch: refetchTablePar } = useGetTotalParticulars();

  const logState = (id: number, status: boolean) => {
    const formData = {
      id,
      movement_status: !status
    }

    setTimeout(() => {
      usePutStoreStatus(formData, {
        onSuccess: (data) => {
          refetch()
          notifySuccess(data?.data?.msg)
          refetchTablePar()
        },
        onError: (data: any) => {
          notifyError(data.response.msg || data.message)
        }
      })
    }, 200)
  }

  return (
    <>
      {listTable
        ? (
          <Tab.SCTableBox style={{ marginBottom: 30 }}>
            <Tab.SCTableTab width="100%">
              <Tab.SCTableTr>
                <Tab.SCTableTh>
                  <Tab.SCTableTitle>
                    {t('storeStatus.table.brand')}
                  </Tab.SCTableTitle>
                </Tab.SCTableTh>
                <Tab.SCTableTh>
                  <Tab.SCTableTitle>
                    {t('storeStatus.table.locationName')}
                  </Tab.SCTableTitle>
                </Tab.SCTableTh>
                <Tab.SCTableTh>
                  <Tab.SCTableTitle>
                    {t('storeStatus.table.locationCode')}
                  </Tab.SCTableTitle>
                </Tab.SCTableTh>
                <Tab.SCTableTh>
                  <Tab.SCTableTitle>
                    {t('storeStatus.table.city')}
                  </Tab.SCTableTitle>
                </Tab.SCTableTh>
                <Tab.SCTableTh>
                  <Tab.SCTableTitle>
                    {t('storeStatus.table.cluster')}
                  </Tab.SCTableTitle>
                </Tab.SCTableTh>
                <Tab.SCTableTh style={{ textAlign: 'center' }}>
                  {t('storeStatus.table.status')}
                </Tab.SCTableTh>
              </Tab.SCTableTr>
              {listTable &&
                listTable.map((item: any) => (
                  <Tab.SCTableTrValue key={item?.id}>
                    <Tab.SCTableTd>{item?.specific_sales}</Tab.SCTableTd>
                    <Tab.SCTableTd>{item?.wh_name}</Tab.SCTableTd>
                    <Tab.SCTableTd>{item?.wh_code}</Tab.SCTableTd>
                    <Tab.SCTableTd>{item?.wh_city}</Tab.SCTableTd>
                    <Tab.SCTableTd>{item?.wh_location_group}</Tab.SCTableTd>
                    <Tab.SCTableTdCenter>
                      <ButtonOutlineStoreStatus
                        labelOn={t('storeStatus.button.active')}
                        labelOff={t('storeStatus.button.inactive')}
                        toggled={item?.movement_status}
                        onClick={() => {
                          logState(item?.id, item?.movement_status)
                        }}
                      />
                    </Tab.SCTableTdCenter>
                  </Tab.SCTableTrValue>
                ))}
            </Tab.SCTableTab>
          </Tab.SCTableBox>
        )
        : (
          <Spinner />
        )}
    </>
  )
}

export default TableStore
