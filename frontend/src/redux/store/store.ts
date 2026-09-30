import { configureStore } from '@reduxjs/toolkit';
import { MTAStore } from '../../VectorFlow/types/MTA';
import { MDMStore } from '../../VectorFlow/types/MDM';
import mdmReducer from '../reducers/MDM';
import mtaReducer from '../reducers/MTA';
import mtoReducer from '../reducers/MTO/index';
import { MTOStore } from '../../VectorFlow/types/MTO';
import { createTransform } from 'redux-persist';
import persistReducer from 'redux-persist/es/persistReducer';
import persistStore from 'redux-persist/es/persistStore';
import storage from 'redux-persist/lib/storage';
import { encryptStorageData,decryptStorageData} from '../../VectorFlow/Pages/MTO/Common/encryption';


const encryptedStorage = {
  setItem: async (key: string, value: string): Promise<void> => {
    try {
      const encryptedValue = await encryptStorageData(value);
      await storage.setItem(key, encryptedValue);
    } catch (error) {
      console.error("Failed to encrypt and set item:", error);
    }
  },
  getItem: async (key: string): Promise<string | null> => {
    try {
      const encryptedValue = await storage.getItem(key);
      if (encryptedValue === null) {
        return null;
      }
      return await decryptStorageData(encryptedValue);
    } catch (error) {
      console.error("Failed to get and decrypt item:", error);
      await storage.removeItem(key);
      return null;
    }
  },
  removeItem: async (key: string): Promise<void> => {
    await storage.removeItem(key);
  },
};


const mdmState:MDMStore = {
    allMasters:[],
    masters:[],
    options:[],
    selectedOptions:[],
    activeMaster:{id:0,fields:[],filters:[],progress:'default',name:'',colDefs:[],rowData:[],isChecked:true},
    isSelectMasterOpen:true,
    draftId:'',
    isUploadModalOpen:false,
    chunkSize:20000,
    recordCount:0,
    isDataAvailableLocally:false,
    lastRunDate:'',
    isSavingToDraft:false
}

const mtaState: MTAStore = {
    showDailyDataGraphModal: false,
    showNormChangeHistoryTable: false,
    dailyData: {
        normChangeData: [],
        chartData: [],
        masterData: [],
        suggestionData: [],
        monitoringData: [],
        rowData: {}
    },
    currentGridState: [],
    planning: {
        currentTab: '',
        currentCategory: '',
        currentView: ''
    },
    lastRunDate: '',
    EnvConfig:{},
    mtaVFMultiFilter:[]

}

const mtoState: MTOStore = {
    AnalyticsData:{}
}

const MTATransform = createTransform(
  (inboundState: MTAStore) => {
    return { EnvConfig: inboundState.EnvConfig };
  },
  (outboundState: { EnvConfig: Record<string, any> }) => {
    return { ...mtaState, EnvConfig: outboundState.EnvConfig };
  },
  { whitelist: ['mta'] }
);

const mtaPersistConfig = {
  key: 'mtaEnvConfig',
  storage: encryptedStorage,
  whitelist: ['EnvConfig'], 
  transforms: [MTATransform],
};

const persistedMtaReducer = persistReducer<MTAStore>(mtaPersistConfig, mtaReducer(mtaState));

export const createStore = (mdmState: MDMStore) => configureStore({
    reducer: {
      mdm: mdmReducer(mdmState),
      mta: persistedMtaReducer, 
      mto: mtoReducer(mtoState),
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false, 
      }),
  });

export const store = createStore(mdmState);
export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>
