import React, { useState, useRef, useEffect } from "react";
import {
  FilterGroup,
  FilterColumn,
  TextWrapper,
  DropDownWrapper,
} from "./style";
import {
  TextInputWrapper,
  ButtonWrapper,
  ImageWrapper,
  StyledCalendar,
} from "../../SupplyChainIntelligenceHub/ElephantOrders/styles";
import { useUserData } from "../../../../../context";
import moment from "moment";
import ReactDOM from "react-dom";
import { getStartDate, useVFMultiFilter } from "./useVFFilterContent";
import { BPRFilterState } from "../../../../../VectorFlow/types/BPR";
import { useSelector } from "react-redux";
import { RootState } from "./../../../../../redux/store/store";
interface FilterSectionProps {
  filters?: any;
  multiFilter: BPRFilterState;
  onMultiFilterChange: (newMultiFilter: BPRFilterState) => void;
  initialFromDate?: string;
  initialToDate?: string;
  selectedFilterType?: string;
}

export const HorizonFilter: React.FC<FilterSectionProps> = ({
  multiFilter,
  onMultiFilterChange,
  initialFromDate = "",
  initialToDate = "",
}) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const { handleSelectChange } = useVFMultiFilter({
    multiFilter,
    onMultiFilterChange,
  });

  const lastRunDate = useSelector((state: RootState) => state.mta.lastRunDate);
  const endDate = lastRunDate ? lastRunDate.split('T')[0] : "";
  const startDate:string = getStartDate(endDate);

  const [fromDate, setFromDate] = useState<string>(initialFromDate);
  const [toDate, setToDate] = useState<string>(initialToDate);

  const [showFromCal, setShowFromCal] = useState(false);
  const [showToCal, setShowToCal] = useState(false);
  const [fromCalPos, setFromCalPos] = useState({ top: 0, left: 0 });
  const [toCalPos, setToCalPos] = useState({ top: 0, left: 0 });

  const fromInputRef = useRef<HTMLInputElement>(null);
  const toInputRef = useRef<HTMLInputElement>(null);
  const fromCalRef = useRef<HTMLDivElement>(null);
  const toCalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (multiFilter?.horizonFilter?.filters) {
      const startDateFilter = multiFilter.horizonFilter.filters.find(
        (f: any) => f.attributeName === "startDate"
      );
      const endDateFilter = multiFilter.horizonFilter.filters.find(
        (f: any) => f.attributeName === "endDate"
      );
      
      if (startDateFilter) {
        setFromDate(startDateFilter.value);
      }
      
      if (endDateFilter) {
        setToDate(endDateFilter.value);
      }
    }
  }, [multiFilter?.horizonFilter?.filters]);

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        fromCalRef.current &&
        !fromCalRef.current.contains(target) &&
        fromInputRef.current &&
        !fromInputRef.current.contains(target)
      ) {
        setShowFromCal(false);
      }

      if (
        toCalRef.current &&
        !toCalRef.current.contains(target) &&
        toInputRef.current &&
        !toInputRef.current.contains(target)
      ) {
        setShowToCal(false);
      }
    };

    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const toggleFromCalendar = () => {
    const rect = fromInputRef.current?.getBoundingClientRect();
    if (rect) {
      setFromCalPos({
        top: rect.bottom + window.scrollY + 20,
        left: rect.left + window.scrollX,
      });
    }
    setShowFromCal((prev) => !prev);
  };

  const tileDisabled = ({ date }: { date: Date }) => {

  const start = new Date(startDate)
  const end = new Date(endDate);

  const tile = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const startOnly = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  const endOnly = new Date(end.getFullYear(), end.getMonth(), end.getDate());
  return tile < startOnly || tile > endOnly;
};
  const toggleToCalendar = () => {
    const rect = toInputRef.current?.getBoundingClientRect();
    if (rect) {
      setToCalPos({
        top: rect.bottom + window.scrollY + 20,
        left: rect.left + window.scrollX,
      });
    }
    setShowToCal((prev) => !prev);
  };

  const handleFromChange = (date: Date) => {
    const formatted = moment(date).format("YYYY-MM-DD");
    setFromDate(formatted);
    setShowFromCal(false);
    
    const newValue = [{ label: formatted, value: formatted }];
    
    handleSelectChange({
      newValue,
      header: "Start Date",
      filterId: "HF1",
      parentId: "horizonFilter",
      attributeName: "startDate",
    });
  };

  const handleToChange = (date: Date) => {
    const formatted = moment(date).format("YYYY-MM-DD");
    setToDate(formatted);
    setShowToCal(false);
    
    const newValue = [{ label: formatted, value: formatted }];
    
    handleSelectChange({
      newValue,
      header: "End Date",
      filterId: "HF2",
      parentId: "horizonFilter",
      attributeName: "endDate",
    });
    
  };

  const clearFromDate = () => {
    setFromDate("");
    
    handleSelectChange({
      newValue: [],
      header: "HorizonFilter",
      filterId: "HF1",
      parentId: "horizonFilter",
      attributeName: "startDate",
    });
  };
  
  const clearToDate = () => {
    setToDate("");
    
    handleSelectChange({
      newValue: [],
      header: "HorizonFilter",
      filterId: "HF2",
      parentId: "horizonFilter",
      attributeName: "endDate",
    });
  };

  const boxStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    borderRadius: "10px",
    border: themeUi === "REGALBLAZE" ? "1px solid #F7B500" : "1px solid #ccc",
    padding: "6px 8px",
    backgroundColor: "#fff",
    gap: "6px",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  };

  return (
    <>
      <FilterGroup>  
        <FilterColumn>
          <TextWrapper>From Date</TextWrapper>
          <DropDownWrapper>
            <div style={boxStyle}>
              <TextInputWrapper
                ref={fromInputRef}
                value={fromDate}
                readOnly
                placeholder="YYYY-MM-DD"
                onClick={toggleFromCalendar}
                style={{
                  flex: 1,
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  cursor: "pointer",
                }}
              />
              <ButtonWrapper type="button" onClick={toggleFromCalendar}>
                <ImageWrapper
                  src={
                    themeUi === "REGALBLAZE"
                      ? "/assets/img/mto/OrderRescheduling/edit-calendar-yellow.svg"
                      : "/assets/img/mto/OrderRescheduling/edit-calendar.svg"
                  }
                  alt="calendar"
                />
              </ButtonWrapper>
              <ButtonWrapper type="button" onClick={clearFromDate}>
                <ImageWrapper
                  src={
                    themeUi === "REGALBLAZE"
                      ? "/assets/img/Clear_Due_Date_Yellow.svg"
                      : "/assets/img/Clear_Due_Date.svg"
                  }
                  alt="clear"
                />
              </ButtonWrapper>
            </div>

            {showFromCal &&
              ReactDOM.createPortal(
                <div
                  ref={fromCalRef}
                  style={{
                    position: "absolute",
                    top: fromCalPos.top,
                    left: fromCalPos.left,
                    zIndex: 9999,
                    backgroundColor: "white",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                    borderRadius: "12px",
                    overflow: "hidden",
                  }}
                >
                  <StyledCalendar
                    themeUi={themeUi}
                    onChange={(val) =>
                      val instanceof Date && handleFromChange(val)
                    }

                    value={fromDate ? new Date(fromDate) : new Date()}
                    tileDisabled={tileDisabled}
                  />
                </div>,
                document.body
              )}
          </DropDownWrapper>
        </FilterColumn>

        <FilterColumn>
          <TextWrapper>To Date</TextWrapper>
          <DropDownWrapper>
            <div style={boxStyle}>
              <TextInputWrapper
                ref={toInputRef}
                value={toDate}
                readOnly
                placeholder="YYYY-MM-DD"
                onClick={toggleToCalendar}
                style={{
                  flex: 1,
                  border: "none",
                  outline: "none",
                  background: "transparent",
                  cursor: "pointer",
                }}
              />
              <ButtonWrapper type="button" onClick={toggleToCalendar}>
                <ImageWrapper
                  src={
                    themeUi === "REGALBLAZE"
                      ? "/assets/img/mto/OrderRescheduling/edit-calendar-yellow.svg"
                      : "/assets/img/mto/OrderRescheduling/edit-calendar.svg"
                  }
                  alt="calendar"
                />
              </ButtonWrapper>
              <ButtonWrapper type="button" onClick={clearToDate}>
                <ImageWrapper
                  src={
                    themeUi === "REGALBLAZE"
                      ? "/assets/img/Clear_Due_Date_Yellow.svg"
                      : "/assets/img/Clear_Due_Date.svg"
                  }
                  alt="clear"
                />
              </ButtonWrapper>
            </div>

            {showToCal &&
              ReactDOM.createPortal(
                <div
                  ref={toCalRef}
                  style={{
                    position: "absolute",
                    top: toCalPos.top,
                    left: toCalPos.left,
                    zIndex: 9999,
                    backgroundColor: "white",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                    borderRadius: "12px",
                    overflow: "hidden",
                  }}
                >
                  <StyledCalendar
                    themeUi={themeUi}
                    onChange={(val) => val instanceof Date && handleToChange(val)}
                    value={toDate ? new Date(toDate) : new Date()}
                    minDate={fromDate ? new Date(fromDate) : undefined}
                    tileDisabled={tileDisabled}
                  />
                </div>,
                document.body
              )}
          </DropDownWrapper>
        </FilterColumn>
      </FilterGroup>
    </>
  );
};
