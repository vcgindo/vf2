import { useRef, useState } from 'react'
import { UseGetIstTotal } from '../../../module-main/services'
import * as NavStyle from './styles'
import { Tooltip } from 'react-tooltip'
import 'react-tooltip/dist/react-tooltip.css'
import { useTranslation } from 'react-i18next'
import { format_number } from '../../../helpers/utils'

const Particulars = ({themeUi}: any) => {
  const { t } = useTranslation()
  const { data: ISTTotal } = UseGetIstTotal()
  const totalPaticulars = ISTTotal?.data?.data

  const yieldValue = totalPaticulars?.yield_value ? (totalPaticulars?.yield_value / 100000).toFixed(1).toString() : "0";
  const yieldValueTotalToday = totalPaticulars?.yield_value_total_today ? (totalPaticulars?.yield_value_total_today / 100000).toFixed(1).toString(): "0";
  const valueYieldToday = `₹${yieldValue} / ${yieldValueTotalToday} L`;
  const listCounters = [
    {
      name: t('navbar.particulars.totalISTLineItems'),
      count: `${totalPaticulars?.total_ist_line_items || 0}`
    },
    {
      name: t('navbar.particulars.totalISTLineItemsSatisfyingMOQ'),
      count: `${totalPaticulars?.total_moq || 0}`
    },
    {
      name: t('navbar.particulars.ISTSuggesionsIgnoredRejected'),
      count: `${totalPaticulars?.ist_suggestions_ignored_rejected || 0}`
    },
    {
      name: t('navbar.particulars.ISTSuggestionsAccepted'),
      count: `${totalPaticulars?.ist_suggestions_accepted || 0}`
    },
    {
      name: t('navbar.particulars.sizeSetCompletion'),
      count: `${totalPaticulars?.size_set_completion.toString().slice(0, 4) || 0
        }`
    },
    {
      name: t('navbar.particulars.ISTYieldToday'),
      count: valueYieldToday
    }
  ]

  const listColumn = [
    { name: t('navbar.particulars.tableHeader.title') },
    { name: t('navbar.particulars.tableHeader.counts') },
    { name: t('navbar.particulars.tableHeader.quantity') },
    { name: t('navbar.particulars.tableHeader.value') }
  ]

  const listPaticulars = [
    {
      paticulars: t('navbar.particulars.tableContent.totalISTLineItems'),
      counts: `${totalPaticulars?.total_ist_line_items || 0}`,
      quantity: `${totalPaticulars?.qty_ist_line_items || 0}`,
      value: `${totalPaticulars?.value_ist_line_items || 0}`
    },
    {
      paticulars: t(
        'navbar.particulars.tableContent.totalISTLineItemsSatisfyingMOQ'
      ),
      counts: `${totalPaticulars?.total_moq || 0}`,
      quantity: `${totalPaticulars?.qty_moq || 0}`,
      value: `${totalPaticulars?.value_moq || 0}`
    },
    {
      paticulars: t(
        'navbar.particulars.tableContent.ISTSuggesionsIgnoredRejected'
      ),
      counts: `${totalPaticulars?.ist_suggestions_ignored_rejected || 0}`,
      quantity: `${totalPaticulars?.qty_ignore || 0}`,
      value: `${totalPaticulars?.value_ignore || 0}`
    },
    {
      paticulars: t('navbar.particulars.tableContent.ISTSuggestionsAccepted'),
      counts: `${totalPaticulars?.ist_suggestions_accepted || 0}`,
      quantity: `${totalPaticulars?.qty_accepted || 0}`,
      value: `${totalPaticulars?.value_accepted || 0}`
    },
    {
      paticulars: t('navbar.particulars.tableContent.sizeSetCompletion'),
      counts: `${totalPaticulars?.size_set_completion.toString().slice(0, 4) || 0
        }`,
      quantity: `${totalPaticulars?.total_qty_size_set_completion.toString().slice(0, 4) ||
        0
        }`,
      value: `${totalPaticulars?.value_qty_size_set_completion.toString().slice(0, 4) ||
        0
        }`
    }
  ]

  const divRef: any = useRef(null)
  const [bottomPosition, setBottomPosition] = useState<number>(0)
  const [leftPosition, setLeftPosition] = useState<number>(0)

  const formatNumber = (value: any) => {
    const dataFormat = format_number(Number(value))
    return dataFormat.digits + dataFormat.letter
  }

  const renderToolTip = () => {
    return (
      <div>
        <NavStyle.SCTableTooltip>
          <tr style={{ borderBottom: '1px dashed #000000' }}>
            {listColumn.map((item) => {
              return (
                <NavStyle.SCTableTooltipTitle>
                  {item.name}
                </NavStyle.SCTableTooltipTitle>
              )
            })}
          </tr>
          {listPaticulars.map(i => (
            <tr>
              <td style={{ fontWeight: '300' }}>{i.paticulars}</td>
              <td
                style={{
                  textAlign: 'center',
                  borderLeft: '1px dashed #000000',
                  width: '15%'
                }}
              >
                {i.counts}
              </td>
              <td
                style={{
                  textAlign: 'center',
                  borderLeft: '1px dashed #000000',
                  width: '15%'
                }}
              >
                {i.quantity}
              </td>
              <td
                style={{
                  textAlign: 'center',
                  borderLeft: '1px dashed #000000',
                  width: '25%'
                }}
              >
                ₹{formatNumber(i.value)}
              </td>
            </tr>
          ))}
        </NavStyle.SCTableTooltip>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px dashed #000000',
            padding: '.5rem 0 .8rem 0'
          }}
        >
          <NavStyle.SCBenefits>
            {t('navbar.particulars.tableContent.ISTYieldToday')}
          </NavStyle.SCBenefits>
          <div style={{ width: '25%', textAlign: 'center' }}>
            <span>{valueYieldToday}</span>
          </div>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderTop: '1px dashed #000000',
            padding: '.5rem 0 .8rem 0'
          }}
        >
          <NavStyle.SCBenefits>
            {t('navbar.particulars.tableContent.ISTYYieldCumulative')}
          </NavStyle.SCBenefits>
          <div style={{ width: '25%', textAlign: 'center' }}>
            <span>₹{yieldValueTotalToday} L</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <NavStyle.SCCount>
      <NavStyle.SCNavCount themeUi={themeUi}>
        <NavStyle.SCNavCountHeader themeUi={themeUi}>
          <span>{t('navbar.particulars.title')}</span>
          <span>{t('navbar.particulars.count')}</span>
        </NavStyle.SCNavCountHeader>
        <NavStyle.SCNavCountList>
          {listCounters.map((item, idx) => (
            <NavStyle.SCNavCountItem key={idx} themeUi={themeUi}>
              <span>{item.name}</span>
              <span>{item.count}</span>
            </NavStyle.SCNavCountItem>
          ))}
        </NavStyle.SCNavCountList>
      </NavStyle.SCNavCount>
      <NavStyle.SCNavCountFooter
        bottomPosition={bottomPosition}
        leftPosition={leftPosition}
        themeUi={themeUi}
      >
        <NavStyle.SCBenefits>
          {t('navbar.particulars.ISTYieldCumulative')}
        </NavStyle.SCBenefits>
        <NavStyle.SCIconTooltip>
          <Tooltip />
          <img
            data-tooltip-id="yield_particulars"
            ref={divRef}
            src={`/assets/img/nav/btnTooltip${themeUi === "CHARCOALCHIC" ? '_black': ''}.svg`}
            alt="tooltip"
            style={{
              padding: '0 5px 3px 0',
              cursor: 'pointer',
              position: 'relative'
            }}
            onMouseOver={(e) => {
              const currentPosition = e.currentTarget.getBoundingClientRect()
              const windowsHeight = window.innerHeight
              const bottonPosition = windowsHeight - currentPosition.bottom + 25
              setBottomPosition(bottonPosition)
              setLeftPosition(currentPosition.left - 25)
            }}
          />
          <span>₹{yieldValueTotalToday} L</span>
        </NavStyle.SCIconTooltip>

        <Tooltip id="yield_particulars">{renderToolTip()}</Tooltip>
      </NavStyle.SCNavCountFooter>
    </NavStyle.SCCount>
  )
}

export default Particulars
