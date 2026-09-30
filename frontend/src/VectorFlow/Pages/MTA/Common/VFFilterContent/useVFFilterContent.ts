import { MutableRefObject, useCallback, useState } from 'react';
import { BPRFilterState, BPRFilter } from "../../../../types/BPR";
interface FilterRow {
  id: number;
}

interface UseVFMultiFilterProps {
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
}

interface SelectChangeParams {
  newValue: any;
  header: string;
  filterId: string;
  parentId: keyof BPRFilterState;
  attributeName?: string;
}

interface RowData {
  column?: any;
  operation?: any;
  value?: any;
}

interface RowSelections {
  [rowId: number]: RowData;
}

interface FilterChangeProps {
  parentId: keyof BPRFilterState;
  prefix: string;
  rowSelections: Record<number, any>;
  setRowSelections: React.Dispatch<React.SetStateAction<Record<number, any>>>;
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
  rowFilterIndexMap: Record<number, number>;
  setRowFilterIndexMap: React.Dispatch<React.SetStateAction<Record<number, number>>>;
  isUpdatingFromInternal: MutableRefObject<boolean>;
}

export const useFilterRows = (initialCount = 1, maxRows = 5) => {
  const [filterRows, setFilterRows] = useState<FilterRow[]>(
    Array(initialCount)
      .fill(null)
      .map((_, idx) => ({ id: idx }))
  );

  const addFilterRow = useCallback(() => {
    setFilterRows((prev) => {
      if (prev.length >= maxRows) return prev;
      const newId =
        prev.length > 0 ? Math.max(...prev.map((r) => r.id)) + 1 : 0;
      return [...prev, { id: newId }];
    });
  }, [maxRows]);

  const removeFilterRow = useCallback((id: number) => {
    setFilterRows((prev) =>
      prev.length > 1 ? prev.filter((row) => row.id !== id) : prev
    );
  }, []);

  const resetFilterRows = useCallback((count: number) => {
    setFilterRows(
      Array(count)
        .fill(null)
        .map((_, idx) => ({ id: idx }))
    );
  }, []);

  const handleAddRow = useCallback(() => {
    if (filterRows.length < maxRows) addFilterRow();
  }, [filterRows.length, maxRows, addFilterRow]);

  const handleRemoveRow = useCallback(
    (rowId: number) => {
      if (filterRows.length > 1) removeFilterRow(rowId);
    },
    [filterRows.length, removeFilterRow]
  );

  return {
    filterRows,
    setFilterRows,
    addFilterRow,
    removeFilterRow,
    resetFilterRows,
    handleAddRow,
    handleRemoveRow,
    isMaxRows: filterRows.length >= maxRows,
    isMinRows: filterRows.length <= 1,
  };
};

export const stringOpertors = [
  { label: "Equal to", value: "equalto" },
  { label: "Not Equal to", value: "notequalto" },
  { label: "Contains", value: "contains" },
  { label: "Does not contain", value: "doesnotcontain" },
  { label: "Starts With", value: "startswith" },
  { label: "Does not start with", value: "doesnotstartwith" },
  { label: "Ends with", value: "endswith" },
  { label: "Does not end with", value: "doesnotendwith" },
  { label: "Has value", value: "hasvalue" },
  { label: "Has no value", value: "hasnovalue" },
]

export const numericOperators = [
  { label: "Equal to", value: "equalto" },
  { label: "Greater than", value: "greaterthan" },
  { label: "Less than", value: "smallerthan" },
  { label: "Greater than equal to", value: "greaterthanequalto" },
  { label: "Less than equal to", value: "smallerthanequalto" },
  { label: "Not equal", value: "notequalto" },
]

export const colorOptions = [
  { value: "Black", label: "Black", color: "black" },
  { value: "Red", label: "Red", color: "red" },
  { value: "Yellow", label: "Yellow", color: "gold" },
  { value: "Green", label: "Green", color: "green" },
  { value: "White", label: "White", color: "lightgrey" },
  { value: "Blue", label: "Blue", color: "blue" },
  { value: "Grey", label: "Grey", color: "grey" },
];

export const categoryOptions = [
  { value: 'SI', label: 'SI' },
  { value: 'CTB', label: 'CTB' },
  { value: 'BR', label: 'BR' },
  { value: 'SD', label: 'SD' },
  { value: 'SE', label: 'SE' },
  { value: 'UN', label: 'UN' },
  { value: 'DN', label: 'DN' },
]

export const colorFilterOptions = [
  { value: 'black', label: 'Black' },
  { value: 'black/red', label: 'Black/Red' },
  { value: 'red', label: 'Red' },
  { value: 'blue', label: 'Blue' },
  { value: 'yellow', label: 'Yellow' },
  { value: 'green', label: 'Green' },
  { value: 'white', label: 'White' },
]

export const availabilityFilterOptions = [
  { label: 'Virtual Norm', value: 'VirtualNorm', name: 'AF4' },
  { label: 'Norm', value: 'Norm', name: 'AF1' },
  { label: 'Stock', value: 'Stock', name: 'AF2' },
  { label: 'GIT', value: 'GIT', name: 'AF3' },
]

export const horizonFilterOptions = [
  { label: 'Start Date', value: 'StartDate' },
  { label: 'EndDate', value: 'EndDate' },
]
export const colorTypeFilterOptions = [
  { value: "colorcount", label: "Color Count" },
  { value: "colorage", label: "Color Age" },
];

export const getStartDate = (endDate: string): string => {
  const date = new Date(endDate);
  if (Number.isNaN(date.getTime())) return "";
  date.setDate(date.getDate() - 89);
  return date.toISOString().split('T')[0];
};

export const useVFMultiFilter = ({
  multiFilter,
  onMultiFilterChange,
}: UseVFMultiFilterProps) => {
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string[]>>({});

  const handleSelectChange = useCallback(({
    newValue,
    header,
    filterId,
    parentId,
    attributeName
  }: SelectChangeParams) => {

    const selectedValues = newValue
      ? newValue.map((item: any) => item.value)
      : [];

    setSelectedOptions((prev) => ({
      ...prev,
      [header]: selectedValues,
    }));

    const parentFilter = multiFilter[parentId];

    const existingFilters = parentFilter.filters.filter(
      (f: BPRFilter) => f.name !== filterId
    );

    const newFilters = selectedValues.map((value: string) => ({
      attributeName: attributeName || header,
      value: value,
      operator: "=",
      label: header,
      name: filterId,
    }));

    const updatedMultiFilter: BPRFilterState = {
      ...multiFilter,
      [parentId]: {
        ...parentFilter,
        filters: [...existingFilters, ...newFilters],
      },
    };

    onMultiFilterChange(updatedMultiFilter);
  }, [multiFilter, onMultiFilterChange]);

  const getSelectedValues = useCallback((header: string): string[] => {
    return selectedOptions[header] || [];
  }, [selectedOptions]);

  const setSelectedValues = useCallback((header: string, values: string[]) => {
    setSelectedOptions(prev => ({
      ...prev,
      [header]: values
    }));
  }, []);

  return {
    handleSelectChange,
    selectedOptions,
    getSelectedValues,
    setSelectedValues
  };
};

export const useRowCompletion = (rowSelections: RowSelections) => {
  const isRowComplete = useCallback(
    (rowId: number): boolean => {
      const row = rowSelections[rowId];
      if (!row) return false;
      const hasColumn = !!row.column;
      const hasOperation = !!row.operation;
      if (
        row.operation?.value === "hasvalue" ||
        row.operation?.value === "hasnovalue"
      ) {
        return hasColumn && hasOperation;
      }
      const value = typeof row.value === "string" ? row.value.trim() : row.value;
      const hasValue = value !== "" && value !== undefined && value !== null;
      return hasColumn && hasOperation && hasValue;
    },
    [rowSelections]
  );

  return { isRowComplete };
};

export const useMultiFilterChange = ({
  parentId,
  rowSelections,
  setRowSelections,
  multiFilter,
  onMultiFilterChange,
  rowFilterIndexMap,
  setRowFilterIndexMap,
  isUpdatingFromInternal,
}: FilterChangeProps) => {
  const onFilterChange = (
    rowId: number,
    field: "column" | "operation" | "value",
    selected: any
  ) => {
    const updatedSelections = {
      ...rowSelections,
      [rowId]: { ...rowSelections[rowId], [field]: selected },
    };
    setRowSelections(updatedSelections);

    const current = updatedSelections[rowId];

    const existingFilters = (multiFilter[parentId]?.filters || []) as BPRFilter[];
 
    const nextFilters = existingFilters.slice();
    const newIndexMap = { ...rowFilterIndexMap };
    const idx = rowFilterIndexMap[rowId];

    if (
      current?.column &&
      current?.operation &&
      (current?.operation?.value === "hasvalue" ||
        current?.operation?.value === "hasnovalue" ||
        (current?.value !== undefined && current?.value !== ""))
    ) {
      const newFilter: BPRFilter = {
        attributeName: current.column.value,
        value:
          current?.operation?.value === "hasvalue"
            ? "hasvalue"
            : current?.operation?.value === "hasnovalue"
            ? "hasnovalue"
            : current.value,
        operator: current.operation.value,
        label: current.column.label,
        name: current.column.name,
      };

      if (typeof idx === "number" && idx >= 0 && idx < nextFilters.length) {
        nextFilters[idx] = newFilter;
      } else {
        nextFilters.push(newFilter);
        newIndexMap[rowId] = nextFilters.length - 1;
      }
    } 
    else {
      if (typeof idx === "number" && idx >= 0 && idx < nextFilters.length) {
        nextFilters.splice(idx, 1);
        delete newIndexMap[rowId];
      }
    }

    isUpdatingFromInternal.current = true;
    onMultiFilterChange({
      ...multiFilter,
      [parentId]: {
        ...multiFilter[parentId],
        filters: nextFilters,
      },
    });

    setRowFilterIndexMap(newIndexMap);
  };

  return { onFilterChange };
};

