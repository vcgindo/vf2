import Spinner from '../../../components/commons/Spinner'
import { SelectSearchMultiple } from './../../index'
import {
  SCProductFilter,
  SCProductFilterText,
  SCProductFilterImg,
  SCIconDown,
  SCProductBoxSelect,
  SCProductFilterHeader,
  SCProductFilterFlex,
  SCIconLocation
} from './styles'
import { useTranslation } from 'react-i18next'
interface ProductProps {
  productFilter: object[]
  loading: boolean
}

const ProductFilter = ({ ...props }: ProductProps) => {
  const { t } = useTranslation()
  const { productFilter, loading } = props

  return (
    <SCProductFilter>
      <SCProductFilterHeader>
        <SCProductFilterImg src="/assets/img/ist/filter.svg" alt="filter" />
        <SCProductFilterText>{t('filter.product.title')}</SCProductFilterText>
      </SCProductFilterHeader>
      <SCProductBoxSelect>
        {loading && <Spinner />}
        {!loading &&
          productFilter.map((item: any, index: number) => {
            return (
              <SCProductFilterFlex key={index}>
                <SCIconLocation
                  className="icon_location"
                  src={item.icon}
                  alt="location"
                  top={item.top}
                />
                <SelectSearchMultiple
                  value={item.value}
                  setValue={item.onChange}
                  options={item.options}
                  placeholder={item.placeholder}
                />
                <SCIconDown
                  className="icon_location"
                  src="/assets/img/down-icon.svg"
                  alt="location"
                />
              </SCProductFilterFlex>
            )
          })}
      </SCProductBoxSelect>
    </SCProductFilter>
  )
}

export default ProductFilter
