/* eslint-disable no-case-declarations */

import type { PayloadAction } from '@reduxjs/toolkit'
import { createReducer } from '@reduxjs/toolkit';
import { BPRFilterState } from '../../../VectorFlow/types/BPR';
import { DailyDataGraph, MTAStore } from '../../../VectorFlow/types/MTA';
import {TOGGLE_GRAPH_MODAL,TOGGLE_NORM_CHANGE_HISTORY_TABLE,UPDATE_PLANNING_DATA,UPDATE_DAILY_DATA, UPDATE_GRID_STATE,UPDATE_LAST_RUN_DATE , UPDATE_ENV_CONFIG , UPDATE_MTA_VF_MULTI_FILTER} from '../../actions/MTA';


const toggleDailyDataGraphModal=(state:any,action:PayloadAction<boolean>)=>{
    state.showDailyDataGraphModal = action.payload
}

const toggleNormChangeHistoryTable = (state:any,action:PayloadAction<boolean>)=>{
    state.showNormChangeHistoryTable = action.payload
}

const setDailyData = (state:any,action:PayloadAction<DailyDataGraph>)=>{
    state.dailyData = action.payload;
}

const updateGridState = (state:any,action:PayloadAction<any>)=>{
    state.currentGridState = action.payload
}

const updatePlanningdata = (state:any,action:PayloadAction<any>)=>{
    state.planning = action.payload
}

const updateLastRunDate = (state:any,action:PayloadAction<string>)=>{
    state.lastRunDate = action.payload
}

const updateEnvConfig = (state:any,action:PayloadAction<string>)=>{
    state.EnvConfig = action.payload
}

const updateMTAVFMultiFilter = (state:any,action:PayloadAction<BPRFilterState>)=>{
    state.mtaVFMultiFilter = action.payload
}

// const resetState = (state:any) => {
//     state.align = [];
//     state.masters=[];
//     state.options=[];
//     state.selectedOptions=[];
//     state.activeMaster={id:0,fields:[],filters:[],progress:'default',name:'',colDefs:[],rowData:[]};
//     state.isSelectMasterOpen = true;
//     state.draftId = '';
//     state.recordCount = 0;
//     state.isDataAvailableLocally = false;
//     state.isUploadModalOpen = false
// }



const mtaReducer = (initialState:MTAStore) => createReducer(initialState, (builder) => {
    builder
      .addCase(TOGGLE_GRAPH_MODAL,toggleDailyDataGraphModal)
      .addCase(TOGGLE_NORM_CHANGE_HISTORY_TABLE,toggleNormChangeHistoryTable)
      .addCase(UPDATE_DAILY_DATA,setDailyData)
      .addCase(UPDATE_GRID_STATE,updateGridState)
      .addCase(UPDATE_PLANNING_DATA,updatePlanningdata)
      .addCase(UPDATE_LAST_RUN_DATE,updateLastRunDate)
      .addCase(UPDATE_ENV_CONFIG,updateEnvConfig)
      .addCase(UPDATE_MTA_VF_MULTI_FILTER,updateMTAVFMultiFilter)
  })

export default mtaReducer;