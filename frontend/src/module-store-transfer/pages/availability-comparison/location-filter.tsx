import { forwardRef, useEffect, useImperativeHandle, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { LocationFilter } from '../../../components'
import { AvailabilityComparisonService } from '../../../module-store-transfer/services/AvailabilityComparison/api'

export default forwardRef((props, ref) => {
  const { t } = useTranslation()
  const [listISTLocGrp, setListISTLocGrp] = useState([])
  const [listRegion, setListRegion] = useState([])
  const [listCluster, setListCluster] = useState([])
  const [listLocPerfGrp, setListLocPerfGrp] = useState([])
  const [filterLoading, setFilterLoading] = useState<boolean>(false)

  const [ISTLocGrp, setISTLocGrp] = useState<any>([])
  const [region, setRegion] = useState<any>([])
  const [cluster, setCluster] = useState<any>([])
  const [locPerfGrp, setLocPerfGrp] = useState<any>([])

  useEffect(() => {
    setFilterLoading(true)
    AvailabilityComparisonService.getListLocationFilter()
      .then((res) => {
        handleLocationData(res.data.data)
      })
      .catch((err) => {
        console.log(err)
      })
      .finally(() => {
        setFilterLoading(false)
      })
  }, [])

  const handleLocationData = (data: any) => {
    const location_group = data.wh_location_group || []
    const region = data.wh_region || []
    const state = data.wh_name || []
    const performance_group = data.performance_group || []
    setListISTLocGrp(
      location_group.map((item: string) => ({ label: item, value: item }))
    )
    setListRegion(region.map((item: string) => ({ label: item, value: item })))
    setListCluster(state.map((item: string) => ({ label: item, value: item })))
    setListLocPerfGrp(
      performance_group.map((item: string) => ({ label: item, value: item }))
    )
  }

  const locationFilter = [
    {
      placeholder: t(
        'filter.location.placeholder.availabilityComparison.locGrp'
      ),
      options: listISTLocGrp,
      value: ISTLocGrp,
      onChange: setISTLocGrp
    },
    {
      placeholder: t(
        'filter.location.placeholder.availabilityComparison.region'
      ),
      options: listRegion,
      value: region,
      onChange: setRegion
    },
    {
      placeholder: t(
        'filter.location.placeholder.availabilityComparison.locName'
      ),
      options: listCluster,
      value: cluster,
      onChange: setCluster
    },
    {
      placeholder: t(
        'filter.location.placeholder.availabilityComparison.locPerfGrp'
      ),
      options: listLocPerfGrp,
      value: locPerfGrp,
      onChange: setLocPerfGrp
    }
  ]

  useImperativeHandle(ref, () => ({
    getLocationFilterValue () {
      return getLocationFilterValue()
    },
    resetFilter () {
      resetFilter()
    }
  }))

  const resetFilter = () => {
    setISTLocGrp([])
    setRegion([])
    setCluster([])
    setLocPerfGrp([])
  }

  const getLocationFilterValue = () => {
    return {
      ISTLocGrp,
      region,
      cluster,
      locPerfGrp
    }
  }

  return (
    <LocationFilter
      locationFilter={locationFilter}
      width={25}
      loading={filterLoading}
    />
  )
})
