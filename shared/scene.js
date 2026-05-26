// Shared scene data and SVG rendering — used by scene-demo.html and scene-grid.html

const SHAPES = [
  { id: 'circle',   zh: '圆形',   py: 'yuánxíng',      cpAdj: '圆',    cpPy: 'yuán' },
  { id: 'square',   zh: '正方形', py: 'zhèngfāngxíng', cpAdj: '方',    cpPy: 'fāng' },
  { id: 'triangle', zh: '三角形', py: 'sānjiǎoxíng',   cpAdj: '三角',  cpPy: 'sānjiǎo' },
  { id: 'rect',     zh: '长方形', py: 'chángfāngxíng', cpAdj: '长方',  cpPy: 'chángfāng' },
  { id: 'diamond',  zh: '菱形',   py: 'língxíng',      cpAdj: '菱',    cpPy: 'líng' },
  { id: 'star',     zh: '星形',   py: 'xīngxíng',      cpAdj: '星',    cpPy: 'xīng' },
];

const SIZES = [
  { id: 'sm', zh: '小', py: 'xiǎo',  cpAdj: '小',   cpPy: 'xiǎo',      r: 18, btn: 26 },
  { id: 'md', zh: '中', py: 'zhōng', cpAdj: '中等', cpPy: 'zhōngděng', r: 28, btn: 34 },
  { id: 'lg', zh: '大', py: 'dà',    cpAdj: '大',   cpPy: 'dà',        r: 40, btn: 44 },
];

const COLORS = [
  { id: 'red',    zh: '红色', py: 'hóngsè',  cpAdj: '红', cpPy: 'hóng',  hex: '#C41E3A' },
  { id: 'orange', zh: '橙色', py: 'chéngsè', cpAdj: '橙', cpPy: 'chéng', hex: '#D4682A' },
  { id: 'yellow', zh: '黄色', py: 'huángsè', cpAdj: '黄', cpPy: 'huáng', hex: '#C8940A' },
  { id: 'green',  zh: '绿色', py: 'lǜsè',    cpAdj: '绿', cpPy: 'lǜ',    hex: '#2C6B3E' },
  { id: 'blue',   zh: '蓝色', py: 'lánsè',   cpAdj: '蓝', cpPy: 'lán',   hex: '#2C3E6B' },
  { id: 'purple', zh: '紫色', py: 'zǐsè',    cpAdj: '紫', cpPy: 'zǐ',    hex: '#6B3E8A' },
  { id: 'pink',   zh: '粉色', py: 'fěnsè',   cpAdj: '粉', cpPy: 'fěn',   hex: '#D4608A' },
  { id: 'white',  zh: '白色', py: 'báisè',   cpAdj: '白', cpPy: 'bái',   hex: '#F0EDE8', stroke: '#C0BBB0' },
  { id: 'grey',   zh: '灰色', py: 'huīsè',   cpAdj: '灰', cpPy: 'huī',   hex: '#8A8A90' },
  { id: 'black',  zh: '黑色', py: 'hēisè',   cpAdj: '黑', cpPy: 'hēi',   hex: '#1A1A1E' },
];

function getShape(id) { return SHAPES.find(s => s.id === id); }
function getSize(id)  { return SIZES.find(s => s.id === id); }
function getColor(id) { return COLORS.find(c => c.id === id); }

// SVG shape markup for a 100×100 viewport centered at 50,50
function shapeEl(shapeId, r, fill, stroke, sw) {
  const cx = 50, cy = 50;
  const g = inner => `<g fill="${fill}" stroke="${stroke ?? 'none'}" stroke-width="${sw ?? 0}">${inner}</g>`;
  switch (shapeId) {
    case 'circle':
      return g(`<circle cx="${cx}" cy="${cy}" r="${r}"/>`);
    case 'square': {
      const h = r * 1.3;
      return g(`<rect x="${cx-h}" y="${cy-h}" width="${h*2}" height="${h*2}" rx="2"/>`);
    }
    case 'triangle': {
      const h = r * 1.15;
      return g(`<polygon points="${cx},${cy-h} ${cx-h*1.1},${cy+h*0.72} ${cx+h*1.1},${cy+h*0.72}"/>`);
    }
    case 'rect': {
      const w = r * 1.75, h = r * 0.85;
      return g(`<rect x="${cx-w}" y="${cy-h}" width="${w*2}" height="${h*2}" rx="2"/>`);
    }
    case 'diamond':
      return g(`<polygon points="${cx},${cy-r*1.25} ${cx+r},${cy} ${cx},${cy+r*1.25} ${cx-r},${cy}"/>`);
    case 'star': {
      const o = r, i = r * 0.42, pts = [];
      for (let k = 0; k < 10; k++) {
        const a = (k * Math.PI / 5) - Math.PI / 2, rad = k % 2 === 0 ? o : i;
        pts.push(`${(cx + Math.cos(a)*rad).toFixed(2)},${(cy + Math.sin(a)*rad).toFixed(2)}`);
      }
      return g(`<polygon points="${pts.join(' ')}"/>`);
    }
  }
}

// Mini icon markup for a 24×24 viewport
function shapeIcon(shapeId) {
  const cx = 12, cy = 12, r = 7;
  switch (shapeId) {
    case 'circle':   return `<circle cx="${cx}" cy="${cy}" r="${r}"/>`;
    case 'square':   return `<rect x="${cx-r}" y="${cy-r}" width="${r*2}" height="${r*2}" rx="1"/>`;
    case 'triangle': return `<polygon points="${cx},${cy-r} ${cx-r},${cy+r*0.65} ${cx+r},${cy+r*0.65}"/>`;
    case 'rect':     return `<rect x="${cx-r*1.3}" y="${cy-r*0.55}" width="${r*2.6}" height="${r*1.1}" rx="1"/>`;
    case 'diamond':  return `<polygon points="${cx},${cy-r} ${cx+r*0.75},${cy} ${cx},${cy+r} ${cx-r*0.75},${cy}"/>`;
    case 'star': {
      const o = r, i = r * 0.42, pts = [];
      for (let k = 0; k < 10; k++) {
        const a = (k * Math.PI / 5) - Math.PI / 2, rad = k % 2 === 0 ? o : i;
        pts.push(`${(cx + Math.cos(a)*rad).toFixed(1)},${(cy + Math.sin(a)*rad).toFixed(1)}`);
      }
      return `<polygon points="${pts.join(' ')}"/>`;
    }
  }
}

// Render a shape into an <svg> element given a { shape, size, color } config
function renderScene(svgEl, config) {
  const sh = getShape(config.shape), sz = getSize(config.size), co = getColor(config.color);
  svgEl.innerHTML = shapeEl(sh.id, sz.r, co.hex, co.stroke, co.stroke ? 1.5 : 0);
}

// Compound phrase strings for a config
function compound(config) {
  const sh = getShape(config.shape), sz = getSize(config.size), co = getColor(config.color);
  return { zh: co.cpAdj + sz.cpAdj + sh.cpAdj, py: co.cpPy + ' ' + sz.cpPy + ' ' + sh.cpPy };
}
