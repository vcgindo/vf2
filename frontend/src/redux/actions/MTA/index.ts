import { createAction } from '@reduxjs/toolkit';
import { type DailyDataGraph } from '../../../VectorFlow/types/MTA';
import { BPRFilterState } from '../../../VectorFlow/types/BPR';

const actions =  {
    UPDATE_DAILY_DATA: createAction<DailyDataGraph>("UPDATE_DAILY_DATA"),
    TOGGLE_GRAPH_MODAL: createAction<boolean>("TOGGLE_GRAPH_MODAL"),
    TOGGLE_NORM_CHANGE_HISTORY_TABLE: createAction<boolean>("TOGGLE_NORM_CHANGE_HISTORY_TABLE"),
    UPDATE_GRID_STATE:createAction<any>(" UPDATE_GRID_STATE"),
    UPDATE_PLANNING_DATA:createAction<any>("UPDATE_PLANNING_DATA"),
    UPDATE_LAST_RUN_DATE:createAction<string>("UPDATE_LAST_RUN_DATE"),
    UPDATE_ENV_CONFIG:createAction<string>("UPDATE_ENV_CONFIG"),
    UPDATE_MTA_VF_MULTI_FILTER:createAction<BPRFilterState>("UPDATE_MTA_VF_MULTI_FILTER")
}

export const {
    UPDATE_DAILY_DATA,
    TOGGLE_GRAPH_MODAL,
    TOGGLE_NORM_CHANGE_HISTORY_TABLE,
    UPDATE_GRID_STATE,
    UPDATE_PLANNING_DATA,
    UPDATE_LAST_RUN_DATE,
    UPDATE_ENV_CONFIG,
    UPDATE_MTA_VF_MULTI_FILTER
} = actions;