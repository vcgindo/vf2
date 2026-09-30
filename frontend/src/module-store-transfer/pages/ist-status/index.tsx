/* eslint-disable no-case-declarations */
import { useContext, useEffect, useState } from 'react'
import { AlertNoRecords, SCIstStatusRow, SCIstStatusTable } from './styles'
import ViewComponent from './views'
import PivotTableUI from 'react-pivottable/PivotTableUI'
import 'react-pivottable/pivottable.css'
import './style.css'
import { ISTStatusService } from '../../services/IstStatus/api'
import { ISTStatusContext } from '../../../context/ISTStatusContext'
import { notifyError, notifySuccess } from '../../../helpers/notify'
import TableRenderers from 'react-pivottable/TableRenderers'
import Plot from 'react-plotly.js'
import createPlotlyRenderers from 'react-pivottable/PlotlyRenderers'
import { useTranslation } from 'react-i18next'

// create Plotly renderers via dependency injection
const PlotlyRenderers = createPlotlyRenderers(Plot)

const istStatus = () => {
  const { t } = useTranslation()
  const [originalDataComponent, setOriginalDataComponent] = useState({} as any)
  const [dataComponent, setDataComponent] = useState([] as any)
  const [listView, setListView] = useState([] as any)
  const [currentView, setCurrentView] = useState({} as any)
  const [pivotTableState, setPivotTableState] = useState({} as any)
  const [loadingView, setLoadingView] = useState(true)

  const {
    currentAction,
    setCurrentAction,
    exportView,
    setExportView,
    setCurrentViewName,
    setCurrentViewCount,
    setCurrentDataCount
  } = useContext(ISTStatusContext)

  // handle EXPORT ALL
  useEffect(() => {
    if (!exportView) return
    async function init() {
      const res = await ISTStatusService.exportAll(currentView.id)
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'IST_Status.csv')
      document.body.appendChild(link)
      link.click()
      // remove the element
      link.parentNode?.removeChild(link)
      // revoke the object URL to avoid memory leaks
      URL.revokeObjectURL(url)
      notifySuccess(t('ISTStatus.notify.exportSuccess'))
      setExportView(false)
    }
    init()
  }, [exportView])

  // handle Edit View
  useEffect(() => {
    if (currentAction !== 'saving' && currentAction !== 'deleting') return
    async function init() {
      try {
        switch (currentAction) {
          case 'saving':
            if (!pivotTableState.rows) {
              // notifyError('Please move at least 1 row');
              break
            }
            const currentViewID = currentView.id
            const currentViewData = listView.find(
              (item: any) => item.id === currentViewID
            )
            const modifiedRows = pivotTableState.rows
            // find key in originalDataComponent
            const modifiedRowsKey = modifiedRows.map((item: any) => {
              const key = Object.keys(originalDataComponent).find(
                (key: any) => originalDataComponent[key] === item
              )
              return key
            })
            currentViewData.columns_list = modifiedRowsKey
            currentViewData.is_default_view = true
            currentViewData.table_config = pivotTableState
            delete currentViewData.table_config.aggregators
            delete currentViewData.table_config.renderers
            delete currentViewData.table_config.tableColorScaleGenerator
            delete currentViewData.table_config.data
            await ISTStatusService.updateView(currentViewID, currentViewData)
            notifySuccess(t('ISTStatus.notify.saveSuccess'))
            break
          case 'deleting':
            await ISTStatusService.deleteView(currentView.id)
            notifySuccess(t('ISTStatus.notify.deleteSuccess'))
            break
          default:
            break
        }
      } catch (error: any) {
        console.log('====================================')
        console.log(error)
        console.log('====================================')
        notifyError(error.message)
        setCurrentAction('edit')
        return
      }
      setCurrentAction('edit')
      if (pivotTableState.rows || currentAction === 'deleting') { await getListView(originalDataComponent) }
    }
    init()
  }, [currentAction])

  const getViewByID = async (
    id: any,
    originalDataComponent: any,
    viewName: string
  ) => {
    // if (currentAction === 'edit') return;
    const viewDetail = await ISTStatusService.getViewDetailById(id)
    let currentDetail: any = Object.keys(
      viewDetail?.data?.data?.ist_status_list[0] || {}
    )
    currentDetail = currentDetail.map((item: any) => {
      return originalDataComponent[item]
    })
    setCurrentViewName(viewName)
    if (viewDetail?.data?.data?.table_config) {
      delete viewDetail.data.data.table_config.aggregators
      delete viewDetail.data.data.table_config.renderers
      delete viewDetail.data.data.table_config.tableColorScaleGenerator
      setPivotTableState(viewDetail.data.data.table_config)
    } else {
      setPivotTableState(
        {
          rows: currentDetail || [],
          aggregatorName: 'Count Unique Values',
          rendererName: 'Table',
          vals: ['Quantity to be Moved']
        }
      )
    }
    setCurrentView({
      current: viewDetail?.data?.data?.ist_status_list,
      detail: currentDetail,
      id,
      viewName
    })
  }

  const getListView = async (dataComponent = originalDataComponent) => {
    let listView: any = await ISTStatusService.getListView()
    listView = listView.data.data.list_views
    setListView(listView)
    setCurrentViewCount(listView.length)
    let currentView = listView.find((item: any) => item.is_default_view)
    currentView = currentView || listView[0]
    if (currentView) {
      await getViewByID(currentView?.id, dataComponent, currentView?.view_name)
    } else {
      setCurrentViewName(t('ISTStatus.viewName'))
      setPivotTableState({})
      setCurrentView({
        detail: []
      })
    }
  }

  useEffect(() => {
    async function init() {
      const dataComponent: any = await ISTStatusService.getListComponent()
      const { columns, data } = dataComponent.data
      setOriginalDataComponent(columns)

      const valueComponents = Object.values(columns).map((item: any) => {
        return { [item]: '-' }
      })
      const flatValueComponents = valueComponents.reduce(
        (acc: any, val: any) => Object.assign(acc, val),
        {}
      )

      const promises: any = []
      data.forEach((item: any) => {
        promises.push(
          // eslint-disable-next-line no-async-promise-executor
          new Promise(async (resolve) => {
            const cloneCpn = { ...flatValueComponents }
            const childPrms: any = []
            // for key value
            for (const key in item) {
              childPrms.push(
                new Promise((resolve) => {
                  const itemCpn = item[key]
                  const keyInComponent = columns[key]
                  cloneCpn[keyInComponent] = itemCpn
                  resolve(1)
                })
              )
            }
            await Promise.all(childPrms)
            resolve(cloneCpn)
          })
        )
      })
      const dataComponentList = JSON.parse(JSON.stringify(await Promise.all(promises)))
      setDataComponent(dataComponentList)
      setLoadingView(false)
      setCurrentDataCount(dataComponentList.length)
      await getListView(columns)
    }
    init()
  }, [])

  // reset context when user leave page
  useEffect(() => {
    return () => {
      setCurrentAction('edit')
      setCurrentViewName(t('ISTStatus.viewName'))
      setCurrentViewCount(0)
    }
  }, [])

  return (
    <SCIstStatusRow className={currentAction === 'edit' ? 'edit-state' : ''}>
      {dataComponent.length === 0 && !loadingView && <AlertNoRecords>
        {t('ISTStatus.notify.noRecords')}
      </AlertNoRecords>}
      {dataComponent.length !== 0 && !loadingView && <>
        <ViewComponent
          currentView={currentView}
          currentAction={currentAction}
          listView={listView}
          getViewByID={getViewByID}
          originalDataComponent={originalDataComponent}
          getListView={getListView}
        />
        <SCIstStatusTable>
          <PivotTableUI
            data={dataComponent}
            onChange={(s: any) => {
              setPivotTableState(s)
            }}
            renderers={Object.assign({}, TableRenderers, PlotlyRenderers)}
            {...pivotTableState}
          />
        </SCIstStatusTable>
      </>}
    </SCIstStatusRow>
  )
}

export default istStatus
