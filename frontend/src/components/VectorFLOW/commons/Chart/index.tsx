
import {
  Chart as ChartJS,
  LinearScale,
  CategoryScale,
  BarElement,
  PointElement,
  LineElement,
  Legend,
  Tooltip,
  LineController,
  BarController,
  ChartOptions,
  TimeScale,
  Filler,
  TimeSeriesScale,
} from 'chart.js';
// import 'chartjs-adapter-date-fns';
// require('chartjs-adapter-date-fns');
import { forwardRef } from 'react';
import { Chart as ReactChart} from 'react-chartjs-2';

ChartJS.register(
  LinearScale,
  CategoryScale,
  BarElement,
  PointElement,
  LineElement,
  Legend,
  Tooltip,
  LineController,
  BarController,
  TimeScale,
  TimeSeriesScale,
  Filler
);

// const labels = ['January', 'February', 'March', 'April', 'May', 'June', 'July'];

interface ChartProps {
  type:any,
  data:any,
  options?:ChartOptions
}


const Chart = forwardRef(({type,data,options}:ChartProps,ref:any) => {
    return(
        <ReactChart type={type} data={data} options={options} ref={ref}/>
    )
})

export default Chart;
