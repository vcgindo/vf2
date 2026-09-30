export function TooltipRenderer({ datum, xKey }: any) {
  return `
    <div class="ag-chart-tooltip-title" style="background-color: #6C696A; display: flex; justify-content: center; align-items: center">
    ${datum[xKey]}
</div>
<div class="ag-chart-tooltip-content" style="color: white; background-color: #6C696A; padding: 0px 20px;">
<div style="border-top: 1px dashed lightgray"></div>
<div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #151515"></div>
        <div style="display:flex ; width: 100%; justify-content: space-between">
            <div>Black</div>
            <div style="margin-left: 20px"> ${datum["b"]}</div>
        </div>
    </div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #E53F40"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div>Red</div>
            <div>${datum["r"]}</div>
        </div>
    </div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #EBBF2C"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div>Yellow</div>
            <div>${datum["y"]}</div>
        </div>
    </div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #418D18"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div>Green</div>
            <div>${datum["g"]}</div>
        </div>
    </div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #3876FE"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div>Blue</div>
            <div>${datum["bl"]}</div>
        </div>
    </div>
    <div style="display: flex;">
        <div style="margin-right: 10px; margin-top: 5px; height: 10px; width: 10px; background-color: #E8E8E8"></div>
        <div style="display:flex ;width: 100%; justify-content: space-between">
            <div>White</div>
            <div>${datum["w"]}</div>
        </div>
    </div>
</div>`;
}

export function createSeriesData() {
  const seriesData: any = [];
  const labels = [
    { text: "Black", color: "#151515", key: "b" },
    { text: "Red", color: "#E53F40", key: "r" },
    { text: "Yellow", color: "#EBBF2B", key: "y" },
    { text: "Green", color: "#418D18", key: "g" },
    { text: "Blue", color: "#3876FE", key: "bl" },
    { text: "White", color: "#E8E8E8", key: "w" },
  ];

  for (let i = 0; i < labels.length; i++) {
    seriesData.push({
      type: "bar",
      xKey: "trailDept",
      yKey: labels[i].key,
      yName: labels[i].text,
      strokeOpacity: 0,
      fill: labels[i].color,
      stacked: true,
      tooltip: {
        renderer: TooltipRenderer,
      },
    });
  }

  return seriesData;
}

