
export function TooltipRenderer({ datum, yKey }: any) {
    return `
    <div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A">
    <div>
        <div style="display: flex;">
            <div style="display:flex ; width: 100%; justify-content: space-between">
               ${datum[yKey]}
            </div>
        </div>
    </div>`;
  }
