import { AvailabilityToolTipWrapper } from './styles'

import { ITooltipParams } from 'ag-grid-enterprise'


const AvailabilityToolTip = (params: ITooltipParams) => {
    return (
        <AvailabilityToolTipWrapper>
            {params?.value}% Availability
        </AvailabilityToolTipWrapper>

    )

}

export default AvailabilityToolTip