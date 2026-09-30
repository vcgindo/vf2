/* eslint-disable no-case-declarations */

import type { PayloadAction } from '@reduxjs/toolkit'
import { createReducer } from '@reduxjs/toolkit';
import {type Option, type MDMMasterState, type MDMStore, type Filter} from '../../../VectorFlow/types/MDM'; 
import { generateRandomId } from '../../../helpers/utils';
import {FILL_MASTERS, FILL_SELECTED_OPTIONS, REMOVE_MASTER, FILTER_MASTER, ADD_MASTER, FILL_OPTIONS, UPDATE_ACTIVE_MASTER, TOGGLE_SELECT_MASTER_SCREEN, UPDATE_COLDEFS, STORE_ALL_MASTERS, ADD_FILTER, REMOVE_FILTER, UPDATE_FILTER, SYNC_ACTIVE_MASTER_TO_MASTER, UPDATE_ROW_DATA, UPDATE_PROGRESS_STATE, RESET_STATE, ADD_COLDEFS, REMOVE_ROW_DATA, REMOVE_COLDEFS, MODIFY_ROW_DATA,SET_DRAFT_ID, TOGGLE_UPLOAD_MODAL, REMOVE_ALL_FILTERS, SET_RECORD_COUNT, UPDATE_DATA_AVAILABILITY_STATUS, RESET_FILTERS,UPDATE_MASTER_CHECKED_STATUS, UPDATE_IS_SAVING_DRAFT, UPDATE_FILTER_VALUE} from '../../actions/MDM';
import { ColDef } from 'ag-grid-enterprise';


const setMasters = (state:any,action:PayloadAction<MDMMasterState[]>|PayloadAction<any>) => {
    switch(action.type){
        case STORE_ALL_MASTERS.type:
            state.allMasters = action.payload;
            break;
        case FILL_MASTERS.type:
            state.masters = action.payload;
            break;
        case REMOVE_MASTER.type:
            state.masters = state.masters.filter(((selectedMaster:MDMMasterState)=>selectedMaster.id !== action.payload));
            break;
        case FILTER_MASTER.type:
            state.masters = state.masters.filter(((selectedMaster:MDMMasterState)=>selectedMaster.id === action.payload));
            break;
        case ADD_MASTER.type:
            state.masters = [...state.masters,action.payload];
            break;
        case SYNC_ACTIVE_MASTER_TO_MASTER.type:
            state.masters = state.masters.map((master:MDMMasterState)=>{
                if(master.id===state.activeMaster.id){
                    return {...state.activeMaster}
                }
                return master
            })
            break;

        case UPDATE_COLDEFS.type:
            state.activeMaster = {...state.activeMaster,colDefs:action.payload};
            // state.masters = state.masters.map((master:MDMMasterState)=>{
            //     if(master.id === action.payload.id){
            //         return {...master,colDefs:action.payload.colDefs}
            //     }
            //     return master;
            // });
            break;
        case ADD_COLDEFS.type:
            state.activeMaster = {...state.activeMaster,colDefs:[...action.payload.colDefs,...state.activeMaster.colDefs]}
            break;
        case REMOVE_COLDEFS.type:
            const newColDefs = state.activeMaster.colDefs.filter((col:ColDef)=>!action.payload.includes(col.colId));
            state.activeMaster = {...state.activeMaster,colDefs:newColDefs};
            break;
        case ADD_FILTER.type:
            state.activeMaster.filters = [
                ...state.activeMaster.filters,
                {
                  id:generateRandomId(),
                  masterId:state.activeMaster.id,
                  field:'',
                  operator:'',
                  text:''
                }
            ]

            state.masters = state.masters.map((master:MDMMasterState)=>{
                if(master.id===state.activeMaster.id){
                    return {...state.activeMaster}
                }
                return master
            })
            break;
        case REMOVE_ALL_FILTERS.type:
            state.activeMaster.filters = []
            state.masters = state.masters.map((master:MDMMasterState)=>{
                if(master.id===state.activeMaster.id){
                    return {...state.activeMaster}
                }
                return master
            })
            break;
        case REMOVE_FILTER.type:
            state.activeMaster.filters = state.activeMaster.filters.filter((filter:Filter)=>filter.id !== action.payload)
            state.masters = state.masters.map((master:MDMMasterState)=>{
                if(master.id===state.activeMaster.id){
                    return {...state.activeMaster}
                }
                return master
            })
            break;
         case RESET_FILTERS.type:
            state.activeMaster.filters = [{
                id:generateRandomId(),
                masterId:state.activeMaster.id,
                field:'',
                operator:'',
                text:''
              }]
            state.masters = state.masters.map((master:MDMMasterState)=>{
                if(master.id===state.activeMaster.id){
                    return {...state.activeMaster}
                }
                return master
            })
            break;
        case UPDATE_FILTER.type:
            state.activeMaster.filters = state.activeMaster.filters.map((filter:Filter) => {
                if(filter.id === action.payload.filterId){
                    return {...filter,[action.payload.property]:action.payload.value}
                }
                return filter;
            })
            break;
        case UPDATE_ROW_DATA.type:
            state.activeMaster = {...state.activeMaster,rowData:action.payload};
            break;
        case MODIFY_ROW_DATA.type:
            const newRowData = state.activeMaster.rowData.map((row:any)=>{
                if(JSON.stringify(row) === JSON.stringify(action.payload.oldRow)){
                    return action.payload.newRow;
                }
                return row;
            })
            state.activeMaster = {...state.activeMaster,rowData:newRowData};
            break;
        case REMOVE_ROW_DATA.type:  
            const selectedRows = action.payload.map((row:any)=>JSON.stringify(row));
            const updatedRows = state.activeMaster.rowData.filter((row:any)=>!selectedRows?.includes(JSON.stringify(row))); 
            state.activeMaster = {...state.activeMaster,rowData:updatedRows};
            break;

        case UPDATE_PROGRESS_STATE.type:
            state.activeMaster = {...state.activeMaster, progress:action.payload};
            break;
        case UPDATE_FILTER_VALUE.type:
            state.activeMaster.filters = state.activeMaster.filters.map((filter: Filter) => {
                if (filter.id === action.payload.filterId) {
                    if (action.payload.property === "field") {
                        return { ...filter, [action.payload.property]: action.payload.value, operator: "", text: "" }
                    } else {
                        return { ...filter, [action.payload.property]: action.payload.value }
                    }
                }
                return filter;
            });
            break;
        default:
            return
    }
  }

const setOptions = (state:any,action: PayloadAction<Array<Option>>) => {
     state.options = action.payload;
}
  
const setSelectedOptions = (state:any,action: PayloadAction<Array<Option>>) => {
    state.selectedOptions = action.payload;
}

const setActiveMaster =  (state:any,action:PayloadAction<number | MDMMasterState>) => {
    if(typeof action.payload ==='number'){
        state.activeMaster = {...state.masters[action.payload]};
        return
    }
    state.activeMaster = {...action.payload};
}
   
const setIsSelectMasterOpen = (state:any,action:PayloadAction<boolean>)=>{
    state.isSelectMasterOpen = action.payload;
}

const setDraftId = (state:any,action:PayloadAction<string>) => {
    state.draftId = action.payload;
}

const setRecordCount = (state:any,action:PayloadAction<number>) => {
    state.recordCount = action.payload;
}

const setIsUploadModalOpen=(state:any,action:PayloadAction<boolean>)=>{
    state.isUploadModalOpen = action.payload
}

const setIsSavingToDraft=(state:any,action:PayloadAction<boolean>)=>{
    state.isSavingToDraft = action.payload
}

const setIsDataAvailableLocally = (state:any,action:PayloadAction<boolean>)=>{
    state.isDataAvailableLocally = action.payload
}

const setMasterCheckedStatus = (state:any,action:PayloadAction<number>) =>{
    state.masters = state.masters.map((master:MDMMasterState)=>{
        const masterCopy = {...master}
        if(masterCopy.id === action.payload){
            masterCopy.isChecked = !masterCopy.isChecked
        }
        return masterCopy
    });
}

const resetState = (state:any) => {
    state.align = [];
    state.masters=[];
    state.options=[];
    state.selectedOptions=[];
    state.activeMaster={id:0,fields:[],filters:[],progress:'default',name:'',colDefs:[],rowData:[]};
    state.isSelectMasterOpen = true;
    state.draftId = '';
    state.recordCount = 0;
    state.isDataAvailableLocally = false;
    state.isUploadModalOpen = false,
    state.isSavingToDraft=false
}



const mdmReducer = (initialState:MDMStore) => createReducer(initialState, (builder) => {
    builder
      .addCase(STORE_ALL_MASTERS,setMasters)
      .addCase(FILL_MASTERS,setMasters)
      .addCase(ADD_MASTER,setMasters)
      .addCase(REMOVE_MASTER,setMasters)
      .addCase(FILTER_MASTER,setMasters)
      .addCase(SYNC_ACTIVE_MASTER_TO_MASTER,setMasters)
      .addCase(UPDATE_COLDEFS,setMasters)
      .addCase(ADD_COLDEFS,setMasters)
      .addCase(REMOVE_COLDEFS,setMasters)
      .addCase(ADD_FILTER,setMasters)
      .addCase(REMOVE_FILTER,setMasters)
      .addCase(REMOVE_ALL_FILTERS,setMasters)
      .addCase(UPDATE_FILTER,setMasters)
      .addCase(RESET_FILTERS,setMasters)
      .addCase(UPDATE_ROW_DATA,setMasters)
      .addCase(MODIFY_ROW_DATA,setMasters)
      .addCase(REMOVE_ROW_DATA,setMasters)
      .addCase(UPDATE_PROGRESS_STATE,setMasters)
      .addCase(FILL_OPTIONS,setOptions)
      .addCase(FILL_SELECTED_OPTIONS,setSelectedOptions)
      .addCase(UPDATE_ACTIVE_MASTER,setActiveMaster)
      .addCase(TOGGLE_SELECT_MASTER_SCREEN,setIsSelectMasterOpen)
      .addCase(UPDATE_IS_SAVING_DRAFT,setIsSavingToDraft)
      .addCase(RESET_STATE,resetState)
      .addCase(SET_DRAFT_ID,setDraftId)
      .addCase(TOGGLE_UPLOAD_MODAL,setIsUploadModalOpen)
      .addCase(SET_RECORD_COUNT,setRecordCount)
      .addCase(UPDATE_DATA_AVAILABILITY_STATUS,setIsDataAvailableLocally)
      .addCase(UPDATE_MASTER_CHECKED_STATUS,setMasterCheckedStatus)
      .addCase(UPDATE_FILTER_VALUE,setMasters)
  })

export default mdmReducer;