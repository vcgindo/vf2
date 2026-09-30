import { useState } from 'react';
import MultiRangeSlider from 'multi-range-slider-react';
import './style.css'

const DualRangeSlider = () => {
  const [rangeValues, setRangeValues] = useState({
    min: 1,
    max: 90,
  });

  const handleInput = (e:any) => {
    const min = e.minValue;
    const max = e.maxValue;
      setRangeValues({ min, max });
      // console.log('min',min,'max', max)  
  };

  return (
    <div style={{ padding: '20px', width:'300px' }}>
      <MultiRangeSlider
        min={0}
        max={90}
        step={1}
        minValue={rangeValues.min}
        maxValue={rangeValues.max}
        onInput={handleInput}
      />
    </div>
  );
};

export default DualRangeSlider;