import { useState } from "react";
import { SCTabs, SCTab } from "./styles";
import * as globalStyles from "../../../styles/global";
import { useUserData } from "../../../context";

interface Tab {
  listTabs: any;
  onClick: any;
  activeTab?:any;
  setActiveTab?:any
}

const NavigationTab = ({ listTabs, onClick,activeTab:propActiveTab ,setActiveTab:propSetActiveTab  }: Tab) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [localActiveTab, localSetActiveTab] = useState(0);
  const activeTab = propActiveTab ?? localActiveTab;
  const setActiveTab = propSetActiveTab ?? localSetActiveTab;

  const onClickTabItem = (index: number) => {
    setActiveTab(index);
    onClick(index);
  };

  const style = {
    color: `${globalStyles.chooseThemeColor[themeUi].color5}`,
    borderBottom: `1px solid ${globalStyles.chooseThemeColor[themeUi].color5}`,
  };

  return (
    <SCTabs>
      {listTabs.map((item: string, index: number) => (
        <SCTab
          key={index}
          style={activeTab === index ? style : {}}
          onClick={() => {
            onClickTabItem(index);
          }}
        >
          {item}
        </SCTab>
      ))}
    </SCTabs>
  );
};

export default NavigationTab;
