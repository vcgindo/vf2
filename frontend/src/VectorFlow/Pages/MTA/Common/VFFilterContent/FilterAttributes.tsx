import React, { useEffect, useState, useRef } from "react";
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
import {
  useFilterRows,
  stringOpertors,
  useRowCompletion,
  useMultiFilterChange,
} from "./useVFFilterContent";
import { useUserData } from "../../../../../context";
import { useGetUIConfigData } from "../../../../Services/MTA/Common/UIConfig";
import { UIColumnConfigName } from "../../../../../helpers/Enum";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader";
import NoAttributesFilters from "./NoAttributesData";

interface FilterSectionProps {
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
  reportName: UIColumnConfigName;
}

export const AttributesFilters: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
  reportName,
}) => {
  const { user } = useUserData();
  const styles = useThemeStyles();
  const { mutateAsync: getUiConfig } = useGetUIConfigData();

  const {
    filterRows,
    handleAddRow,
    handleRemoveRow,
    isMaxRows,
    isMinRows,
    setFilterRows,
    resetFilterRows,
  } = useFilterRows();

  const [attributeOptions, setAttributeOptions] = useState<any[]>([]);
  const [rowSelections, setRowSelections] = useState<
    Record<number, { column?: any; operation?: any; value?: any }>
  >({});
  const [rowFilterIndexMap, setRowFilterIndexMap] = useState<
    Record<number, number>
  >({});
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const commonFilterKeywords = ["skulocattr", "skuattr", "locattr"];
  const isUpdatingFromInternal = useRef(false);

  const { isRowComplete } = useRowCompletion(rowSelections);

  useEffect(() => {
    const loadAttributes = async () => {
      setIsLoading(true);
      try {
        const resCurrent = await getUiConfig(reportName);
        const currentData =
          resCurrent?.data?.data?.data || resCurrent?.data?.data || [];

        const currentAttributes = currentData.filter((col: any) =>
          commonFilterKeywords.some((kw) =>
            col.Col_Code?.toLowerCase()?.includes(kw)
          )
        );

        let finalAttributes = currentAttributes;

        if (currentAttributes.length === 0) {
          const resBPR = await getUiConfig(UIColumnConfigName.BPR);

          const bprData = resBPR?.data?.data?.data || resBPR?.data?.data || [];

          const bprAttributes = bprData.filter((col: any) =>
            commonFilterKeywords.some((kw) =>
              col.Col_Code?.toLowerCase()?.includes(kw)
            )
          );

          finalAttributes = bprAttributes;
        }

        const formatted = finalAttributes.map((col: any, idx: number) => ({
          value: col.Col_Code,
          label: col.Header || col.Col_Code,
          name: `CAF${idx + 1}`,
        }));

        setAttributeOptions(formatted);
      } catch (err) {
        console.error(
          `Error loading UIConfig attributes for ${reportName}`,
          err
        );
        setAttributeOptions([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadAttributes();
  }, [getUiConfig, reportName]);

  useEffect(() => {
    if (isUpdatingFromInternal.current) {
      isUpdatingFromInternal.current = false;
      return;
    }

    const hasFilters =
      multiFilter?.customAttributeFilter?.filters?.length > 0 || false;
    if (!hasFilters) {
      setRowSelections({});
      resetFilterRows(1);
      setRowFilterIndexMap({});
      setIsInitialized(false);
    }
  }, [multiFilter?.customAttributeFilter?.filters, resetFilterRows]);

  useEffect(() => {
    if (attributeOptions.length === 0 || isInitialized) return;

    const parentId = "customAttributeFilter";
    const savedFilters = multiFilter[parentId]?.filters || [];

    if (savedFilters.length === 0) {
      setRowSelections({});
      resetFilterRows(1);
      setRowFilterIndexMap({});
      setIsInitialized(true);
      return;
    }

    const newRows = savedFilters.map((_, idx) => ({ id: idx }));
    setFilterRows(newRows);

    const restored: Record<
      number,
      { column?: any; operation?: any; value?: any }
    > = {};
    const indexMap: Record<number, number> = {};

    savedFilters.forEach((f: BPRFilter, idx: number) => {
      const column = attributeOptions.find(
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
  }, [
    attributeOptions,
    multiFilter?.customAttributeFilter?.filters,
    isInitialized,
    resetFilterRows,
    setFilterRows,
  ]);

  const { onFilterChange } = useMultiFilterChange({
    parentId: "customAttributeFilter",
    prefix: "CAF",
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

    const parentId = "customAttributeFilter";
    const existingFilters = (multiFilter[parentId]?.filters ||
      []) as BPRFilter[];
    const idx = rowFilterIndexMap[rowId];
    const nextFilters = existingFilters.slice();
    const newIndexMap = { ...rowFilterIndexMap };

    if (typeof idx === "number" && idx >= 0 && idx < nextFilters.length) {
      nextFilters.splice(idx, 1);
      Object.keys(newIndexMap).forEach((k) => {
        const rid = Number(k);
        if (rid === rowId) return;
        if (newIndexMap[rid] > idx) newIndexMap[rid] = newIndexMap[rid] - 1;
      });
    }

    handleRemoveRow(rowId);
    setRowSelections((prev) => {
      const copy = { ...prev };
      delete copy[rowId];
      return copy;
    });
    delete newIndexMap[rowId];
    setRowFilterIndexMap(newIndexMap);

    isUpdatingFromInternal.current = true;
    onMultiFilterChange({
      ...multiFilter,
      [parentId]: { ...multiFilter[parentId], filters: nextFilters },
    });
  };

  if (isLoading) {
    return <VFLoader />;
  }

  if (!isLoading && attributeOptions.length === 0) {
    return <NoAttributesFilters reportName={reportName} />;
  }

  return (
    <FilterGroup>
      <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
        <TextWrapper>Select Attributes - SKU/Location</TextWrapper>
        {filterRows.map((row) => (
          <DropDownRow key={row.id} style={{ alignItems: "center" }}>
            <DropDownWrapper>
              <Select
                options={attributeOptions}
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
  );
};
