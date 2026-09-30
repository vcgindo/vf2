export function Rectangle({
  x,
  y,
  size,
  path,
}: {
  x: number;
  y: number;
  size: number;
  path: any;
}) {
      
  const width = size*4; // adjust this factor after checking paddings
  const height = 2;       // thin horizontal line

  path.clear();
  path.rect(x - width / 2, y - height / 2, width, height);
  path.closePath();

}