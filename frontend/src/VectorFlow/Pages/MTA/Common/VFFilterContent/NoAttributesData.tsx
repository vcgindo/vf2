import React from "react";
import { useUserData } from "../../../../../context";
import { 
  NoFiltersContainer,
  NoFiltersIcon,
  NoFiltersSubText
} from "./style";

interface NoAttributesFiltersProps {
  reportName: string;
}

const NoAttributesFilters: React.FC<NoAttributesFiltersProps> = ({ 
  reportName 
}) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui || "";
  
  const svgSrc = themeUi === "REGALBLAZE" 
    ? "/assets/img/MTAVFMultiFilter/no data-yellow.svg" 
    : "/assets/img/MTAVFMultiFilter/no data.svg";

  return (
    <NoFiltersContainer>
      <NoFiltersIcon>
        <img 
          src={svgSrc}
          alt="No Attribute Filters Available"
          width="280" 
          height="250"
        />
      </NoFiltersIcon>
      <NoFiltersSubText theme_ui={themeUi}>
        No SKU/Location attributes found for{" "}
        <span style={{ fontWeight: '600' }}>{reportName}</span>
      </NoFiltersSubText>
    </NoFiltersContainer>
  );
};

export default NoAttributesFilters;