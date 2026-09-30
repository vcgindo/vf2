let numberFormat = 'USA'; //by default if not in table

export function setNumberFormat(value?: any) {
  if (value && value.trim() !== '') {
    numberFormat = value;
  } else {
    numberFormat = 'USA';
  }
}

export function getNumberFormat() {
  return numberFormat;

}

