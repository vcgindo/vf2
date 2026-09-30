export const formDataPermission = ({
  parent,
  child,
  grandChild,
  keyParent,
  keyChild,
  keyGrandChild,
}: any) => {
  const dataPermission: any = [];
  let formData: any;
  if (parent?.length > 0) {
    for (const eleParent of parent) {
      let isAddParent: any = false;
      if (child?.length > 0) {
        for (const eleChild of child) {
          let isAddChild: any = false;
          if (eleChild.value.split(" > ").includes(eleParent.value)) {
            const dataChild: any = eleChild.value.split(" > ");
            if (grandChild?.length > 0) {
              for (const eleGrandChild of grandChild) {

                const splitValue = eleGrandChild.value.split(" > ").slice(0, 3);
                const exactMatchValue = splitValue[0] + " > " + splitValue[1];
                if (exactMatchValue === eleChild.value) {
                  const dataGrandChild = eleGrandChild.value.split(" > ");
                  formData = {
                    [keyParent]: eleParent.value,
                    [keyChild]: dataChild[1],
                    [keyGrandChild]: dataGrandChild[2],
                  };
  
                  dataPermission.push(formData);
                  isAddParent = true;
                  isAddChild = true;
                }
              }
  
              if (!isAddChild) {
                formData = {
                  [keyParent]: eleParent.value,
                  [keyChild]: dataChild[1],
                };
                dataPermission.push(formData);
                isAddParent = true;
              }
            } else {
              formData = {
                [keyParent]: eleParent.value,
                [keyChild]: dataChild[1],
              };
              dataPermission.push(formData);
              isAddParent = true;
            }
          }
        }
  
        if (!isAddParent) {
          formData = { [keyParent]: eleParent.value };
          dataPermission.push(formData);
        }
      } else {
        formData = { [keyParent]: eleParent.value };
        dataPermission.push(formData);
      }
    }
    return dataPermission;
  }

};

export const handleSelectParent = ({
  e,
  dataAll,
  child,
  grandChild,
  setChild,
  setGrandChild,
}: any) => {
  const keyChildArr: any = [];
  const newObjChild: any = {};
  const valueChild: any = [];
  const valueGrandChild: any = [];

  e.forEach((eleParent: any) => {
    Object.keys(dataAll[eleParent.value])?.forEach((keyChild: any) => {
      const dataChild = {
        label: `${eleParent.value} > ${keyChild}`,
        value: `${eleParent.value} > ${keyChild}`,
      };
      keyChildArr.push(dataChild);
      newObjChild[keyChild] = dataAll[eleParent.value][keyChild];
    });

    if (child?.length > 0) {
      child.forEach((eleChild: any) => {
        if (eleChild.value.split(' > ')[0].includes(eleParent.value)) {
          valueChild.push(eleChild);
        }
      });
    }

    if (grandChild?.length > 0) {
      for (const eleGrandChild of grandChild) {
        if (eleGrandChild.value.includes(`${eleParent.value} > `)) {
          valueGrandChild.push(eleGrandChild);
        }
      }
    }
  });
 
  setChild(valueChild);
  setGrandChild(valueGrandChild);
};

export const handleSelectChild = ({
  e,
  grandChild,
  valueParent,
  setParent,
  setGrandChild,
}: any) => {
  const valueGrandChild: any = [];
  const newParentArr =
    valueParent?.length > 0 ? valueParent?.map((item: any) => item.value) : [];

  e.forEach((eleChild: any) => {
    const childArr = eleChild.value.split(" > ");
    if (!newParentArr.includes(childArr[0])) {
      newParentArr.push(childArr[0]);
    }

    if (grandChild?.length > 0) {
      for (const eleGrandChild of grandChild) {
        const splitValue = eleGrandChild.value.split(" > ").slice(0, 3);
        const exactMatchValue = splitValue[0] + " > " + splitValue[1];
        if (exactMatchValue === eleChild.value) {
          valueGrandChild.push(eleGrandChild);  
        }
      }
    }
  });

  const newValueBrand = newParentArr?.map((item: any) => ({
    label: item,
    value: item,
  }));
  setGrandChild(valueGrandChild);
  setParent(newValueBrand);
};

export const handleSelectGrandChild = ({
  e,
  valueParent,
  setParent,
  valueChild,
  setChild,
}: any) => {
  const newParentArr =
    valueParent?.length > 0 ? valueParent?.map((item: any) => item.value) : [];
  const newChildArr =
    valueChild?.length > 0 ? valueChild?.map((item: any) => item.value) : [];

  e.forEach((element: any) => {
    const elementArr = element.value.split(" > ");

    if (!newParentArr.includes(elementArr[0])) {
      newParentArr.push(elementArr[0]);
    }

    if (!newChildArr.includes(`${elementArr[0]} > ${elementArr[1]}`)) {
      newChildArr.push(`${elementArr[0]} > ${elementArr[1]}`);
    }
  });

  const newValueParent = newParentArr?.map((item: any) => ({
    label: item,
    value: item,
  }));
  const newValueChild = newChildArr?.map((item: any) => ({
    label: item,
    value: item,
  }));

  setParent(newValueParent);
  setChild(newValueChild);
  
};
