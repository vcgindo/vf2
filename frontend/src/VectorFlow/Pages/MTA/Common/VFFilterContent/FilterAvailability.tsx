import React, { useEffect, useState } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
  DropDownRow,
  IconWrapper,
  CheckboxWrapper,
} from "./style";
import Select, { components } from "react-select";
import {
  useThemeStyles,
  useColorThemeStyles,
  useColorOptionStyles,
} from "../../../../../hooks/useVFFilterContent";
import {
  numericOperators,
  colorOptions,
  useVFMultiFilter,
  categoryOptions,
  availabilityFilterOptions,
} from "./useVFFilterContent";
import { useUserData } from "../../../../../context";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import "./styles.css";

interface AvailabilityFilterProps {
  filters: any;
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
  currentTab?: string;
  currCategory?: string;
}
interface TagsFilterProps {
  name: string;
  checked: boolean;
  onChange: (name: string, checked: boolean) => void;
}

const CustomCategoryOption = (props: any) => {
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
        <div
          style={{
            ...optionStyles.colorPanel,
            backgroundColor: props.data.color || "#ccc",
          }}
        />
        <span style={optionStyles.colorName}>{props.data.label}</span>
      </div>
    </components.Option>
  );
};

const CustomMultiValue = (props: any) => {
  return (
    <components.MultiValue {...props}>
      <span
        style={{
          backgroundColor: props.data.color,
          width: "12px",
          height: "12px",
          borderRadius: "3px",
          display: "inline-block",
          marginRight: "5px",
        }}
      />
      {props.children}
    </components.MultiValue>
  );
};

const TagsFilter: React.FC<TagsFilterProps> = ({ name, checked, onChange }) => {
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;
  const themeColor = theme_ui === "REGALBLAZE" ? "#FCA311" : "#BC3D80";

  const handleClick = () => {
    onChange(name, !checked);
  };

  return (
    <CheckboxWrapper
      style={{
        alignItems: "center",
        gap: "8px",
        cursor: "pointer",
        backgroundColor: checked ? `${themeColor}15` : "white",
        borderColor: checked ? themeColor : "#c7c0c0ff",
        borderWidth: checked ? "2px" : "1px",
        boxShadow: checked ? `0 2px 8px ${themeColor}25` : "none",
      }}
      onClick={handleClick}
    >
      <input
        style={{
          height: "18px",
          width: "18px",
          accentColor: themeColor,
          pointerEvents: "none",
        }}
        type="checkbox"
        id={name.toLowerCase()}
        checked={checked}
        onChange={() => {
          console.log("Clicked");
        }}
        readOnly
      />
      <label
        style={{
          marginTop: "1px",
          cursor: "pointer",
          userSelect: "none",
          color: checked ? themeColor : "black",
          fontWeight: checked ? "600" : "400",
          transition: "all 0.1s ease-in-out",
        }}
        htmlFor={name.toLowerCase()}
      >
        {name}
      </label>
    </CheckboxWrapper>
  );
};

export const AvailabilityFilters: React.FC<AvailabilityFilterProps> = ({
  multiFilter,
  onMultiFilterChange,
  currentTab = "both",
  currCategory,
}) => {
  const styles = useThemeStyles();
  const colorStyles = useColorThemeStyles();
  const { user } = useUserData();
  const availabilityTags = ["PIPO", "Seasonality"];
  const { handleSelectChange} =
    useVFMultiFilter({
      multiFilter,
      onMultiFilterChange,
    });
  const [rowSelections, setRowSelections] = useState<{
    [columnId: string]: { operation?: any; value?: string };
  }>({});
  
  const isRowComplete = (columnId: string) => {
    const row = rowSelections[columnId];
    return row && row.operation && row.value && row.value.trim() !== "";
  };

  const onFilterChange = (
    columnId: string,
    field: "operation" | "value",
    selected: any
  ) => {
    const updated = {
      ...rowSelections,
      [columnId]: { ...rowSelections[columnId], [field]: selected },
    };
    setRowSelections(updated);

    const parentId = "availabilityFilter";
    const columnInfo = availabilityFilterOptions.find(
      (col) => col.value === columnId
    );
    const current = updated[columnId];

    if (
      columnInfo &&
      current?.operation &&
      current.value?.trim() !== undefined &&
      current?.value !== ""
    ) {
      const newFilter: BPRFilter = {
        attributeName: columnId,
        value: current.value,
        operator: current.operation.value,
        label: columnInfo.label,
        name: columnInfo.name,
      };

      const existingFilters = multiFilter[parentId]?.filters || [];
      const filteredFilters = existingFilters.filter(
        (f: BPRFilter) => f.name !== columnInfo.name
      );

      const updatedMultiFilter = {
        ...multiFilter,
        [parentId]: {
          ...multiFilter[parentId],
          filters: [...filteredFilters, newFilter],
        },
      };

      onMultiFilterChange(updatedMultiFilter);
    } else if (columnInfo) {
      const existingFilters = multiFilter[parentId]?.filters || [];
      const filteredFilters = existingFilters.filter(
        (f: BPRFilter) => f.name !== columnInfo.name
      );

      if (existingFilters.length !== filteredFilters.length) {
        const updatedMultiFilter = {
          ...multiFilter,
          [parentId]: {
            ...multiFilter[parentId],
            filters: filteredFilters,
          },
        };
        onMultiFilterChange(updatedMultiFilter);
      }
    }
  };

  const handleResetRow = (columnId: string) => {
    const updated = {
      ...rowSelections,
      [columnId]: { operation: null, value: "" },
    };
    setRowSelections(updated);

    const parentId = "availabilityFilter";
    const columnInfo = availabilityFilterOptions.find(
      (col) => col.value === columnId
    );

    if (columnInfo) {
      const existingFilters = multiFilter[parentId]?.filters || [];
      const filteredFilters = existingFilters.filter(
        (f: BPRFilter) => f.name !== columnInfo.name
      );

      const updatedMultiFilter = {
        ...multiFilter,
        [parentId]: {
          ...multiFilter[parentId],
          filters: filteredFilters,
        },
      };

      onMultiFilterChange(updatedMultiFilter);
    }
  };

  const [selectedOptions, setSelectedOptions] = useState<{
    onHandInventoryColor: string[];
    pipelineInventoryColor: string[];
    category: string[];
  }>({
    onHandInventoryColor: [],
    pipelineInventoryColor: [],
    category: [],
  });

  useEffect(() => {
    if (multiFilter?.availabilityFilter?.filters) {
      const restoredRowSelections: {
        [columnId: string]: { operation?: any; value?: string };
      } = {};

      const forOnHandInventoryColor =
        multiFilter.availabilityFilter.filters.filter(
          (f: BPRFilter) => f.name === "AF5"
        );
      const forPipelineInventoryColor =
        multiFilter.availabilityFilter.filters.filter(
          (f: BPRFilter) => f.name === "AF6"
        );
      const forTags = multiFilter.availabilityFilter.filters.filter(
        (f: BPRFilter) => f.name === "AF7"
      );
      const forCategory = multiFilter.availabilityFilter.filters.filter(
        (f: BPRFilter) => f.name === "AF8"
      );

      availabilityFilterOptions.forEach((column) => {
        const savedFilter = multiFilter.availabilityFilter.filters.find(
          (f: BPRFilter) => f.name === column.name
        );

        if (savedFilter) {
          const operation = numericOperators.find(
            (op) => op.value === savedFilter.operator
          );

          restoredRowSelections[column.value] = {
            operation: operation || null,
            value: savedFilter.value,
          };
        }
      });
      setRowSelections(restoredRowSelections);

      setSelectedOptions({
        onHandInventoryColor: forOnHandInventoryColor.map((f) => f.value),
        pipelineInventoryColor: forPipelineInventoryColor.map((f) => f.value),
        category: forCategory.map((f) => f.value),
      });

      const activeTags = forTags.map((f) => f.value);
      setTagStates({
        PIPO: activeTags.includes("PIPO"),
        Seasonality: activeTags.includes("Seasonality"),
      });
    }
  }, [multiFilter?.availabilityFilter?.filters]);

  const [tagStates, setTagStates] = useState<{ [key: string]: boolean }>({
    PIPO: false,
    Seasonality: false,
  });

  const handleTagChange = (name: string, checked: boolean) => {
    setTagStates((prev) => ({
      ...prev,
      [name]: checked,
    }));

    const newValue = [
      ...Object.entries({
        ...tagStates,
        [name]: checked,
      })
        .filter(([_, val]) => val) 
        .map(([key]) => ({ label: key, value: key })),
    ];

    handleSelectChange({
      newValue,
      header: "Tags",
      filterId: "AF7",
      parentId: "availabilityFilter",
      attributeName: "PIPO,Seasonality",
    });
  };

  const isBTRReport = window.location.pathname === '/mta/insights-and-trends/buffer-trend-report';

  const shouldShowColorFilters = currCategory === 'BPR' || currCategory === 'BOR' || currCategory === 'RRR';

  const shouldShowTags = currCategory === 'BPR';

  return (
    <>
      <FilterGroup>
        <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
          <TextWrapper>Select Operation</TextWrapper>
          {availabilityFilterOptions.map((column) => (
            <DropDownRow key={column.value}>
              <DropDownWrapper>
                <Select
                  placeholder={column.label}
                  styles={styles}
                  components={{
                    IndicatorSeparator: () => null,
                    DropdownIndicator: () => null,
                    Menu: () => null,
                  }}
                  isDisabled={true}
                  value={{ label: column.label, value: column.value }}
                />
              </DropDownWrapper>
              <DropDownWrapper>
                <Select
                  options={numericOperators}
                  placeholder="Select an Operation"
                  styles={styles}
                  isSearchable={false}
                  components={{ IndicatorSeparator: () => null }}
                  value={rowSelections[column.value]?.operation || null}
                  onChange={(selected) =>
                    onFilterChange(column.value, "operation", selected)
                  }
                />
              </DropDownWrapper>
              <DropDownWrapper>
                <input
                  placeholder="Enter value"
                  className={`filter-input ${
                    user.user.theme_ui === "REGALBLAZE"
                      ? "filter-input--regal"
                      : "filter-input--default"
                  }`}
                  value={rowSelections[column.value]?.value || ""}
                  onChange={(e) =>
                    onFilterChange(column.value, "value", e.target.value)
                  }
                />
              </DropDownWrapper>
              
              <IconWrapper 
                theme_ui={user.user.theme_ui}
                style={{
                  opacity: isRowComplete(column.value) ? 0 : 1,
                  cursor: isRowComplete(column.value) ? "default" : "pointer",
                }}
              >
                <img 
                  src="/assets/img/MTAVFMultiFilter/Error.svg" 
                  alt="error" 
                  title={isRowComplete(column.value) ? "All fields are filled" : "Must select a column."}
                />
              </IconWrapper>

              <IconWrapper 
                theme_ui={user.user.theme_ui}
                style={{ cursor: 'pointer' }}
                onClick={() => handleResetRow(column.value)}
              >
                <img
                  src="/assets/img/MTAVFMultiFilter/refresh.svg"
                  alt="refresh"
                  title="Reset this filter row"
                />
              </IconWrapper>
            </DropDownRow>
          ))}
        </FilterColumn>
      </FilterGroup>

      {(shouldShowColorFilters || isBTRReport) && (
        <FilterGroup style={{ marginTop: "1px" }}>
          <FilterColumn>
            <div style={{ 
              display: "flex", 
              gap: "20px", 
              alignItems: "flex-start",
              flexWrap: "wrap" 
            }}>
              {(currentTab === 'on-hand' || currentTab === 'both' || currCategory === 'BPR' || currCategory === 'RRR' || currCategory === 'BOR' || (isBTRReport && (currentTab === 'on-hand' || currentTab === 'both'))) && (
                <div style={{ 
                  flex: (currentTab === 'both') ? 1 : 'auto', 
                  minWidth: "280px",
                  maxWidth: (currentTab === 'both') ? "calc(50% - 10px)" : "100%"
                }}>
                  <TextWrapper>On Hand Inventory Color</TextWrapper>
                  <DropDownWrapper>
                    <Select
                      options={colorOptions}
                      isMulti
                      closeMenuOnSelect={false}
                      hideSelectedOptions={false}
                      components={{
                        Option: CustomOption,
                        MultiValue: CustomMultiValue,
                        IndicatorSeparator: () => null,
                        ClearIndicator: () => null,
                      }}
                      styles={colorStyles}
                      placeholder="Select Color"
                      value={colorOptions.filter((opt) =>
                        selectedOptions.onHandInventoryColor.includes(opt.value)
                      )}
                      onChange={(newValue) =>
                        handleSelectChange({
                          newValue,
                          header: "OHIC",
                          filterId: "AF5",
                          parentId: "availabilityFilter",
                        })
                      }
                    />
                  </DropDownWrapper>
                </div>
              )}

              {(currentTab === 'pipeline' || currentTab === 'both' || currCategory === 'BOR' || currCategory === 'BPR' || currCategory === 'RRR' || (isBTRReport && (currentTab === 'pipeline' || currentTab === 'both'))) && (
                <div style={{ 
                  flex: (currentTab === 'both') ? 1 : 'auto', 
                  minWidth: "280px",
                  maxWidth: (currentTab === 'both') ? "calc(50% - 10px)" : "100%"
                }}>
                  <TextWrapper>Pipeline Inventory Color</TextWrapper>
                  <DropDownWrapper>
                    <Select
                      options={colorOptions}
                      isMulti
                      closeMenuOnSelect={false}
                      hideSelectedOptions={false}
                      components={{
                        Option: CustomOption,
                        MultiValue: CustomMultiValue,
                        IndicatorSeparator: () => null,
                        ClearIndicator: () => null,
                      }}
                      styles={colorStyles}
                      placeholder="Select Color"
                      value={colorOptions.filter((opt) =>
                        selectedOptions.pipelineInventoryColor.includes(opt.value)
                      )}
                      onChange={(newValue) =>
                        handleSelectChange({
                          newValue,
                          header: "PIC",
                          filterId: "AF6",
                          parentId: "availabilityFilter",
                        })
                      }
                    />
                  </DropDownWrapper>
                </div>
              )}
            </div>
          </FilterColumn>
        </FilterGroup>
      )}

      {(shouldShowTags || (isBTRReport && (currentTab === 'both' || currentTab === 'pipeline' || currentTab === 'on-hand'))) && (
        <FilterGroup style={{ marginTop: "1px" }}>
          <FilterColumn>
            <TextWrapper>Tags</TextWrapper>
            <DropDownRow style={{ gap: "20px" }}>
              {availabilityTags.map((tag) => (
                <TagsFilter
                  key={tag}
                  name={tag}
                  checked={tagStates[tag]}
                  onChange={handleTagChange}
                />
              ))}
            </DropDownRow>
          </FilterColumn>
        </FilterGroup>
      )}

      {isBTRReport && (
        <FilterGroup style={{ marginTop: "1px" }}>
          <FilterColumn>
            <TextWrapper>Category</TextWrapper>
            <DropDownWrapper style={{ gap: "20px" }}>
              <Select
                options={categoryOptions}
                isMulti
                closeMenuOnSelect={false}
                hideSelectedOptions={false}
                components={{
                  Option: CustomCategoryOption,
                  IndicatorSeparator: () => null,
                  ClearIndicator: () => null,
                }}
                styles={{
                  ...colorStyles,
                  menuList: (base) => ({
                    ...base,
                    maxHeight: 150,
                    overflowY: "auto",
                  }),
                }}
                placeholder="Select Category"
                value={categoryOptions.filter((opt) =>
                  selectedOptions.category.includes(opt.value)
                )}
                onChange={(newValue) =>
                  handleSelectChange({
                    newValue,
                    header: "Category",
                    filterId: "AF8",
                    parentId: "availabilityFilter",
                  })
                }
              />
            </DropDownWrapper>
          </FilterColumn>
        </FilterGroup>
      )}
    </>
  );
};