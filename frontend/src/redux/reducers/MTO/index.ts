import type { PayloadAction } from '@reduxjs/toolkit'
import { createReducer } from '@reduxjs/toolkit';
import { MTOStore } from '../../../VectorFlow/types/MTO';
import {
  SAVE_ANALYTICS_DATA,
  DAYWISE_COVERAGE_ANALYTICS,
  PROCPLANNING_ANALYTICS,
  RESOURCE_UTIL_ANALYTICS,
  BM_REPORT_ANALYTICS,
  SET_TASK_PENDING_SELECTED,
  APPLIED_FILTERS,
  SET_POOGI_INITIAL_DATA,
  SET_EDITABLE_MAJ_ROW,
  SET_EDITABLE_MIN_ROW,
  SET_BUFFER_INITIAL_DATA,
  SET_CALENDAR_INITIAL_DATA,
  SET_CALENDAR_MODIFY_DATA,
  SET_BUFFER_MODIFY_DATA,
  SET_TASK_PENDING_ROW_DATA,
  SET_CCR_INITIAL_DATA,
  SET_CCR_MODIFY_DATA,
  SET_POOGI_MODIFY_DATA,
  RESET_MTO_STATE,
  SET_EDIT_STATUS,
} from "../../actions/MTO";




const setAnalyticsData = (state: any, action: PayloadAction<any>) => {
    state.AnalyticsData = action.payload
}

const setDayWiseCoverageAnalytics = (state: any, action: PayloadAction<any>) => {
    state.DaywiseCoverageAnalytics = action.payload
}

const setProcPlanningAnalytics = (state: any, action: PayloadAction<any>) => {
    state.ProcPlanningAnalytics = action.payload
}

const setResourceUtilAnalytics = (state: any, action: PayloadAction<any>) => {
    state.ResourceUtilAnalytics = action.payload
}

const setAppliedFilters = (state: any, action: PayloadAction<any>) => {
    state.AppliedFilters = action.payload
}

const setBMReportAnalytics = (state: any, action: PayloadAction<any>) => {
    state.BMReportAnalytics = action.payload;
}

const setTaskPendingSelected = (state: any, action: PayloadAction<any>)=>{
    state.taskPendingSelected = action.payload;
}

const setEditableMajRow = (state: any, action: PayloadAction<any>)=>{
    state.editableMajRow = action.payload;
}
const setEditableMinRow = (state: any, action: PayloadAction<any>)=>{
    state.editableMinRow = action.payload;
}

const setPoogiIntialData = (state: any, action: PayloadAction<any>)=>{
    state.poogiIntialData = action.payload;
}

const setBufferInitialData= (state: any, action: PayloadAction<any>)=>{
    state.bufferInitialData = action.payload;
}

const setBufferModifyData = (state: any, action: PayloadAction<any>)=>{
    state.bufferModifyData = action.payload;
}
const setCalenderInitialData= (state: any, action: PayloadAction<any>)=>{
    state.calendarInitialData = action.payload;
}

const setCalenderModifyData = (state: any, action: PayloadAction<any>)=>{
    state.calendarModifyData = action.payload;
}

const setCCRInitialData = (state: any, action: PayloadAction<any>)=>{
    state.ccrInitialData = action.payload;
}

const setCCRModifyData = (state: any, action: PayloadAction<any>)=>{
    state.ccrModifyData = action.payload;
}

const setTaskPendingRowData  = (state: any, action: PayloadAction<any>)=>{
    state.taskPendingRowData = action.payload;
}

const setPoogiModifyData = (state: any, action: PayloadAction<any>)=>{
    state.poogiModifyData = action.payload;
}

const setEditStatus = (state:any , action: PayloadAction<any>)=>{
    state.editStatus = action.payload;
}

const resetMtoState = (state: any)=>{
    state.poogiModifyData = null;
    state.poogiIntialData  = null;
    state.taskPendingRowData = null;
    state.ccrModifyData = null;
    state.ccrInitialData = null;
    state.bufferInitialData = null;
    state.bufferModifyData = null;
    state.calendarInitialData = null;
    state.calendarModifyData = null;
    state.editableMajRow = null;
    state.editableMinRow;
    state.taskPendingSelected = null;
}

const mtoReducer = (initialState: MTOStore) => createReducer(initialState, (builder) => {
    builder.addCase(SAVE_ANALYTICS_DATA, setAnalyticsData)
    builder.addCase(DAYWISE_COVERAGE_ANALYTICS, setDayWiseCoverageAnalytics)
    builder.addCase(PROCPLANNING_ANALYTICS, setProcPlanningAnalytics)
    builder.addCase(RESOURCE_UTIL_ANALYTICS, setResourceUtilAnalytics)
    builder.addCase(BM_REPORT_ANALYTICS, setBMReportAnalytics)
    builder.addCase(SET_TASK_PENDING_SELECTED, setTaskPendingSelected)
    builder.addCase(APPLIED_FILTERS, setAppliedFilters)
    builder.addCase(SET_EDITABLE_MAJ_ROW, setEditableMajRow)
    builder.addCase(SET_EDITABLE_MIN_ROW, setEditableMinRow)
    builder.addCase(SET_POOGI_INITIAL_DATA, setPoogiIntialData)
    builder.addCase(SET_BUFFER_INITIAL_DATA, setBufferInitialData)
    builder.addCase(SET_BUFFER_MODIFY_DATA, setBufferModifyData)
    builder.addCase(SET_CALENDAR_INITIAL_DATA, setCalenderInitialData)
    builder.addCase(SET_CALENDAR_MODIFY_DATA, setCalenderModifyData)
    builder.addCase(SET_TASK_PENDING_ROW_DATA, setTaskPendingRowData)
    builder.addCase(SET_CCR_INITIAL_DATA, setCCRInitialData)
    builder.addCase(SET_CCR_MODIFY_DATA, setCCRModifyData)    
    builder.addCase(SET_POOGI_MODIFY_DATA, setPoogiModifyData)
    builder.addCase(RESET_MTO_STATE, resetMtoState)
    builder.addCase(SET_EDIT_STATUS, setEditStatus)
})

export default mtoReducer;
