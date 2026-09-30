import { useTranslation } from "react-i18next";
import { useUserData } from "../../../context";
import { BoldSpan } from './styles'

const BreadCrumb = () => {
  const { t } = useTranslation();
  const { user } = useUserData();
  if (location.pathname === '/mta/master-data-management/control-panel' || location.pathname === '/mto/master-data-management/control-panel') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Control Panel</BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/control-panel/view-modify' || location.pathname === '/mto/master-data-management/control-panel/view-modify') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> View / Modify</BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/saved-drafts' || location.pathname === '/mto/master-data-management/saved-drafts') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Saved Drafts </BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/task-status' || location.pathname === '/mto/master-data-management/task-status') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Task Status </BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/task-pending' || location.pathname === '/mto/master-data-management/task-pending') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Task Pending For Review </BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/control-panel/add' || location.pathname === '/mto/master-data-management/control-panel/add') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Add Records </BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/control-panel/delete' || location.pathname === '/mto/master-data-management/control-panel/delete') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Delete Records </BoldSpan></span>
  if (location.pathname === '/mta/master-data-management/data-modification-history' || location.pathname === '/mto/master-data-management/data-modification-history') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Data Modification History</BoldSpan></span>
  
  if (location.pathname === '/masters-interceptor/control-panel') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> Control Panel <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Module Selection </BoldSpan></span>
  if (location.pathname === '/masters-interceptor/saved-drafts') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> Saved Drafts <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>  Module Selection </BoldSpan></span>
  if (location.pathname === '/masters-interceptor/task-pending') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> Task Pending for Review  <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Module Selection</BoldSpan></span>
  if (location.pathname === '/masters-interceptor/task-status') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> Task Status<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Module Selection</BoldSpan></span>
  if (location.pathname === '/masters-interceptor/data-modification-history') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> Data Modification History <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>  Module Selection</BoldSpan></span>
  


  if (location.pathname === '/mta/supply-chain-intelligence-hub/planning') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Planning </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/bpr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BPR</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/rrr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> RRR</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/bor') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BOR</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/buffer-trend-report') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>BTR </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/open-expediting-requests') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> OER </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/sdr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> SDR </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/eo') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> EO </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/planning') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Planning</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/bpr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BPR </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/rrr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> RRR </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/bor') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BOR </BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/buffer-trend-report') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BTR</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/open-expediting-requests') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>OER</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/sdr') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>SDR</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/eo') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>EO</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/total-requirement-report') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Total Requirement Report</BoldSpan></span>

  if (location.pathname === '/mta/logistics/intransit-whereabouts') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>In Transit whereabouts</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/bor-color-bandwise') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BOR - Color Bandwise</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/SupplierWiseAllocation') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Supplier Wise Allocation</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/rrr-color-bandwise') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> RRR - Color Bandwise</BoldSpan></span>
  if (location.pathname === '/mta/supply-chain-intelligence-hub/order-allocation-report') return <span>SCIH <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Order Allocation Report</BoldSpan></span>
  if (location.pathname === '/mta/logistics/intransit-whereabouts') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>In Transit whereabouts</BoldSpan></span>



  if (location.pathname === '/mta/insights-and-trends/buffer-trend-report') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>BTR</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/buffer-trends') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BT</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/guided-insights') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> GI</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/research-insights') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>RI</BoldSpan></span>

  if (location.pathname === '/mta/dbm/dbm-norm-suggestions') return <span>DBM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>DBM Norm Suggestion</BoldSpan></span>





  if (location.pathname === '/mta/insights-and-trends/buffer-trend-report') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BTR</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/buffer-trends') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> BT</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/guided-insights') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> GI</BoldSpan></span>
  if (location.pathname === '/mta/insights-and-trends/research-insights') return <span>Insights & Trends <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> RI</BoldSpan></span>

  if (location.pathname === '/mta/dbm/dbm-norm-suggestions') return <span>DBM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>DBM Norm Suggestion</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/enquiry-response') return <span><span style={{ fontWeight: 'normal' }}>Production Planning & Scheduling </span><img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Enquiry Response</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insight-and-trends/bm-trends') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / BM Trends</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / STPL & Full Kits</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insight-and-trends/order-at-risk') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / Orders At Risk</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insight-and-trends/order-balance') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / Order Balance</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insights-and-trends/elapsed-time') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / Elapsed Time</BoldSpan></span>

  if (location.pathname === '/mto/procurement/material-coverage-open-sales') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Material Coverage For Open Sales Order</BoldSpan></span>
  if (location.pathname === '/mto/procurement-planning/planning') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Procurement Planning</BoldSpan></span>
  if (location.pathname === '/mto/planning/simulative-fullkit') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Procurement Planning</BoldSpan></span>
  if (location.pathname === '/mto/procurement/material-requirement') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Material Requirement</BoldSpan></span>
  if (location.pathname === '/mto/procurement/insights-and-trends/day-wise-coverage') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Insights & Trends / Day Wise Coverage </BoldSpan></span>
  if (location.pathname === '/mto/procurement/insights-and-trends/rmpm-orderwise-coverage') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insights & Trends / RM/PM Orderwise Coverage </BoldSpan></span>
  if (location.pathname === '/mto/procurement/insights-and-trends/rmpm-buffer-trends') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insights & Trends / RM/PM Buffer Trends </BoldSpan></span>
  if (location.pathname === '/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers') return <span>Procurement <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insights & Trends / Expediting RM/Suppliers </BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/insights-and-trends/fol-summary') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} />  <BoldSpan> Insights & Trends / FOL Summary </BoldSpan></span>
  if (location.pathname === '/mto/production-planning-and-scheduling/due-date-quotation') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Due Date Quotation </BoldSpan></span>
  if (location.pathname === '/mto/production-planning-and-scheduling/order-rescheduling') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Order Rescheduling </BoldSpan></span>

  if (location.pathname === '/mto/production-planning-scheduling/dynamic-release-mangement') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Dynamic Release Management </BoldSpan></span>

  if (location.pathname === '/mto/production-planning-scheduling/deptwise-bm-report') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan>Dept-wise BM Report</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/full-kit-assignment') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Full Kit Assignment</BoldSpan></span>
  if (location.pathname === '/mto/production-planning-scheduling/overall-bm-report') return <span>Production Planning & Scheduling <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Overall BM Report</BoldSpan></span>

  if (location.pathname === '/mto/poogi/insight-and-trends/resource-utilization-wip-profile') return <span>Poogi<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> <BoldSpan> Resource Utilization & WIP Profile </BoldSpan></span>
  if (location.pathname === '/mto/poogi/reasons-for-delayed-orders') return <span>Poogi<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Reason For Delayed Orders </BoldSpan></span>
  if (location.pathname === '/mto/poogi/insight-and-trends/otif-analysis') return <span>POOGI <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> OTIF Analysis</BoldSpan></span>
  if (location.pathname === '/mto/poogi/insight-and-trends/ot-and-if-analysis') return <span>POOGI <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insight & Trends / OT & IF Analysis</BoldSpan></span>
  if (location.pathname === '/mto/poogi/insight-and-trends/lead-time') return <span>POOGI <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan>Insight & Trends / Lead Time </BoldSpan> </span>
  if (location.pathname === '/mto/poogi/insight-and-trends/top-failure-reasons') return <span>POOGI <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insight & Trends / Top Failure Reasons </BoldSpan></span>
  if (location.pathname === '/mto/poogi/insight-and-trends/trend-of-failure-reason') return <span>POOGI <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /><BoldSpan> Insight & Trends / Trend Of Failure Reason</BoldSpan></span>


  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Delivery Performance / BM Trend</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan> Delivery Performance /OTIF Analysis</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan> Delivery Performance /OT & IF Analysis</BoldSpan></span>


  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Delivery Performance / Lead Time</BoldSpan></span>




  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Elapsed Time</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Orders At Risk</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Order Balance</BoldSpan></span>


  if (location.pathname === '/mto/manufacturing-intelligence-hub/future-order-load-chart') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Future Order Load Chart</BoldSpan></span>



  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / FOL Summary</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / STPL & Full Kits</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / Day Wise Coverage</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / RM / PM Order Wise Coverage</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / Expediting - RM & Suppliers</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / RM - PM Buffer Trend</BoldSpan></span>




  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Top Failure Reasons</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Trend Of Failure Reasons</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Resource Utilization & WIP Profile</BoldSpan></span>


  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Delivery Performance / BM Trend</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan> Delivery Performance /OTIF Analysis</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan> Delivery Performance /OT & IF Analysis</BoldSpan></span>


  if (location.pathname === '/mto/manufacturing-intelligence-hub/delivery-performance/lead-time') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Delivery Performance / Lead Time</BoldSpan></span>
  if (location.pathname === '/mta/logistics/intransit-whereabouts') return <span>MDM <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} />In Transit whereabouts</span>



  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Elapsed Time</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Orders At Risk</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Congestion Analysis / Order Balance</BoldSpan></span>





  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / FOL Summary</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / STPL & Full Kits</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / Day Wise Coverage</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / RM / PM Order Wise Coverage</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / Expediting - RM & Suppliers</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Forward Execution / RM - PM Buffer Trend</BoldSpan></span>




  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Top Failure Reasons</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Trend Of Failure Reasons</BoldSpan></span>

  if (location.pathname === '/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile') return <span>Manufacturing Intelligence Hub <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Improvement Areas / Resource Utilization & WIP Profile</BoldSpan></span>


  if( location.pathname==='/mto/production/scheduling' && location.search==='?page=ResourceView') return <span>Production Planning & Scheduling<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Scheduling / Resource View</BoldSpan></span>
  if( location.pathname==='/mto/production/scheduling' && location.search==='?page=JobView') return <span>Production Planning & Scheduling<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Scheduling / Job View</BoldSpan></span>
  if( location.pathname==='/mto/production/scheduling' && location.search==='?page=GridViewR') return <span>Production Planning & Scheduling<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Scheduling / GridView - Resource List</BoldSpan></span>
  if( location.pathname==='/mto/production/scheduling' && location.search==='?page=GridViewJ') return <span>Production Planning & Scheduling<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Scheduling / GridView - Job List</BoldSpan></span>
  if( location.pathname==='/mto/production/scheduling') return <span>Production Planning & Scheduling<img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={8} width={8} /><BoldSpan>Scheduling / Download-Upload Template</BoldSpan></span>
  
  if(location.pathname==='/login-audit-report') return <span> {t("breadCrumb.um")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("Login Audit Report")}</span>;






  if (location.pathname === "/manual-upload") {
    return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.manualUpload")}</span>;
  } else if (location.pathname === "/") {
    // return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.pendingISTRequests")}</span>;
    return <></>;
  } else if (location.pathname === "/ist-forced-closure") {
    return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.ISTForcedClosure")}</span>;
  } else if (location.pathname === "/ist-status") {
    return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.ISTStatus")}</span>;
  } else if (location.pathname === "/store-status") {
    return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.storeStatus")}</span>;
  } else if (location.pathname === "/profile") {
    if (
      user.user.is_admin ||
      user?.roles?.permission?.includes("IST Admin")
    ) {
      return <span> {t("breadCrumb.um")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.administration")}</span>;
    } else {
      return <span> {t("breadCrumb.um")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.myProfile")}</span>;
    }
  } else if (location.pathname === "/availability-comparison") {
    return <span> {t("breadCrumb.ist")} <img src={"/assets/img/VectorFLOW/arrowbreadcrumb.svg"} alt="Arrow" height={11} width={11} /> {t("header.availabilityComparison")}</span>;
  } else {
    return <></>
  }
};

export default BreadCrumb