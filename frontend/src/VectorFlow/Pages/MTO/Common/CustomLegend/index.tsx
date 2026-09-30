import { CustomLegendWrapper, LegendOptions, LegendOptionsName, LegendOptionsWrapper } from "./styles";

const CustomLegend = ({chartOptions, setChartOptions}:any) => {

  // Toggle series visibility
  const toggleSeries = (index: number) => {
    const newOptions = { ...chartOptions };
    newOptions.series[index].visible = !newOptions.series[index].visible;
    setChartOptions(newOptions);
  };

  return (
    
      <CustomLegendWrapper>
        {chartOptions.series.map((series: any, i: number) => (
          <LegendOptionsWrapper
            key={i}
            onClick={() => toggleSeries(i)}
            opacity= {series.visible ? 1 : 0.4}
          >
            <LegendOptions
              background={series.fill || series.stroke || "black"}
            />
            <LegendOptionsName>{series.yName || series.yKey}</LegendOptionsName>
          </LegendOptionsWrapper>
        ))}
      </CustomLegendWrapper>
  );
};

export default CustomLegend;
