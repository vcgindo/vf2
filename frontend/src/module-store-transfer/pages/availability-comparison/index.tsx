import {
  SCBoxFilterSticky,
  SCBoxFilter,
  SCButtonFilter,
  SCFilterBtn,
  SCResetFilterBtn,
  SCTabArea,
  SCTabHeader,
  SCExportAllBoxButton,
  SCExportAllBoxSpan,
  SCTabHeaderLeft,
  SCTabHeaderRight,
  SCTabButton,
  SCTabBody,
  CurrentAvailability
} from './styles'
import { useRef, useState } from 'react'
import {
  ButtonOutlineAvailability,
  AvailabilityActiveTab,
  ModalAvailabilityComparison
} from '../../../components'

import { AvailabilityComparisonService } from '../../../module-store-transfer/services/AvailabilityComparison/api'
import { notifyError, notifySuccess } from '../../../helpers/notify'
import { useTranslation } from 'react-i18next'
import LcnFilter from './location-filter'
import PrdFilter from './product-filter'
import { useUserData } from "../../../context";

const Availability = () => {
  const { t } = useTranslation()
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [filterStyle, setFilterStyle] = useState<boolean>(true)

  const [executeFilter, setExecuteFilter] = useState<number>(
    new Date().getTime()
  )
  const [dataTable, setDataTable] = useState<any>([])
  const [openModalExport, setOpenModalExport] = useState<boolean>(false)

  const [activeTab, setActiveTab] = useState<string>('store')

  const [selectedItem, setSelectedItem] = useState<any>([])
  const [exportInprogress, setExportInprogress] = useState<boolean>(false)

  const changeTab = (tab: string) => {
    setActiveTab(tab)
    setExecuteFilter(new Date().getTime())
  }

  const locationFilterRef = useRef<any>()
  const productFilterRef = useRef<any>()

  const resetFilter = () => {
    productFilterRef.current?.resetFilter()

    locationFilterRef.current?.resetFilter()

    setExecuteFilter(new Date().getTime())
  }

  const handleExport = async (data: any) => {
    const { ISTLocGrp, region, cluster, locPerfGrp } =
      // eslint-disable-next-line no-unsafe-optional-chaining
      locationFilterRef.current?.getLocationFilterValue()
    const { brand, subBrand, category } =
      // eslint-disable-next-line no-unsafe-optional-chaining
      productFilterRef.current?.getProductFilterValue()
    await new Promise<void>((resolve) => {
      AvailabilityComparisonService.exportViewData(
        { brand, subBrand, category },
        { ISTLocGrp, region, cluster, locPerfGrp },
        activeTab,
        filterStyle,
        data
      )
        .then((resp: any) => {
          const blob = new Blob([resp.data], {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          })
          const url = URL.createObjectURL(blob)
          const link = document.createElement('a')
          link.href = url
          const tab =
            activeTab === 'store'
              ? 'StoreLevel'
              : activeTab === 'sub-brand'
                ? 'SubBrandLevel'
                : 'CategoryLevel'
          link.setAttribute('download', `${tab}_${new Date().getTime()}.xlsx`)
          document.body.appendChild(link)
          link.click()
          // remove the element
          link.parentNode?.removeChild(link)
          // revoke the object URL to avoid memory leaks
          URL.revokeObjectURL(url)
          notifySuccess(t('availabilityComparison.notify.exportSuccess'))
        })
        .catch((error) => {
          console.log(error)
          notifyError(t('availabilityComparison.notify.exportError'))
        })
        .finally(() => {
          resolve()
        })
    })
  }

  const startExport = async (data: any) => {
    if (data.length === 0) { return notifyError(t('availabilityComparison.notify.noRecordsSelected')) }
    data = data.map((item: any) => item.split('X'))
    setExportInprogress(true)
    await handleExport(data)
    setOpenModalExport(false)
    setSelectedItem([])
    setExportInprogress(false)
  }

  return (
    <>
      <ModalAvailabilityComparison
        modalTitle={t('availabilityComparison.modal.title')}
        openModal={openModalExport}
        closeModal={() => {
          setOpenModalExport(false)
          setSelectedItem([])
        }}
        exportInprogress={exportInprogress}
        selectedItem={selectedItem}
        setSelectedItem={setSelectedItem}
        startExport={startExport}
        dataTable={dataTable}
      />
      <SCBoxFilterSticky>
        <SCBoxFilter>
          <PrdFilter ref={productFilterRef} />
          <LcnFilter ref={locationFilterRef} />
          <SCButtonFilter>
            <SCFilterBtn
              onClick={() => {
                setExecuteFilter(new Date().getTime())
              }}
              themeUi={themeUi}
            >
              {t('availabilityComparison.button.filter')}
            </SCFilterBtn>
            <SCResetFilterBtn onClick={resetFilter} themeUi={themeUi}>
              {t('availabilityComparison.button.resetFilter')}
            </SCResetFilterBtn>
          </SCButtonFilter>
        </SCBoxFilter>
        <SCTabArea>
          <SCTabHeader>
            <SCTabHeaderLeft>
              <SCTabButton
                active={activeTab === 'store'}
                zIndex={3}
                marLeft={false}
                onClick={() => {
                  changeTab('store')
                }}
                themeUi={themeUi}
              >
                {t('availabilityComparison.tab.storeLevel')}
              </SCTabButton>
              <SCTabButton
                active={activeTab === 'sub-brand'}
                zIndex={2}
                marLeft={true}
                onClick={() => {
                  changeTab('sub-brand')
                }}
                themeUi={themeUi}
              >
                {t('availabilityComparison.tab.subBrandLevel')}
              </SCTabButton>
              <SCTabButton
                active={activeTab === 'category'}
                zIndex={1}
                marLeft={true}
                onClick={() => {
                  changeTab('category')
                }}
                themeUi={themeUi}
              >
                {t('availabilityComparison.tab.categoryLevel')}
              </SCTabButton>
            </SCTabHeaderLeft>
            <SCTabHeaderRight>
              <ButtonOutlineAvailability
                labelOn={t('availabilityComparison.button.pcs')}
                labelOff={t('availabilityComparison.button.style')}
                toggled={filterStyle}
                onClick={() => {
                  setFilterStyle(!filterStyle)
                  setExecuteFilter(new Date().getTime())
                }}
              />
              <SCExportAllBoxButton
                onClick={() => {
                  setOpenModalExport(true)
                }}
              >
                <img src="/assets/img/forced/excel.png" alt="and" />
                <SCExportAllBoxSpan>
                  {t('availabilityComparison.button.exportSelected')}
                </SCExportAllBoxSpan>
                <img src="/assets/img/forced/export.svg" alt="and" />
              </SCExportAllBoxButton>
            </SCTabHeaderRight>
          </SCTabHeader>
          <SCTabBody>
            <AvailabilityActiveTab
              handleExport={handleExport}
              setDataTable={setDataTable}
              productFilter={productFilterRef}
              locationFilter={locationFilterRef}
              activeTab={activeTab}
              filterStyle={filterStyle}
              executeFilter={executeFilter}
            />
          </SCTabBody>
          <CurrentAvailability>
            <span>{t('availabilityComparison.currentAvailability')}</span>
          </CurrentAvailability>
        </SCTabArea>
      </SCBoxFilterSticky>
    </>
  )
}

export default Availability
