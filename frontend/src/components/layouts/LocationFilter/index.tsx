import Spinner from '../../../components/commons/Spinner'
import { SelectSearchMultiple } from '../../index'
import {
  SCLocationFilter,
  SCProducFilterHeader,
  SCProductBoxSelect,
  SCProductFilterText,
  SCIconLocation,
  SCIconDown,
  SCProductFilterImg,
  SCProductBoxSelectItem
} from './styles'
import { useTranslation } from 'react-i18next'

interface LocationProps {
  locationFilter: object[]
  width: number
  loading: boolean
}

const LocationFilter = ({ locationFilter, width, loading }: LocationProps) => {
  const { t } = useTranslation()
  return (
    <SCLocationFilter>
      <SCProducFilterHeader>
        <SCProductFilterImg src="/assets/img/ist/filter.svg" alt="filter" />
        <SCProductFilterText>{t('filter.location.title')}</SCProductFilterText>
      </SCProducFilterHeader>
      <SCProductBoxSelect>
        {loading && <Spinner />}

        {!loading &&
          locationFilter.map((item: any, index: number) => {
            return (
              <SCProductBoxSelectItem key={index} width={width}>
                <SCIconLocation
                  className="icon_location"
                  src={item.icon ? item.icon : '/assets/img/ist/location.svg'}
                  alt="location"
                  locationIcon={!item.icon}
                />
                <SelectSearchMultiple
                  placeholder={item.placeholder}
                  options={item.options}
                  value={item.value}
                  setValue={item.onChange}
                />
                <SCIconDown
                  className="icon_location"
                  src="/assets/img/down-icon.svg"
                  alt="location"
                />
              </SCProductBoxSelectItem>
            )
          })}
      </SCProductBoxSelect>
    </SCLocationFilter>
  )
}

export default LocationFilter
