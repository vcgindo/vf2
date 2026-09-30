import { useTranslation } from "react-i18next";
import { useUserData } from "../../../context";

const ArrowList = ({ listData, setListData, infoUser, setInfoUser }: any) => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  const handleOpenList = (index: number) => {    
    const newData = [...listData];
    newData[index].status = !newData[index].status
    setListData(newData)
  }

  const handleCheckBox = (check: any) => {    
    const newData = { ...infoUser };    
    const index = newData.roles.indexOf(check);
    
    if (index < 0) {
      newData.roles.push(check)
    } else {
      newData.roles.splice(index, 1)
    }
    setInfoUser(newData);
  }
  
  return (
    <div className="list-roles--content scroll-style">
      {listData?.map((item: any, index: number) => (
        <div className="role-item" key={index}>
          {item.child.length > 0
            ? (
            <>
              <div
                className="wrap-title"
                onClick={() => {
                  handleOpenList(index)
                }}
              >
                <div className="role-item--title">{t(item.title)}</div>
                {item.child.length > 0 && (
                  <div className={`${item.status ? 'action-down-up' : ''}`}>
                    <img src={'/assets/img/down-icon.svg'} alt="icon" />
                  </div>
                )}
              </div>
              {item.status && (
                <div className="role-list">
                  {item.child.map((item: any) => (
                    <div className={`role-item--content ${themeUi}`} key={item.id}>
                      <input 
                        id={`checkbox-admin-${item.id}`} 
                        checked={infoUser.roles.includes(item.id)} 
                        type="checkbox" 
                        onChange={() => handleCheckBox(item.id)} 
                      />
                      <label htmlFor={`checkbox-admin-${item.id}`}>
                        <span>{t(item.name)}</span>
                      </label>
                    </div>
                  ))}
                </div>
              )}
            </>
              )
            : (
            <>
              <div className="wrap-title">
                <div className="role-item--title">{item.title}</div>
              </div>
            </>
              )}
        </div>
      ))}
    </div>
  )
}

export default ArrowList
