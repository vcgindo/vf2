import { useTranslation } from 'react-i18next'
import { notifySuccess } from '../../../helpers/notify'
import { ISTStatusService } from '../../services/IstStatus/api'
import {
  SCIstStatusAddButton,
  SCIstStatusAddNew,
  SCIstStatusAddText,
  SCIstStatusFIlterBox,
  SCIstStatusInput,
  SCIstStatusLabel
} from './styles'
import { useUserData } from "../../../context";

function Views (props: any) {
  const { t } = useTranslation()
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const {
    currentView,
    listView,
    getViewByID,
    originalDataComponent,
    getListView,
    currentAction
  } = props

  const addView = async () => {
    await ISTStatusService.createView(
      `${t('ISTStatus.viewTitle')} ${listView.length + 1}`
    )
    notifySuccess(t('ISTStatus.notify.createViewSuccess'))
    await getListView()
  }

  return (
    <SCIstStatusFIlterBox>
      <SCIstStatusAddNew>
        <SCIstStatusAddText>{t('ISTStatus.viewTitle')}</SCIstStatusAddText>
        {listView.length < 5 && currentAction === 'edit' && (
          <SCIstStatusAddButton
            onClick={async () => {
              await addView()
            }}
          >
            +{t('ISTStatus.addViews')}
          </SCIstStatusAddButton>
        )}
      </SCIstStatusAddNew>
      <div style={{ display: 'flex' }}>
        {/* quick fix */}
        {listView.map((item: any, index: number) => (
          <div key={`${index}_${item.id}`} style={{ marginRight: '10px' }}>
            <SCIstStatusInput
              defaultChecked={index === 0}
              name="settingPanel"
              type={'radio'}
              value={item.view_name}
            />
            <SCIstStatusLabel
              themeUi={themeUi}
              active={currentView.id === item.id}
              onClick={() => {
                if (currentView.id !== item.id) { getViewByID(item.id, originalDataComponent, item.view_name) }
              }}
            >
              <span>{item.view_name}</span>
            </SCIstStatusLabel>
          </div>
        ))}
      </div>
    </SCIstStatusFIlterBox>
  )
}

export default Views
