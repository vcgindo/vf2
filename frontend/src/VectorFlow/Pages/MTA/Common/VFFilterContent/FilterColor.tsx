import React, { useState, useEffect, useRef } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
  DropDownRow,
  IconWrapper,
} from "./style";
import Select from "react-select";
import { useThemeStyles } from "../../../../../hooks/useVFFilterContent";
import { colorFilterOptions, numericOperators } from "./useVFFilterContent";
import { useUserData } from "../../../../../context";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import { useDispatch } from "react-redux";
import { UPDATE_MTA_VF_MULTI_FILTER } from "../../../../../redux/actions/MTA";

interface FilterSectionProps {
  filters: any;
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
}

interface FilterRowState {
  id: string;
  type: string;
  attributeName: string;
  operator: string;
  value: string;
}

const INITIAL_ROWS: FilterRowState[] = [
  { id: "CF1", type: "", attributeName: "", operator: "", value: "" },
  { id: "CF2", type: "", attributeName: "", operator: "", value: "" },
  { id: "CF3", type: "", attributeName: "", operator: "", value: "" },
];

export const ColorFilters: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
}) => {
  const styles = useThemeStyles();
  const { user } = useUserData();
  const isUpdatingFromInternal = useRef(false);

  const [filterRows, setFilterRows] = useState<FilterRowState[]>(INITIAL_ROWS);
  const dispatch = useDispatch();
  const colorTypeFilterOptions = [
    { value: "colorcount", label: "Color Count" },
    { value: "colorage", label: "Color Age" },
  ];

  const isRowComplete = (row: FilterRowState) => {
    return row.type && row.attributeName && row.operator && row.value && row.value.trim() !== "";
  };

  useEffect(() => {
    if (isUpdatingFromInternal.current) {
      isUpdatingFromInternal.current = false;
      return;
    }

    if (multiFilter?.colorFilter?.filters && multiFilter.colorFilter.filters.length > 0) {
      const restoredRows: FilterRowState[] = [...INITIAL_ROWS];

      multiFilter.colorFilter.filters.forEach((filter: BPRFilter) => {
        if (filter.name && filter.name.startsWith("CF")) {
          const rowIndex = parseInt(filter.name.replace("CF", "")) - 1;
          if (rowIndex >= 0 && rowIndex < 3) {
            restoredRows[rowIndex] = {
              id: filter.name,
              type: filter.type || "",
              attributeName: filter.attributeName || "",
              operator: filter.operator || "",
              value: filter.value || "",
            };
          }
        }
      });

      setFilterRows(restoredRows);
    } else {
      setFilterRows([...INITIAL_ROWS]);
    }
  }, [multiFilter?.colorFilter?.filters]);

  const handleFilterChange = (
    rowId: string,
    field: keyof FilterRowState,
    value: string
  ) => {
    const updatedRows = filterRows.map((row) => {
      if (row.id === rowId) {
        return {
          ...row,
          [field]: value,
        };
      }
      return row;
    });

    setFilterRows(updatedRows);

    const updatedRow = updatedRows.find(r => r.id === rowId);
    
    if (updatedRow) {
      const updatedMultiFilter = { ...multiFilter };

      if (!updatedMultiFilter.colorFilter) {
        updatedMultiFilter.colorFilter = {
          id: "6",
          label: "Color",
          filters: [],
        };
      } else {
        updatedMultiFilter.colorFilter = { ...updatedMultiFilter.colorFilter };
      }

      const existingFilters = updatedMultiFilter.colorFilter.filters ? [...updatedMultiFilter.colorFilter.filters] : [];
      const filteredFilters = existingFilters.filter(
        (f: BPRFilter) => f.name !== rowId
      );

      if (isRowComplete(updatedRow)) {
        const filterObj: BPRFilter = {
          type: updatedRow.type,
          attributeName: updatedRow.attributeName,
          value: updatedRow.value,
          operator: updatedRow.operator,
          label: updatedRow.type,
          name: updatedRow.id,
        };

        updatedMultiFilter.colorFilter.filters = [...filteredFilters, filterObj];
      } else {
        updatedMultiFilter.colorFilter.filters = filteredFilters;
      }
      isUpdatingFromInternal.current = true;
      onMultiFilterChange(updatedMultiFilter);
      dispatch(UPDATE_MTA_VF_MULTI_FILTER(updatedMultiFilter))
    }
  };

  const handleSelectChange = (
    rowId: string,
    field: keyof FilterRowState,
    selectedOption: any
  ) => {
    handleFilterChange(rowId, field, selectedOption?.value || "");
  };

  const handleResetRow = (rowId: string) => {
    const updatedRows = filterRows.map((row) => {
      if (row.id === rowId) {
        return {
          ...row,
          type: "",
          attributeName: "",
          operator: "",
          value: "",
        };
      }
      return row;
    });

    setFilterRows(updatedRows);

    const updatedMultiFilter = { ...multiFilter };
    
    if (updatedMultiFilter.colorFilter?.filters) {
      updatedMultiFilter.colorFilter = { ...updatedMultiFilter.colorFilter };
      const filteredFilters = updatedMultiFilter.colorFilter.filters.filter(
        (f: BPRFilter) => f.name !== rowId
      );
      
      updatedMultiFilter.colorFilter.filters = filteredFilters;
      
      isUpdatingFromInternal.current = true;
      onMultiFilterChange(updatedMultiFilter);
      dispatch(UPDATE_MTA_VF_MULTI_FILTER(updatedMultiFilter))
    }
  };

  return (
    <>
      <FilterGroup>
        <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
          <TextWrapper>Color Filter</TextWrapper>

          {filterRows.map((row) => {
            const isComplete = isRowComplete(row);

            return (
              <DropDownRow key={row.id} style={{ alignItems: "center" }}>
                <DropDownWrapper>
                  <Select
                    placeholder={"Select Type"}
                    styles={styles}
                    isSearchable={false}
                    components={{ IndicatorSeparator: () => null }}
                    options={colorTypeFilterOptions}
                    value={
                      colorTypeFilterOptions.find(
                        (opt) => opt.value === row.type
                      ) || null
                    }
                    onChange={(selectedOption) =>
                      handleSelectChange(row.id, "type", selectedOption)
                    }
                  />
                </DropDownWrapper>

                <DropDownWrapper>
                  <Select
                    options={colorFilterOptions}
                    placeholder={"Select Color"}
                    styles={styles}
                    isSearchable={false}
                    components={{ IndicatorSeparator: () => null }}
                    value={
                      colorFilterOptions.find(
                        (opt) => opt.value === row.attributeName
                      ) || null
                    }
                    onChange={(selectedOption) =>
                      handleSelectChange(
                        row.id,
                        "attributeName",
                        selectedOption
                      )
                    }
                  />
                </DropDownWrapper>

                <DropDownWrapper>
                  <Select
                    options={numericOperators}
                    placeholder={"Select OP"}
                    styles={styles}
                    isSearchable={false}
                    components={{ IndicatorSeparator: () => null }}
                    value={
                      numericOperators.find(
                        (opt) => opt.value === row.operator
                      ) || null
                    }
                    onChange={(selectedOption) =>
                      handleSelectChange(row.id, "operator", selectedOption)
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
                    value={row.value}
                    onChange={(e) =>
                      handleFilterChange(row.id, "value", e.target.value)
                    }
                  />
                </DropDownWrapper>

                <IconWrapper
                  theme_ui={user.user.theme_ui}
                  style={{
                    opacity: isComplete ? 0 : 1,
                    cursor: isComplete ? "default" : "pointer",
                  }}
                >
                  <img 
                    src={"/assets/img/MTAVFMultiFilter/Error.svg"}
                    alt="error"
                    title={isComplete ? "All fields are filled" : "Must select a column."}
                  />
                </IconWrapper>

                <IconWrapper
                  theme_ui={user.user.theme_ui}
                  onClick={() => handleResetRow(row.id)}
                  style={{ cursor: "pointer" }}
                >
                  <img 
                    src={"/assets/img/MTAVFMultiFilter/refresh.svg"}
                    alt="refresh"
                    title="Reset this filter row"
                  />
                </IconWrapper>
              </DropDownRow>
            );
          })}
        </FilterColumn>
      </FilterGroup>
    </>
  );
};