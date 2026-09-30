import React, { useEffect, useState, useMemo, useRef } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
  DropDownRow,
  IconWrapper,
} from "./style";
import Select, { components } from "react-select";
import {
  useColorOptionStyles,
  useColorThemeStyles,
  useThemeStyles,
} from "../../../../../hooks/useVFFilterContent";
import {
  useFilterRows,
  stringOpertors,
  useRowCompletion,
  useMultiFilterChange,
} from "./useVFFilterContent";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import { useUserData } from "../../../../../context";
import { useSelector } from "react-redux";
import { RootState } from "../../../../../redux/store/store";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import {
  useGetAllLocations,
  useSearchWHDescription,
} from "../../../../../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import { MultiValue, ActionMeta } from "react-select";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";

interface FilterSectionProps {
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
}
interface LocationOption {
  label: string;
  value: string;
  id: string;
  originalData: any;
}

export const LocationFilters: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
}) => {
  const { user } = useUserData();
  const styles = useThemeStyles();

  const {
    filterRows,
    handleAddRow,
    handleRemoveRow,
    isMaxRows,
    isMinRows,
    setFilterRows,
    resetFilterRows,
  } = useFilterRows();

  const colorStyles = useColorThemeStyles({
    minWidth: "620px",
    minHeight: "48px",
    valueContainerPaddingLeft: "175px",
    inputColor: "#333",
    placeholderColor: "#999",
    menuListMaxHeight: 400,
    gridColumns: 2,
    menuWidth: "800px",
    gridGap: "12px",
    optionPadding: "8px 16px",
  });

  const EnvConfig = useSelector((state: RootState) => state.mta.EnvConfig);

  const LOCATION_PERMISSION_L1 = EnvConfig["LOCATION_PERMISSION_L1"];
  const LOCATION_PERMISSION_L2 = EnvConfig["LOCATION_PERMISSION_L2"];
  const LOCATION_PERMISSION_L3 = EnvConfig["LOCATION_PERMISSION_L3"];

  const filterLocationOptions = [
    { value: "l1", label: LOCATION_PERMISSION_L1, name: "LF1" },
    { value: "l2", label: LOCATION_PERMISSION_L2, name: "LF2" },
    { value: "l3", label: LOCATION_PERMISSION_L3, name: "LF3" },
  ];

  const [rowSelections, setRowSelections] = useState<{
    [rowId: number]: { column?: any; operation?: any; value?: any };
  }>({});

  const { isRowComplete } = useRowCompletion(rowSelections);

  const [rowFilterIndexMap, setRowFilterIndexMap] = useState<
    Record<number, number>
  >({});
  const [isInitialized, setIsInitialized] = useState(false);
  const [filterType, setFilterType] = useState<
    "Location Code" | "Location Description"
  >("Location Code");

  const [selectedLocations, setSelectedLocations] = useState<LocationOption[]>(
    []
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [manualSearchQuery, setManualSearchQuery] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const selectRef = useRef<any>(null);

  const { data: locationData, isLoading: isLocationDataLoading } =
    useGetAllLocations();

  const { data: searchData, refetch: triggerSearch } =
    useSearchWHDescription(manualSearchQuery);

  const targetSize = 2000;
  const locationDataSize = locationData?.data?.data?.length || 0;
  const shouldUseLocalData = locationDataSize <= targetSize;
  const shouldShowSearchButton = !shouldUseLocalData;

  const customFilterOption = (option: any, inputValue: string) => {
    if (!inputValue) return false;

    const searchTerm = inputValue.toLowerCase();
    const optionLabel = option.label.toLowerCase();
    const optionValue = option.value.toLowerCase();

    return optionLabel.includes(searchTerm) || optionValue.includes(searchTerm);
  };

  const localLocationOptions = useMemo((): LocationOption[] => {
    if (!locationData?.data?.data || !shouldUseLocalData) return [];

    return locationData.data.data.map((location: any) => {
      const label = filterType === "Location Code" ? location.wc : location.wd;
      return {
        label: label,
        value: location.wc,
        id: location.wc,
        originalData: location,
      };
    });
  }, [locationData, filterType, shouldUseLocalData]);

  const searchLocationOptions = useMemo((): LocationOption[] => {
    if (!searchData || shouldUseLocalData) return [];

    try {
      let results: any[] = [];

      if (Array.isArray(searchData)) {
        results = searchData;
      } else if (searchData && typeof searchData === "object") {
        if (searchData.data && Array.isArray(searchData.data)) {
          results = searchData.data;
        } else {
          results = Object.values(searchData);
        }
      } else {
        results = [];
      }

      return results.map((location: any) => {
        const label =
          filterType === "Location Code" ? location.wc : location.wd;
        return {
          label: label,
          value: location.wc,
          id: location.wc,
          originalData: location,
        };
      });
    } catch (error) {
      console.error("Error processing search results:", error);
      return [];
    }
  }, [searchData, filterType, shouldUseLocalData]);

  const locationOptions = shouldUseLocalData
    ? localLocationOptions
    : searchLocationOptions;

  const isLoading = shouldUseLocalData ? isLocationDataLoading : isSearching;

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

  const isUpdatingFromInternal = useRef(false);

  useEffect(() => {
    if (isUpdatingFromInternal.current) {
      isUpdatingFromInternal.current = false;
      return;
    }

    const parentId = "locationFilter";
    const savedFilters = multiFilter[parentId]?.filters || [];

    const savedLocationFilters = savedFilters.filter((f) => f.name === "LF6");
    const restoredLocations = savedLocationFilters.map((f) => ({
      value: f.value,
      label: f.label === "LocationCode" ? f.value : f.label,
      id: f.value,
      originalData: { wc: f.value, wd: f.label },
    }));
    setSelectedLocations(restoredLocations);

    const operationFilters = savedFilters.filter(
      (f) => !f.name.startsWith("LF6")
    );

    if (operationFilters.length === 0) {
      setRowSelections({});
      resetFilterRows(1);
      setRowFilterIndexMap({});
      setIsInitialized(true);
      return;
    }

    if (isInitialized) return;

    const newRows = operationFilters.map((_, idx) => ({ id: idx }));
    setFilterRows(newRows);

    const restored: {
      [rowId: number]: { column?: any; operation?: any; value?: any };
    } = {};
    const indexMap: Record<number, number> = {};

    operationFilters.forEach((f: BPRFilter, idx: number) => {
      const column = filterLocationOptions.find(
        (opt) => opt.value === f.attributeName
      );
      const operation = stringOpertors.find((op) => op.value === f.operator);

      restored[idx] = {
        column: column || null,
        operation: operation || null,
        value: f.value,
      };
      indexMap[idx] = idx;
    });

    setRowSelections(restored);
    setRowFilterIndexMap(indexMap);
    setIsInitialized(true);
  }, [multiFilter?.locationFilter?.filters, setFilterRows, resetFilterRows]);

  const { onFilterChange } = useMultiFilterChange({
    parentId: "locationFilter",
    prefix: "LF",
    rowSelections,
    setRowSelections,
    multiFilter,
    onMultiFilterChange,
    rowFilterIndexMap,
    setRowFilterIndexMap,
    isUpdatingFromInternal,
  });

  const handleRemoveRowWithFilter = (rowId: number) => {
    if (isMinRows) return;

    const parentId = "locationFilter";
    const existingFilters = (multiFilter[parentId]?.filters ||
      []) as BPRFilter[];
    const locationFilters = existingFilters.filter((f) => f.name === "LF6");

    handleRemoveRow(rowId);
    setRowSelections((prev) => {
      const updated = { ...prev };
      delete updated[rowId];

      const remainingRowIds = Object.keys(updated)
        .map(Number)
        .sort((a, b) => a - b);

      const newFilters: BPRFilter[] = [];
      const newIndexMap: Record<number, number> = {};

      remainingRowIds.forEach((rid, newIdx) => {
        const current = updated[rid];
        if (
          current?.column &&
          current?.operation &&
          (current.operation.value === "hasvalue" ||
            current.operation.value === "hasnovalue" ||
            (current.value !== undefined && current.value !== ""))
        ) {
          newFilters.push({
            attributeName: current.column.value,
            operator: current.operation.value,
            value:
              current.operation.value === "hasvalue"
                ? "hasvalue"
                : current.operation.value === "hasnovalue"
                ? "hasnovalue"
                : current.value,
            label: current.column.label,
            name: current.column.name,
          });
          newIndexMap[rid] = newIdx;
        }
      });

      setRowFilterIndexMap(newIndexMap);

      isUpdatingFromInternal.current = true;
      onMultiFilterChange({
        ...multiFilter,
        [parentId]: {
          ...multiFilter[parentId],
          filters: [...newFilters, ...locationFilters],
        },
      });

      return updated;
    });
  };

  const handleLocationSelectChange = (
    newValue: MultiValue<any>,
    actionMeta: ActionMeta<any>
  ) => {
    const selected = Array.isArray(newValue) ? [...newValue] : [];
    setSelectedLocations(selected);

    setSearchQuery("");
    setHasSearched(false);
    setManualSearchQuery("");

    const parentId = "locationFilter";
    const existingFilters = (multiFilter[parentId]?.filters ||
      []) as BPRFilter[];
    const operationFilters = existingFilters.filter(
      (f) => !f.name.startsWith("LF6")
    );

    const newFilters = selected.map((loc) => ({
      attributeName: "Location",
      value: loc.value,
      operator: "=",
      label: "LocationCode",
      name: "LF6",
    }));

    isUpdatingFromInternal.current = true;
    const updatedMultiFilter: BPRFilterState = {
      ...multiFilter,
      [parentId]: {
        ...multiFilter[parentId],
        filters: [...operationFilters, ...newFilters],
      },
    };

    onMultiFilterChange(updatedMultiFilter);
  };

  const handleSearchApply = async () => {
    if (searchQuery && searchQuery.length >= 2) {
      setIsSearching(true);
      setHasSearched(true);
      setManualSearchQuery(searchQuery);

      try {
        await triggerSearch();
        setTimeout(() => {
          if (selectRef.current) {
            selectRef.current.focus();
            if (selectRef.current.openMenu) {
              selectRef.current.openMenu();
            }
          }
        }, 100);
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        setIsSearching(false);
      }
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && !shouldUseLocalData) {
      handleSearchApply();
    }
  };

  const handleFilterTypeChange = (selected: any) => {
    setFilterType(selected.value);
    setSelectedLocations([]);
    setSearchQuery("");
    setManualSearchQuery("");
    setHasSearched(false);
    setIsSearching(false);

    const parentId = "locationFilter";
    const existingFilters = (multiFilter[parentId]?.filters ||
      []) as BPRFilter[];
    const operationFilters = existingFilters.filter(
      (f) => !f.name.startsWith("LF6")
    );

    isUpdatingFromInternal.current = true;
    const updatedMultiFilter: BPRFilterState = {
      ...multiFilter,
      [parentId]: {
        ...multiFilter[parentId],
        filters: operationFilters,
      },
    };

    onMultiFilterChange(updatedMultiFilter);
  };

  const handleInputChange = (inputValue: string, { action }: any) => {
    if (action === "input-change") {
      setSearchQuery(inputValue);
      if (hasSearched && inputValue.length < 2) {
        setManualSearchQuery("");
        setHasSearched(false);
        setIsSearching(false);
      }
    }
  };

  const getFilteredOptions = () => {
    if (!shouldUseLocalData) {
      return locationOptions;
    }

    if (!searchQuery) {
      return [];
    }

    return locationOptions.filter((option) =>
      customFilterOption(option, searchQuery)
    );
  };

  const filteredOptions = getFilteredOptions();

  if (!isInitialized) return null;

  if (!isInitialized) {
    return <VFLoader />;
  }

  return (
    <>
      <FilterGroup>
        <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
          <TextWrapper>Select Operation</TextWrapper>
          {filterRows.map((row) => (
            <DropDownRow key={row.id} style={{ alignItems: "center" }}>
              <DropDownWrapper>
                <Select
                  options={filterLocationOptions}
                  placeholder="Select Column"
                  styles={styles}
                  components={{ IndicatorSeparator: () => null }}
                  value={rowSelections[row.id]?.column || null}
                  onChange={(selected) =>
                    onFilterChange(row.id, "column", selected)
                  }
                />
              </DropDownWrapper>
              <DropDownWrapper>
                <Select
                  options={stringOpertors}
                  placeholder="Select Operation"
                  styles={styles}
                  isSearchable={false}
                  components={{ IndicatorSeparator: () => null }}
                  value={rowSelections[row.id]?.operation || null}
                  onChange={(selected) =>
                    onFilterChange(row.id, "operation", selected)
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
                  }${
                    rowSelections[row.id]?.operation?.value === "hasvalue" ||
                    rowSelections[row.id]?.operation?.value === "hasnovalue"
                      ? " filter-input--disabled"
                      : ""
                  }`}
                  value={rowSelections[row.id]?.value || ""}
                  onChange={(e) =>
                    onFilterChange(row.id, "value", e.target.value)
                  }
                  disabled={
                    rowSelections[row.id]?.operation?.value === "hasvalue" ||
                    rowSelections[row.id]?.operation?.value === "hasnovalue"
                  }
                />
              </DropDownWrapper>
              <div style={{ display: "flex", alignItems: "center" }}>
                <IconWrapper
                  theme_ui={user.user.theme_ui}
                  style={{
                    opacity: isRowComplete(row.id) ? 0 : 1,
                    cursor: isRowComplete(row.id) ? "default" : "pointer",
                  }}
                >
                  <img
                    src={"/assets/img/MTAVFMultiFilter/Error.svg"}
                    alt="error"
                    title={
                      isRowComplete(row.id)
                        ? "All fields are filled"
                        : "Must select a column."
                    }
                  />
                </IconWrapper>
                <IconWrapper
                  theme_ui={user.user.theme_ui}
                  disabled={isMaxRows}
                  onClick={handleAddRow}
                >
                  <img
                    src={"/assets/img/MTAVFMultiFilter/plus-sign-circle.svg"}
                    alt="add"
                  />
                </IconWrapper>
                <IconWrapper
                  theme_ui={user.user.theme_ui}
                  disabled={isMinRows}
                  onClick={() => handleRemoveRowWithFilter(row.id)}
                >
                  <img
                    src={"/assets/img/MTAVFMultiFilter/minus-sign-circle.svg"}
                    alt="remove"
                  />
                </IconWrapper>
              </div>
            </DropDownRow>
          ))}
        </FilterColumn>
      </FilterGroup>

      <FilterGroup style={{ paddingTop: "10px" }}>
        <FilterColumn>
          <TextWrapper>Select Location</TextWrapper>
          <DropDownRow>
            <DropDownWrapper style={{ flex: 1 }}>
              <Select
                ref={selectRef}
                placeholder={
                  shouldUseLocalData
                    ? "Type location code to search..."
                    : "Type to search locations and click Search button"
                }
                options={shouldUseLocalData ? filteredOptions : locationOptions}
                styles={{
                  ...colorStyles,
                  menu: (base) => ({
                    ...base,
                    minWidth: "620px",
                  }),
                  input: (base) => ({
                    ...base,
                    color: "#333",
                  }),
                }}
                components={{
                  Option: CustomOption,
                  IndicatorSeparator: () => null,
                  DropdownIndicator: () => null,
                }}
                isMulti
                isSearchable
                closeMenuOnSelect={false}
                hideSelectedOptions={false}
                value={selectedLocations}
                onChange={handleLocationSelectChange}
                onInputChange={handleInputChange}
                inputValue={searchQuery}
                onKeyDown={handleKeyPress}
                isLoading={isLoading}
                filterOption={
                  shouldUseLocalData ? customFilterOption : undefined
                }
                noOptionsMessage={({ inputValue }) =>
                  shouldUseLocalData
                    ? inputValue
                      ? "No locations found"
                      : "Start typing to search locations"
                    : inputValue && hasSearched 
                    ? "No locations found. Try a different search term."
                    : "Type to search and click Search button"
                }
              />

              <div style={{ width: 165, marginTop: -44, marginLeft: 4.5 }}>
                <Select
                  placeholder="Location Code"
                  styles={{
                    ...styles,
                    control: (base: any, state: any) => ({
                      ...base,
                      minHeight: "39px",
                      border: state.isFocused
                        ? user.user.theme_ui === "REGALBLAZE"
                          ? "2px solid #FCA311"
                          : "2px solid #BC3D80"
                        : "1px solid #c7c0c0ff",
                      borderRadius: "7px",
                      boxShadow: "none",
                      outline: "none",
                      "&:hover": {
                        border: state.isFocused
                          ? user.user.theme_ui === "REGALBLAZE"
                            ? "2px solid #FCA311"
                            : "2px solid #BC3D80"
                          : "1px solid #c7c0c0ff",
                      },
                    }),
                  }}
                  components={{ IndicatorSeparator: () => null }}
                  options={[
                    { value: "Location Code", label: "Location Code" },
                    {
                      value: "Location Description",
                      label: "Location Description",
                    },
                  ]}
                  value={{
                    value: filterType,
                    label: filterType,
                  }}
                  onChange={handleFilterTypeChange}
                />
              </div>
            </DropDownWrapper>

            {shouldShowSearchButton && (
              <VFButton
                themeUi={user.user.theme_ui}
                onClick={handleSearchApply}
                width={120}
                style={{
                  fontSize: 15,
                  fontWeight: 350,
                  height: 44,
                  marginBottom: 4,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                disabled={!searchQuery || searchQuery.length < 2 || isLoading}
              >
                <div
                  style={{ display: "flex", alignItems: "center", gap: "6px" }}
                >
                  <img
                    src={"/assets/img/MTAVFMultiFilter/Search-white.svg"}
                    alt="search"
                    style={{ width: 16, height: 16 }}
                  />
                  <span>{isLoading ? "Searching..." : "Search"}</span>
                </div>
              </VFButton>
            )}
          </DropDownRow>
        </FilterColumn>
      </FilterGroup>
    </>
  );
};
