/* eslint-disable no-unsafe-optional-chaining */
import { useEffect, useState } from 'react'
import { AvailabilityComparisonService } from '../../../module-store-transfer/services/AvailabilityComparison/api'
import {
  ItemPanel,
  ItemPanelBody,
  ItemPanelBodyCenter,
  ItemPanelBodyLeft,
  ItemPanelBodyRight,
  ItemPanelFooter,
  ItemPanelHeader,
  ItemPanelHeaderContent,
  ProjectedAvailability,
  ContentArea,
  ContentItem,
  ItemPanelLoading
} from './styles'
import Spinner from '../Spinner'
import { useTranslation } from 'react-i18next'
import { format_number } from '../../../helpers/utils'

interface TabProps {
  productFilter: any
  locationFilter: any
  activeTab: string
  filterStyle: boolean
  executeFilter: number
  setDataTable: (data: any) => void
  handleExport: (data: any) => void
}

const AvailabilityActiveTab = ({ ...props }: TabProps) => {
  const { t } = useTranslation()
  const {
    productFilter,
    locationFilter,
    activeTab,
    filterStyle,
    executeFilter,
    setDataTable,
    handleExport
  } = props
  const [storeLevelData, setStoreLevelData] = useState([] as any)
  const [dataLoading, setDataLoading] = useState(true)
  const [selectedItem, setSelectedItem] = useState({
    idx: null,
    data: null
  } as any)

  useEffect(() => {
    setDataLoading(true)
    const { ISTLocGrp, region, cluster, locPerfGrp } =
      locationFilter.current?.getLocationFilterValue()
    const { brand, subBrand, category } =
      productFilter.current?.getProductFilterValue()
    AvailabilityComparisonService.getViewData(
      { brand, subBrand, category },
      { ISTLocGrp, region, cluster, locPerfGrp },
      activeTab,
      filterStyle
    )
      .then((resp: any) => {
        setStoreLevelData([])
        handleViewData(resp.data.data)
      })
      .catch((error) => {
        console.log(error)
      })
      .finally(() => {
        setDataLoading(false)
      })
  }, [executeFilter])

  const handleViewData = (data: any) => {
    const whiteData = {
      color: t('availabilityComparison.color.white'),
      data: data.filter((item: any) => item.after === 'White')
    }
    const greenData = {
      color: t('availabilityComparison.color.green'),
      data: data.filter((item: any) => item.after === 'Green')
    }
    const redData = {
      color: t('availabilityComparison.color.red'),
      data: data.filter((item: any) => item.after === 'Red')
    }
    setStoreLevelData([whiteData, greenData, redData])
    setDataTable([whiteData, greenData, redData])
  }

  const exportItem = async (idx: string, data: any) => {
    if (idx === selectedItem.idx) return
    setSelectedItem({
      idx,
      data
    })

    await handleExport([[data.before, data.after]])

    setSelectedItem({
      idx: null,
      data: null
    })
  }

  return (
    <ContentArea>
      {dataLoading && <Spinner />}
      {!dataLoading &&
        storeLevelData.map((item: any, idx: number) => {
          return (
            <ContentItem color={item.color} key={`content_item_${idx}`}>
              {item.color === t('availabilityComparison.color.white') && (
                <img
                  src="/assets/img/availability/surplus.svg"
                  alt="surplus"
                  className="left-icon"
                />
              )}
              {item.color === t('availabilityComparison.color.red') && (
                <img
                  src="/assets/img/availability/shortage.svg"
                  alt="shortage"
                  className="left-icon"
                />
              )}
              {item.color === t('availabilityComparison.color.green') && (
                <ProjectedAvailability>
                  <span>
                    <p>{t('availabilityComparison.projectedAvailability')}</p>
                    <p>({t('availabilityComparison.ISTReplenishment')})</p>
                  </span>
                </ProjectedAvailability>
              )}
              {item.data.map((subItem: any, index: any) => {
                const price_replenishment = format_number(
                  subItem.price_replenishment
                )
                const price_in = format_number(subItem.price_in)
                const price_out = format_number(subItem.price_out)
                const quantityCount =
                  subItem.quantity_moving_in_replenishment +
                  subItem.quantity_moving_in -
                  subItem.quantity_moving_out
                const priceCount = format_number(
                  subItem.price_replenishment +
                  subItem.price_in -
                  subItem.price_out
                )
                const keyProp = `item_panel_${index}_${idx}`
                return (
                  <ItemPanel
                    key={keyProp}
                    onClick={async () => {
                      await exportItem(keyProp, subItem)
                    }}
                  >
                    {selectedItem.idx === keyProp && (
                      <ItemPanelLoading>
                        <div className="overlay"></div>
                        <Spinner />
                      </ItemPanelLoading>
                    )}
                    <ItemPanelHeader>
                      <img
                        src="/assets/img/availability/black-arrow.svg"
                        alt="arrow"
                      />
                      <ItemPanelHeaderContent
                        index={index}
                        color={subItem.after}
                      >
                        <span>{subItem.before}</span>
                        <span>{subItem.after}</span>
                      </ItemPanelHeaderContent>
                    </ItemPanelHeader>
                    <ItemPanelBody>
                      <ItemPanelBodyLeft>
                        <div className="rep-in">
                          <span>
                            {subItem.quantity_moving_in_replenishment}
                            <sub>{filterStyle ? 'Pc' : 'St'}</sub>
                          </span>
                          <span>
                            ₹{price_replenishment.compare}
                            {price_replenishment.digits}
                            {price_replenishment.letter}
                          </span>
                        </div>
                        <div className="ist-in">
                          <span>
                            {subItem.quantity_moving_in}
                            <sub>{filterStyle ? 'Pc' : 'St'}</sub>
                          </span>
                          <span>
                            ₹{price_in.compare}
                            {price_in.digits}
                            {price_in.letter}
                          </span>
                        </div>
                      </ItemPanelBodyLeft>
                      <ItemPanelBodyCenter activeTab={activeTab}>
                        <div className="gray-arrow">
                          <img
                            src="/assets/img/availability/gray-arrow.svg"
                            alt="gray-arrow"
                            className="gray-arrow-left"
                          />
                        </div>
                        <div className="store">
                          {activeTab === 'store'
                            ? (
                              <img
                                src="/assets/img/availability/home.svg"
                                alt="home"
                              />
                            )
                            : (
                              <img
                                src="/assets/img/availability/home-2.svg"
                                alt="home-2"
                              />
                            )}
                        </div>
                        <div className="gray-arrow">
                          <img
                            src="/assets/img/availability/gray-arrow.svg"
                            alt="gray-arrow"
                            className="gray-arrow-right"
                          />
                        </div>
                      </ItemPanelBodyCenter>
                      <ItemPanelBodyRight>
                        <div className="ist-out">
                          <span>
                            {subItem.quantity_moving_out}
                            <sub>{filterStyle ? 'Pc' : 'St'}</sub>
                          </span>
                          <span>
                            ₹{price_out.compare}
                            {price_out.digits}
                            {price_out.letter}
                          </span>
                        </div>
                      </ItemPanelBodyRight>
                    </ItemPanelBody>
                    <span className="number-last">{subItem.number}</span>
                    <ItemPanelFooter>
                      <span>
                        {Math.abs(quantityCount)}
                        <sub>{filterStyle ? 'Pc' : 'St'}</sub>{' '}
                        {quantityCount > 0
                          ? (
                            <img
                              src="/assets/img/availability/blue-arrow.svg"
                              alt="blue-arrow"
                            />
                          )
                          : quantityCount < 0
                            ? (
                              <img
                                src="/assets/img/availability/brown-arrow-down.svg"
                                alt="brown-arrow-down"
                              />
                            )
                            : (
                              '~'
                            )}
                      </span>
                      <span>
                        ₹{priceCount.compare}
                        {Math.abs(priceCount.digits)}
                        {priceCount.letter}{' '}
                        {priceCount.digits > 0
                          ? (
                            <img
                              src="/assets/img/availability/blue-arrow.svg"
                              alt="blue-arrow"
                            />
                          )
                          : priceCount.digits < 0
                            ? (
                              <img
                                src="/assets/img/availability/brown-arrow-down.svg"
                                alt="brown-arrow-down"
                              />
                            )
                            : (
                              '~'
                            )}
                      </span>
                    </ItemPanelFooter>
                  </ItemPanel>
                )
              })}
            </ContentItem>
          )
        })}
    </ContentArea>
  )
}

export default AvailabilityActiveTab
