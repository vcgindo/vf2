import _ from 'lodash';
import React from 'react'
import { useDispatch, useSelector } from 'react-redux';
import { SET_POOGI_MODIFY_DATA } from '../../../../../redux/actions/MTO';
import { UPDATE_ROW_DATA } from '../../../../../redux/actions/MDM';
import { RootState } from '../../../../../redux/store/store';

const MinReasonDescCell = (props:any) => {
    const activeMaster = useSelector((state:RootState) => state.mdm.activeMaster);

    const initialPoogiData = useSelector((state: any)=> state.mto.poogiIntialData);
    const poogiModifyData = useSelector((state:any)=> state.mto.poogiModifyData);

    const dispatch = useDispatch();

    const undo = ()=>{
        if(!props.data.id){

            const newData = _.cloneDeep(activeMaster.rowData);
    newData.forEach((ele) => {
      if (ele.majId === props.data.majId) {
        initialPoogiData.forEach((elm:any) => {
          if (elm.majId === ele.majId) {
            ele.minData.forEach((ex:any) => {
              if (ex.minId === props.data.minId) {
                const initialMinData = elm.minData.find((initEx:any) => initEx.minId === ex.minId);
                if (initialMinData) {
                  ex.mindsc = initialMinData.mindsc;
                  ex.iu = false;
                }
              }
            });
          }
        });
      }
    });
    dispatch(UPDATE_ROW_DATA(newData));

        const newModifyData = _.cloneDeep(poogiModifyData);
        newModifyData.forEach((e:any)=>{
            if(e.majId===props.data.majId){
                e.minData.forEach((elm:any)=>{
                    if(elm.minId===props.data.minId){
                        initialPoogiData.forEach((ex: any)=>{
                            if(ex.majId===props.data.majId){
                                ex.minData.forEach((exm:any)=>{
                                    if(exm.minId===props.data.minId){
                                        elm.mindsc = exm.mindsc;
                                        elm.iu = false;
                                    }
                                })
                            }
                        })
                    }
                })
            }
        })

        dispatch(SET_POOGI_MODIFY_DATA(newModifyData));
        }
    }
  return (
    <div
  style={{
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '4px',
    opacity: `${
      activeMaster.rowData.some(
        (element: any) =>
          element.majId === props.data.majId && element.id === true
      ) || props.data.id
        ? 0.3
        : 1
    }`,
  }}
>
  <span>{props.data.mindsc}</span>
  {(props.data.iu && !props.data.in) && (
    <span style={{ paddingTop: '2px', cursor: 'pointer' }}>
      <img
        onClick={undo}
        height={18}
        width={18}
        src="/assets/img/undo.svg"
        alt="undo"
      />
    </span>
  )}
</div>

  )
}

export default MinReasonDescCell