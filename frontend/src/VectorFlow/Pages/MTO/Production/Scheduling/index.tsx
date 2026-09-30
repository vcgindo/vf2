import React, { useEffect, useState } from 'react'
import { useGetFinalRunResult, useGetRunState, usePostStartSchedulingRun } from '../../../../Services/MTO/Scheduling';
import VFOverlayModal from '../../../../../components/VectorFLOW/commons/VFOverlayModal';
import FileUploadSection from './FileUploadSection';
import StatusBarBottom from './components/StatusBarBottom';
import RunStatusModal from './components/RunStatusModal';
import FinalResultSection from './FinalResultSection';
import { notifyError, notifySuccess, notifyWarning } from '../../../../../helpers/notify';
import OverlayLoader from '../../Common/Loader';
import { useSearchParams } from 'react-router-dom';
import { useUserData } from '../../../../../context';
import { MainSection } from './SchedulingStyles';



const Scheduling = () => {

    const [step, setStep] = useState("Upload");
    
    const [runStatus, setRunStatus] = useState<any>( {
        status: null,
        startTime: null,
        endTime: null,
        message: null,
    });

    const user = useUserData().user

    const [finalResult, setFinalResult] = useState<any>(null);

    const {mutateAsync: getRunState} = useGetRunState();

    const {mutateAsync: postStartSchedulingRun} = usePostStartSchedulingRun();

    const {mutateAsync: getFinalRunResult, isLoading: finalResultLoading} = useGetFinalRunResult();
    const [runId, setRunId] = useState<string | null>(null);

    const GetRunStatus = async()=>{ 
        try{

            const result = await getRunState();
            if(result.status===200){
                setRunStatus(result.data.data);
            }else{
                setRunStatus({status: 'FAILED_TO_FETCH', startTime: null, endTime: null, message: null});
            }
        }
        catch(e:any){
            setRunStatus({status: 'FAILED_TO_FETCH', startTime: null, endTime: null, message: null});
            notifyError("Failed to fetch run status");
            console.error('error', e);
        }
    }

    useEffect(()=>{
        let interval: NodeJS.Timer;
        if(runStatus.status === "RUNNING"){
            interval = setInterval(()=>{
                GetRunStatus();
            }, 5000);
        }
        return () => {
            if(interval) clearInterval(interval);
        }
    },[runStatus.status])

    useEffect(()=>{ 
        GetRunStatus();
    },[])

    const [isRunEnabled, setIsRunEnabled] = useState(false);

    const getStep = ()=>{
        switch (step) {
            case "Upload":
                return <FileUploadSection setIsRunEnabled={setIsRunEnabled}/>
            case "Final Result":
                return <FinalResultSection setStep={setStep} finalResult={finalResult}/>
            default:
                return null;
        }
    }

    const [isModalOpen, setIsModalOpen] = useState(true);
    const [searchParams, setSearchParams] = useSearchParams();

    const onGoToFinalResult = async() => {

        try{
            const result = await getFinalRunResult();
            if(result.status===200){
                notifySuccess("Fetched Run Result Successfully");
                setFinalResult(result.data.data);
                setSearchParams({ page: "ResourceView" });
                setStep("Final Result");
            }
            else{
                notifyError("Failed to fetch run result");
            }
        }
        catch(e){
            notifyError("Failed to fetch run result");
            console.error(e);
        }
    }

    const getRunStatusModal = (runStatus:any) => {
        if(["SUCCESS", "FAILED", "ABORT", "RUNNING", 'FAILED_TO_FETCH'].includes(runStatus.status)){
            return(
            <VFOverlayModal parentSelector="#main-content" openModal={isModalOpen}  >
            <RunStatusModal runStatus={runStatus} closeModal={()=>setIsModalOpen(false)} goTofinalResult={onGoToFinalResult}/>
            </VFOverlayModal>
            )        
        }
    }

    const WEB_SOCKET = process.env.REACT_APP_WS_API_HOST

    useEffect(() => {
        if(runId && WEB_SOCKET){
    
            try{

                const socket = new WebSocket(`${WEB_SOCKET}/ws/scheduler/${runId}/`);
                
                socket.onopen = () => {
                console.log("WebSocket connection opened");
                setRunStatus((prev: any) => ({ ...prev, status: "RUNNING" }));
                // StartRun()
            };
            
            socket.onmessage = (event) => {
                console.log("WebSocket message received:", event.data);
            };
            
            socket.onerror = (error) => {
                console.error("WebSocket error:", error);
                // notifyError("Failed to connect to WebSocket. Couldn't fetch run progress!!");
            };
            
            socket.onclose = () => {
                console.log("WebSocket connection closed");
            };
            
            return () => {
                socket.close();
            };
        }
        catch(e){
            console.error("WebSocket connection error:", e);
            // notifyWarning("Could not connect to websocket. Run status might not update in real-time.");
        }
        }
      
    }, [runId]);

    const StartRun = async()=>{
        try{
            const response = await postStartSchedulingRun({user_id: user.user.id.toString(), user_name: user.user.name});
            if(response.status === 200){
                const run_id = response.data.run_id;
                setRunId(run_id)
                setRunStatus((prev: any)=>({ ...prev, status: "RUNNING",progress: '0%', startTime: new Date().toISOString(), endTime: null, message: "initializing..."}));
                notifySuccess("Run started successfully");
                setIsModalOpen(true);
                setTimeout(()=>{
                    GetRunStatus();
                },3000)
            }
        }
        catch(e){
            notifyError("Failed to start the run");
            console.error('error', e);
        }
    }

    

    const getRunActionBar = () => {
        
        switch (step) {
            case "Upload":
                return (
                    <StatusBarBottom isRunEnabled={isRunEnabled} isGoToFinalResult onGoToFinalResult={onGoToFinalResult} StartRun={StartRun}/>
                );
            case "Final Result":
                return null;
            default:
                return null;
    }}

    

    return (
        <MainSection id='main-content' >
            {
                finalResultLoading &&
                <OverlayLoader message='Fetching Run Result...'/>
            }
            {
                getRunStatusModal(runStatus)
            }
            {
                getStep()
            }
            {
                getRunActionBar()
            }
        </MainSection>
    )
}

export default Scheduling