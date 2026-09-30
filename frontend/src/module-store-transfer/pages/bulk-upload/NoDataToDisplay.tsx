
import { NoData } from './style'

interface NoDataToDisplayProps {
    imgSrc?: string
}

function NoDataToDisplay({imgSrc}:NoDataToDisplayProps) {
  return (
   <NoData>
        <img src={imgSrc} alt="" />
   </NoData>
  )
}

export default NoDataToDisplay