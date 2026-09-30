import { useContext,useEffect } from "react";
import {
  useResetState,
  useSaveState,
} from "../VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR";
import { GridStateContext } from "../context/GridStateContext";
import { notifyError, notifyLoader, notifySuccess } from "../helpers/notify";
import {toast} from 'react-toastify'
import { GridState } from "../VectorFlow/types/BPR";
import { handleDownloadVFReports } from "../helpers/utils";


interface exportToExcelParameters {
  pagination:{
    recordCount:number
    chunkSize:number
  }
  callBack:any
}

const useSaveAllState = (isPlanning?:boolean) => {
  const { ref,setTempDownloadData,setExportExcelRowData,tempDownloadData, onResetCallback } = useContext(GridStateContext);

  const { mutateAsync: saveState } = useSaveState();
  const { mutateAsync: resetState } = useResetState();

  useEffect(()=>{
      if(isPlanning && tempDownloadData){
        setTempDownloadData(false)
      }
    
  },[tempDownloadData])

  const onExportToExcelOld = async (params:exportToExcelParameters)=>{
    const {pagination,callBack} = params
    const {recordCount,chunkSize} = pagination
    

    try {
      //buggy line below
      const numberOfPages = Math.ceil(recordCount/chunkSize);
      const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
      const rows = [];
      for(let i=1; i<=numberOfPages; i++){
      
        const result = await callBack(i);

        if(result === null) {
          // throw new Error("Something Went Wrong")
          break
        }
        rows.push(...result)
        if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
        else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
      }
      
      // setExportExcelColumns(exportExcelColumns)
      setExportExcelRowData([...rows])
      setTempDownloadData(true);
      toast.dismiss(toastId);
      
      notifySuccess(`Data Exported Successfully`);
    } catch (error) {
      console.error(error)
      toast.dismiss();
      notifyError('Something Went Wrong');
    }
    
  }


  const onExportToExcel = async (params:{name:string,filters:any})=>{
    const loader = notifyLoader(`Downloading ${params.name}`)
    try{
      await handleDownloadVFReports(params)
    }catch(err:any){
      notifyError(err)
    }finally{
      toast.dismiss(loader)
    }

    // const {pagination,callBack} = params
    // const {recordCount,chunkSize} = pagination
    

    // try {
    //   //buggy line below
    //   const numberOfPages = Math.ceil(recordCount/chunkSize);
    //   const toastId = notifyLoader(`Downloading Data 0 / ${recordCount}`)
    //   const rows = [];
    //   for(let i=1; i<=numberOfPages; i++){
      
    //     const result = await callBack(i);

    //     if(result === null) {
    //       // throw new Error("Something Went Wrong")
    //       break
    //     }
    //     rows.push(...result)
    //     if(i===numberOfPages) toast.update(toastId,{render:`Downloading Data ${recordCount} / ${recordCount}`})
    //     else toast.update(toastId,{render:`Downloading Data ${i*chunkSize} / ${recordCount}`})
    //   }
      
    //   // setExportExcelColumns(exportExcelColumns)
    //   setExportExcelRowData([...rows])
    //   setTempDownloadData(true);
    //   toast.dismiss(toastId);
      
    //   notifySuccess(`Data Exported Successfully`);
    // } catch (error) {
    //   console.error(error)
    //   toast.dismiss();
    //   notifyError('Something Went Wrong');
    // }
    
  }

  const onSaveState = async (name: string) => {
    try {
      
      const columnState = ref.current?.api.getColumnState();
      if(!columnState?.length)
      {
        notifyError("Cannot save layout: The table is empty.");
        return;
      }
      const chartsState =  ref.current?.api.getChartModels()
      const isPivot = ref.current?.api.isPivotMode()
      const gridState:GridState = {
        pivot:isPivot,
        charts:chartsState,
        columns:columnState
      }

      await saveState({
        reportname: name,
        state: JSON.stringify(gridState),
      });
      notifySuccess("State has been saved");
      ref.current?.api.applyColumnState({ state: columnState });
      ref.current?.api.restoreChart(chartsState)
      ref.current?.api.setGridOption('pivotMode',isPivot)
    } catch (err: any) {
        console.error(err)
      notifyError(err);
    }
  };

  const onResetAllState = async (name: string) => {
    notifyLoader("Reseting Data");
    try {
      
      let tempCurrentGridState = ref.current?.api.getColumnState()
      
      if(!tempCurrentGridState?.length) {
        notifyError("Cannot reset layout: The table is empty.");
        return;
      }

      await resetState({"reportname":name});
      if (onResetCallback) {
        await onResetCallback();
      }

      tempCurrentGridState = tempCurrentGridState.map((t:any) => {
        
        return {
          ...t,
          hide: false,
          sort: null,
          sortIndex: null,
          aggFunc: null,
          rowGroup: false,
          rowGroupIndex: null,
          pivot: false,
          pivotIndex: null,
          flex: undefined,
        };
      });
      ref.current.api.applyColumnState({state:tempCurrentGridState,applyOrder:true})
      // onResetCallback()
      ref.current.api.resetColumnState()
      ref.current.api.setGridOption('pivotMode',false)
      const charts  = ref.current.api.getChartModels()
      charts.forEach((c:any)=>{
        const tempRef = ref.current.api.getChartRef(c.chartId)
        tempRef.destroyChart()
      })
      await onSaveState(name);
      notifySuccess("State has been reset");
    } catch (err: any) {
      notifyError(err);
    }
  };

  return {
    onSaveState,
    onResetAllState,
    onExportToExcel,
    onExportToExcelOld
  };
};

export default useSaveAllState;
