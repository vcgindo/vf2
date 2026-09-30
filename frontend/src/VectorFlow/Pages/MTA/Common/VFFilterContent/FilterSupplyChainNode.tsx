import React, { useState, useEffect } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
} from "./style";
import Select, { components } from "react-select";
import { useColorThemeStyles } from "../../../../../hooks/useVFFilterContent";
import useGetLocation from "../../../../../hooks/useGetLocation";
import { useUserData } from "../../../../../context";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import { useVFMultiFilter } from "./useVFFilterContent";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";

interface FilterSectionProps {
  filters: any;
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
}

const CustomOption = (props: any) => {
  const optionStyles = useColorOptionStyles();

  return (
    <components.Option {...props}>
      <div style={optionStyles.optionContainer}>
        <input
          type="checkbox"
          checked={props.isSelected}
          style={optionStyles.checkbox}
          readOnly
        />
        <span style={optionStyles.colorName}>{props.data.label}</span>
      </div>
    </components.Option>
  );
};

export const SupplyChainNodeFilters: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
}) => {
  const { locations } = useGetLocation();
  const colorStyles = useColorThemeStyles();

  const { handleSelectChange } = useVFMultiFilter({
    multiFilter,
    onMultiFilterChange,
  });

  const [selectedOptions, setSelectedOptions] = useState<{
    ForLocation: string[];
    ForChildren: string[];
  }>({
    ForLocation: [],
    ForChildren: [],
  });

  const locationOptionsWithValue = locations.map((location: any) => ({
    label: location.label,
    id: location.id,
    value: location.id || location.label,
  }));

  useEffect(() => {
    if (multiFilter?.supplyChainFilter) {
      const forLocationFilters = multiFilter.supplyChainFilter.filters.filter(
        (f: BPRFilter) => f.name === "SCF1"
      );
      const forChildrenFilters = multiFilter.supplyChainFilter.filters.filter(
        (f: BPRFilter) => f.name === "SCF2"
      );

      setSelectedOptions((prev) => ({
        ...prev,
        ForLocation: forLocationFilters.map((f: BPRFilter) => f.value),
        ForChildren: forChildrenFilters.map((f: BPRFilter) => f.value),
      }));
    }
  }, [multiFilter]);

  if (!locations) {
    return <VFLoader />;
  }

  return (
    <>
      <FilterGroup>
        <FilterColumn>
          <TextWrapper>For Location</TextWrapper>
          <DropDownWrapper style={{ gap: "20px" }}>
            <Select
              options={locationOptionsWithValue}
              isMulti
              closeMenuOnSelect={false}
              hideSelectedOptions={false}
              components={{
                Option: CustomOption,
                IndicatorSeparator: () => null,
                ClearIndicator: () => null,
              }}
              styles={{
                ...colorStyles,
                input: (base) => ({
                  ...base,
                  color: "#333",
                }),
                placeholder: (base) => ({
                  ...base,
                  color: "#999",
                  display: "block",
                }),
                menuList: (base) => ({
                  ...base,
                  maxHeight: 500,
                  overflowY: "auto",
                  scrollbarWidth: "thin",
                  scrollbarColor: "#888 transparent",

                  "&::-webkit-scrollbar": {
                    width: "6px",
                  },
                  "&::-webkit-scrollbar-thumb": {
                    backgroundColor: "#888",
                    borderRadius: "4px",
                  },
                  "&::-webkit-scrollbar-thumb:hover": {
                    backgroundColor: "#555",
                  },
                }),
              }}
              placeholder="Location Type"
              value={selectedOptions.ForLocation.map((option) => ({
                label: option,
                value: option,
              }))}
              onChange={(newValue) =>
                handleSelectChange({
                  newValue,
                  header: "ForLocation",
                  filterId: "SCF1",
                  parentId: "supplyChainFilter",
                })
              }
            />
          </DropDownWrapper>
        </FilterColumn>

        <FilterColumn>
          <TextWrapper>For Children Of</TextWrapper>
          <DropDownWrapper style={{ gap: "20px" }}>
            <Select
              options={locationOptionsWithValue}
              isMulti
              closeMenuOnSelect={false}
              hideSelectedOptions={false}
              components={{
                Option: CustomOption,
                IndicatorSeparator: () => null,
                ClearIndicator: () => null,
              }}
              styles={{
                ...colorStyles,
                input: (base) => ({
                  ...base,
                  color: "#333",
                }),
                placeholder: (base) => ({
                  ...base,
                  color: "#999",
                  display: "block",
                }),
                menuList: (base) => ({
                  ...base,
                  maxHeight: 500,
                  overflowY: "auto",
                  scrollbarWidth: "thin",
                  scrollbarColor: "#888 transparent",

                  "&::-webkit-scrollbar": {
                    width: "6px",
                  },
                  "&::-webkit-scrollbar-thumb": {
                    backgroundColor: "#888",
                    borderRadius: "4px",
                  },
                  "&::-webkit-scrollbar-thumb:hover": {
                    backgroundColor: "#555",
                  },
                }),
              }}
              placeholder="Location Type"
              value={selectedOptions.ForChildren.map((option) => ({
                label: option,
                value: option,
              }))}
              onChange={(newValue) =>
                handleSelectChange({
                  newValue,
                  header: "ForChildren",
                  filterId: "SCF2",
                  parentId: "supplyChainFilter",
                })
              }
            />
          </DropDownWrapper>
        </FilterColumn>
      </FilterGroup>
    </>
  );
};

export const useColorOptionStyles = () => {
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;
  const themeColor = theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80";

  return {
    checkbox: {
      width: "16px",
      height: "16px",
      accentColor: themeColor,
      cursor: "pointer",
      flexShrink: 0,
    },
    colorPanel: {
      width: "20px",
      height: "20px",
      borderRadius: "4px",
      border: "1px solid #ddd",
      flexShrink: 0,
      boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
      order: 2,
    },
    colorName: {
      fontSize: "14px",
      fontFamily: "Roboto, sans-serif",
      fontWeight: "400",
      color: "#333",
      flex: 1,
      textAlign: "left" as const,
      order: 1,
    },
    optionContainer: {
      display: "flex",
      alignItems: "center",
      gap: "10px",
      width: "100%",
      padding: "4px 0",
    },
  };
};
