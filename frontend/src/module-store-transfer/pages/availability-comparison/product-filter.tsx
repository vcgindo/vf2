import { forwardRef, useEffect, useImperativeHandle, useState } from 'react'
import { ProductFilter } from '../../../components'
import { AvailabilityComparisonService } from '../../../module-store-transfer/services/AvailabilityComparison/api'
import { useSelector } from 'react-redux'
import { RootState } from '../../../redux/store/store'

export default forwardRef((props, ref) => {
  // const { t } = useTranslation()
  const [productFilterLoading, setProductFilterLoading] =
    useState<boolean>(false)
  const [listBrand, setListBrand] = useState<any>([])
  const [listSubBrand, setListSubBrand] = useState<any>([])
  const [listCategory, setListCategory] = useState<any>([])

  const [brand, setBrand] = useState<any>([])
  const [subBrand, setSubBrand] = useState<any>([])
  const [category, setCategory] = useState<any>([])
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1'];   
  const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2'];   
  const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3'];   

  const handleProductData = (data: any) => {
    setListBrand(
      data?.product_hierarchy_1?.map((item: string) => ({ label: item, value: item }))
    )
    setListSubBrand(
      data?.product_hierarchy_2?.map((item: string) => ({ label: item, value: item }))
    )
    setListCategory(
      data?.product_hierarchy_3?.map((item: string) => ({ label: item, value: item }))
    )
  }

  useEffect(() => {
    async function initProductFilter () {
      setProductFilterLoading(true)
      const { data } =
        await AvailabilityComparisonService.getListProductFilter()
      const productFilter = data?.data
      handleProductData(productFilter)

      setProductFilterLoading(false)
    }
    initProductFilter()
  }, [])

  const productFilter = [
    {
      icon: '/assets/img/ist/target.svg',
      placeholder: PRODUCT_PERMISSION_L1,
      options: listBrand,
      value: brand,
      onChange: setBrand,
      top: 18
    },
    {
      icon: '/assets/img/ist/target.svg',
      placeholder: PRODUCT_PERMISSION_L2,
      options: listSubBrand,
      value: subBrand,
      onChange: setSubBrand,
      top: 18
    },
    {
      icon: '/assets/img/ist/option.svg',
      placeholder: PRODUCT_PERMISSION_L3,
      options: listCategory,
      value: category,
      onChange: setCategory
    }
  ]

  useImperativeHandle(ref, () => ({
    getProductFilterValue () {
      return getProductFilterValue()
    },
    resetFilter () {
      resetFilter()
    }
  }))

  const resetFilter = () => {
    setBrand([])
    setSubBrand([])
    setCategory([])
  }

  const getProductFilterValue = () => {
    return {
      brand,
      subBrand,
      category
    }
  }

  return (
    <ProductFilter
      productFilter={productFilter}
      loading={productFilterLoading}
    />
  )
})
