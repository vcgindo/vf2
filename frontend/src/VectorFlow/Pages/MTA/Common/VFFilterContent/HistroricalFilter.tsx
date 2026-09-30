import React, { useState } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
  DropDownRow,
  IconWrapper,
} from "./style";
import Select from "react-select";
import {
  useThemeStyles,
} from "../../../../../hooks/useVFFilterContent";
import { numericOperators } from "./useVFFilterContent";
import { useUserData } from "../../../../../context";
import "./styles.css";

interface AvailabilityFilterProps {
  filters: any;
  onFilterChange: (field: string, value: any) => void;
  onApplyFilter: (filters: any) => void;
  initialFilters?: any;
}

export const HistroricalFilter: React.FC<AvailabilityFilterProps> = ({
  filters,
  onFilterChange,
}) => {
  const styles = useThemeStyles();
  const { user } = useUserData();

  return (
    <>
      <FilterGroup>
        <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
          <TextWrapper>Select Operation</TextWrapper>
          <DropDownRow>
            <DropDownWrapper>
              <Select
                placeholder={"VirtualNorm"}
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isDisabled={true}
                value={{ label: "Virtual Norm", value: "Virtual Norm" }}
                options={[]}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                options={numericOperators}
                placeholder={"Select an Operation"}
                styles={styles}
                components={{ IndicatorSeparator: () => null }}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder="Enter a value"
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isSearchable={true}
                inputValue={filters.someValue || ""}
                onInputChange={(inputValue) =>
                  onFilterChange("someValue", inputValue)
                }
                menuIsOpen={false}
                options={[]}
              />
            </DropDownWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/Error.svg"} />
            </IconWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/refresh.svg"} />
            </IconWrapper>
          </DropDownRow>
          <DropDownRow>
            <DropDownWrapper>
              <Select
                placeholder={"Norm"}
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isDisabled={true}
                value={{ label: "Norm", value: "Norm" }}
                options={[]}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder={"Select an Operation"}
                styles={styles}
                components={{ IndicatorSeparator: () => null }}
                options={numericOperators}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder="Enter a value"
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isSearchable={true}
                inputValue={filters.someValue || ""}
                onInputChange={(inputValue) =>
                  onFilterChange("someValue", inputValue)
                }
                menuIsOpen={false}
                options={[]}
              />
            </DropDownWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/Error.svg"} />
            </IconWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/refresh.svg"} />
            </IconWrapper>
          </DropDownRow>
          <DropDownRow>
            <DropDownWrapper>
              <Select
                placeholder={"Stock"}
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isDisabled={true}
                value={{ label: "Stock", value: "Stock" }}
                options={[]}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder={"Select an Operation"}
                styles={styles}
                components={{ IndicatorSeparator: () => null }}
                options={numericOperators}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder="Enter a value"
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isSearchable={true}
                inputValue={filters.someValue || ""}
                onInputChange={(inputValue) =>
                  onFilterChange("someValue", inputValue)
                }
                menuIsOpen={false}
                options={[]}
              />
            </DropDownWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/Error.svg"} />
            </IconWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/refresh.svg"} />
            </IconWrapper>
          </DropDownRow>
          <DropDownRow>
            <DropDownWrapper>
              <Select
                placeholder={"GIT"}
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isDisabled={true}
                value={{ label: "GIT", value: "GIT" }}
                options={[]}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder={"Select an Operation"}
                styles={styles}
                components={{ IndicatorSeparator: () => null }}
                options={numericOperators}
              />
            </DropDownWrapper>
            <DropDownWrapper>
              <Select
                placeholder="Enter a value"
                styles={styles}
                components={{
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                  Menu: () => null,
                }}
                isSearchable={true}
                inputValue={filters.someValue || ""}
                onInputChange={(inputValue) =>
                  onFilterChange("someValue", inputValue)
                }
                menuIsOpen={false}
                options={[]}
              />
            </DropDownWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/Error.svg"} />
            </IconWrapper>
            <IconWrapper theme_ui={user.user.theme_ui}>
              <img src={"/assets/img/MTAVFMultiFilter/refresh.svg"} />
            </IconWrapper>
          </DropDownRow>
        </FilterColumn>
      </FilterGroup>
    </>
  );
};
