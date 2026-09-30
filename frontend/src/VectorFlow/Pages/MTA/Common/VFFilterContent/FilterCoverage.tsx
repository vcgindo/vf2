import React, { useEffect, useState } from "react";
import "./styles.css";
import { useThemeStyles } from "../../../../../hooks/useVFFilterContent";
import { FilterColumn, FilterGroup, TextWrapper } from "./style";
import { BPRFilter, BPRFilterState } from "../../../../../VectorFlow/types/BPR";

interface FilterSectionProps {
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
}

type CoverageOption = {
  label: string;
  value: string;
  color: string;
  name: string;
};

const coverageOptions: CoverageOption[] = [
  { label: "Gap < 33%", value: "low", color: "green", name: "CGF1" },
  { label: "33% ≤ Gap ≤ 67%", value: "medium", color: "goldenrod", name: "CGF2" },
  { label: "Gap > 67%", value: "high", color: "crimson", name: "CGF3" },
];

const coverageValueMap: Record<string, string> = {
  low: "Gap < 33%",
  medium: "33% <= Gap <= 67%",
  high: "Gap > 67%",
};

export const CoverageFilters: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
}) => {
  const styles = useThemeStyles();
  const [selected, setSelected] = useState<string[]>([]);
  const parentId = "coverageFilter";

  useEffect(() => {
    const savedFilters = multiFilter[parentId]?.filters || [];
    const selectedValues = savedFilters.map((f: BPRFilter) => {
      if (f.value.includes("< 33%")) return "low";
      if (f.value.includes("33%") && f.value.includes("67%")) return "medium";
      if (f.value.includes("> 67%")) return "high";
      return "";
    }).filter(Boolean);
    setSelected(selectedValues);
  }, [multiFilter]);

  const toggleOption = (value: string) => {
    setSelected((prevSelected) => {
      const updated = prevSelected.includes(value)
        ? prevSelected.filter((v) => v !== value)
        : [...prevSelected, value];

      const newCoverageFilters = updated.map((v) => {
        const opt = coverageOptions.find((o) => o.value === v);
        return {
          attributeName: "Coverage",
          value: coverageValueMap[v],
          operator: "=",
          label: "Coverage",
          name: opt?.name || "CGF",
        };
      });

      const updatedMultiFilter = {
        ...multiFilter,
        [parentId]: {
          ...multiFilter[parentId],
          filters: newCoverageFilters,
        },
      };

      onMultiFilterChange(updatedMultiFilter);
      return updated;
    });
  };

  return (
    <FilterGroup>
      <FilterColumn style={{ minWidth: "400px", maxWidth: "none" }}>
        <TextWrapper>Coverage Filter</TextWrapper>
        <div className="chip-container">
          {coverageOptions.map((option) => {
            const isActive = selected.includes(option.value);
            return (
              <button
                key={option.value}
                onClick={() => toggleOption(option.value)}
                className={`chip ${isActive ? "active" : ""}`}
                style={{
                  backgroundColor: isActive ? option.color : "transparent",
                  borderColor: option.color,
                  color: isActive ? "white" : option.color,
                }}
              >
                {option.label}
              </button>
            );
          })}
        </div>
      </FilterColumn>
    </FilterGroup>
  );
};
