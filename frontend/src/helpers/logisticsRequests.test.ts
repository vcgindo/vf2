import {mapTransitRemarkBatch, mapExpediteActionBatch, mapPlanningRequest} from './logisticsRequests';

test('single and batch transit actions retain current fields and the real receiver', () => {
  const row={OrderNo:'Order-1',SKUCode:'337',ReceiverLoc:'DP010290',SenderLocation:'Parent-2',
    CurrentLoc:'Hub-3',Action:"Driver's update",ETA:'2026-10-20'};
  expect(mapTransitRemarkBatch([{...row,remark:'New remark'}])).toEqual({data:[{
    OrderNo:'Order-1',SKUCode:'337',WhCode:'DP010290',ParentWHCode:'Parent-2',
    Remarks:'New remark',CurrentLocation:'Hub-3',ETA:'2026/10/20',
  }]});
  const result=mapTransitRemarkBatch([{...row,CurrentLoc:'Hub-4'},{...row,action:'Batch update',ETA:null}]);
  expect(result.data[0].Remarks).toBe("Driver's update");
  expect(result.data[0].CurrentLocation).toBe('Hub-4');
  expect(result.data[1].Remarks).toBe('Batch update');
  expect(result.data[1].ETA).toBeNull();
});

test('expedite single action uses the same exact batch model and current ETA', () => {
  expect(mapExpediteActionBatch([{sc:'337',wc:'DP010290',eta:'2026-10-21',action:'Contacted'}])).toEqual({
    data:[{SKUCode:'337',WHCode:'DP010290',Remark:'Contacted',ETA:'2026/10/21'}],
  });
  expect(mapExpediteActionBatch([{sc:'337',wc:'DP010290',eta:null,action:'Contacted'}]).data[0].ETA).toBeNull();
});

test('Planning uses the selected code, never its display description or an array first row', () => {
  const row={sc:'338',wc:'DP010290',pl:'Parent display name',parentWhCode:'Parent-2',eta:'2026-10-21'};
  expect(mapPlanningRequest(row,'Expedite')).toEqual({skuCode:'338',whCode:'DP010290',
    parentWhCode:'Parent-2',request:'Expedite',eta:'2026/10/21'});
  expect(()=>mapPlanningRequest([row],'Expedite')).toThrow('Select the request row first');
  expect(()=>mapPlanningRequest({...row,parentWhCode:undefined},'Expedite')).toThrow('parent location code');
  const {parentWhCode,...missing}=row;
  expect(()=>mapPlanningRequest(missing,'Expedite')).toThrow('parent location code');
  expect(mapPlanningRequest({...row,parentWhCode:null,eta:undefined},'New')).toEqual({
    skuCode:'338',whCode:'DP010290',parentWhCode:null,request:'New',eta:null,
  });
});

test('a non-date ETA cannot silently become a default date', () => {
  expect(()=>mapExpediteActionBatch([{sc:'337',wc:'DP010290',eta:3}])).toThrow('date value');
});
