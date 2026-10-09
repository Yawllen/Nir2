import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const runtime = String.raw`C:\Users\Yawllen\.cache\codex-runtimes\codex-primary-runtime\dependencies`;
process.env.RUNTIME_NODE_MODULES = path.join(runtime, 'node', 'node_modules');
const skill = String.raw`C:\Users\Yawllen\.codex\plugins\cache\openai-primary-runtime\presentations\26.1007.11041\skills\presentations`;
const workspace = String.raw`C:\Users\Yawllen\Documents\GitHub\Nir2\presentation`;
const build = path.join(workspace, '.slides05-06-build');
const source = path.join(workspace, 'NIR2_slide01_v2.pptx');
const output = path.join(workspace, 'results', 'NIR2_slides05_06_unified_v2.pptx');
const { Presentation, PresentationFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool', { paths: [path.join(runtime, 'node', 'node_modules')] })).href);
const { applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools', 'artifact_tool_utils.mjs')).href);

const extract = String.raw`import zipfile,xml.etree.ElementTree as E,json,hashlib,sys
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
p=sys.argv[1]
with zipfile.ZipFile(p) as z:
 data=[]
 for i in (1,2,3,4):
  r=E.fromstring(z.read(f'ppt/charts/chart{i}.xml'))
  data.append([[float(x.text) for x in s.findall('c:val//c:v',ns)] for s in r.findall('.//c:ser',ns)])
 print(json.dumps({'charts':data,'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()}))`;
const data = JSON.parse(execFileSync(path.join(runtime, 'python', 'python.exe'), ['-c', extract, source], { encoding: 'utf8' }));
const [loss, ap, recall] = data.charts.map(c => c[0]);
assert.equal(loss.length, 20);
assert.equal(ap.length, 20);
assert.equal(recall.length, 20);
assert.ok(Math.abs(recall[18] - 6 / 11 * 100) < 0.000001);
assert.equal(data.charts[3][0][18], 0);
assert.ok(Math.abs((3337 - 13) / 3337 * 100 - 99.61) < 0.005);

const FONT = 'Times New Roman';
const C = { ink: '#222C38', blue: '#2467A6', orange: '#D97720', grid: '#E3E7EB', muted: '#5B6570', pale: '#EEF3F8', selected: '#FFF0DE' };
const p = Presentation.create({ slideSize: { width: 960, height: 720 } });
p.theme.defaultFont = FONT;
const style = { fontFamily: FONT, typeface: FONT, color: C.ink, fontSize: 22, alignment: 'left', verticalAlignment: 'middle', insets: 0 };

function text(slide, value, x, y, w, h, options = {}) {
  const sh = slide.shapes.add({ geometry: 'textbox', position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { width: 0, fill: 'none' } });
  sh.text = value;
  sh.text.style = { ...style, ...options };
  return sh;
}
function line(slide, x, y, w, color = C.grid) {
  slide.shapes.add({ geometry: 'line', position: { left: x, top: y, width: w, height: 0 }, line: { style: 'solid', fill: color, width: 1 }, fill: 'none' });
}
function base(title, page, subtitle) {
  const s = p.slides.add();
  s.background.fill = '#FFFFFF';
  text(s, title, 40, 25, 880, 54, { fontSize: 40 });
  text(s, subtitle, 42, 85, 660, 27, { fontSize: 20, color: C.muted });
  s.shapes.add({ geometry: 'ellipse', position: { left: 761, top: 92, width: 10, height: 10 }, fill: C.orange, line: { fill: '#FFFFFF', width: 1 } });
  text(s, '19-я эпоха', 784, 85, 136, 27, { fontSize: 19, color: C.orange });
  line(s, 40, 120, 880);
  text(s, String(page), 875, 679, 45, 25, { fontSize: 22, color: '#8B9299', alignment: 'right' });
  return s;
}
function chart(slide, name, values, frame, yTitle, min, max, step, format, selectedLabel) {
  const chosen = values[18];
  const solid = { style: 'solid', fill: C.blue, width: 2.5 };
  const dash = { style: 'dashed', fill: C.orange, width: 1.5 };
  const native = slide.charts.add('scatter', {
    position: frame,
    title: name,
    titleTextStyle: { fontSize: 23, fill: C.ink, bold: true },
    scatterOptions: { style: 'lineWithMarkers' },
    hasLegend: false,
    chartFill: '#FFFFFF',
    chartLine: { fill: 'none', width: 0 },
    plotAreaFill: '#FFFFFF',
    plotAreaLine: { fill: 'none', width: 0 },
    series: [
      { name: 'Метрика по эпохам', xValues: values.map((_, i) => i + 1), values, line: solid, marker: { symbol: 'circle', size: 3, fill: C.blue } },
      { name: 'Проекция на ось эпох', xValues: [19, 19], values: [min, chosen], line: dash, marker: { symbol: 'none' } },
      { name: 'Проекция на ось метрики', xValues: [0, 19], values: [chosen, chosen], line: dash, marker: { symbol: 'none' } },
      { name: '19-я эпоха', xValues: [19], values: [chosen], line: { fill: 'none', width: 0 }, marker: { symbol: 'diamond', size: 10, fill: C.orange }, dataLabels: { showValue: true, position: 'top', numberFormatCode: format, textStyle: { fontSize: 18, bold: true, fill: C.orange } }, dataLabelOverrides: [{ idx: 0, text: selectedLabel, showValue: true, position: 'top', textStyle: { fontSize: 18, bold: true, fill: C.orange } }] },
      { name: 'Метка эпохи на оси', xValues: [19], values: [min], line: { fill: 'none', width: 0 }, marker: { symbol: 'triangle', size: 5, fill: C.orange }, dataLabels: { showValue: true, position: 'top', textStyle: { fontSize: 16, bold: true, fill: C.orange } }, dataLabelOverrides: [{ idx: 0, text: '19', showValue: true, position: 'top', textStyle: { fontSize: 16, bold: true, fill: C.orange } }] },
    ],
    xAxis: { title: { text: 'Эпоха', textStyle: { fontSize: 19, fill: C.ink } }, min: 0, max: 20, majorUnit: 5, numberFormatCode: '0', textStyle: { fontSize: 17, fill: C.ink }, line: { style: 'solid', fill: '#A4ABB3', width: 1 }, majorGridlines: null, minorGridlines: null },
    yAxis: { title: { text: yTitle, textStyle: { fontSize: 19, fill: C.ink } }, min, max, majorUnit: step, numberFormatCode: format, textStyle: { fontSize: 17, fill: C.ink }, line: { style: 'solid', fill: '#A4ABB3', width: 1 }, majorGridlines: { style: 'solid', fill: C.grid, width: 0.7 }, minorGridlines: null },
  });
  applyPresentationChartFont(native, { fontFamily: FONT });
  return native;
}
function table(slide, values, frame, widths, selectedRow = -1) {
  const t = slide.tables.add({ rows: values.length, columns: values[0].length, ...frame, columnWidths: widths, values });
  t.borders.assign({ style: 'solid', fill: C.grid, width: 0.7 });
  t.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({ textStyle: { ...style, fontSize: 20, alignment: 'center' }, margins: { left: 7, right: 7, top: 6, bottom: 6 }, anchor: 'center' });
  for (let r = 0; r < values.length; r++) {
    t.rows[r].height = frame.height / values.length;
    for (let c = 0; c < values[0].length; c++) {
      const cell = t.getCell(r, c);
      cell.fill = r === 0 ? C.pale : r === selectedRow ? C.selected : '#FFFFFF';
      cell.text.style = { ...style, fontSize: r === 0 ? 19 : 22, bold: r === 0 || r === selectedRow, alignment: 'center', color: r === selectedRow ? '#9A4D10' : C.ink };
    }
  }
  return t;
}

const s5 = base('Результаты обучения и тестирования', 5, 'Дообучение ResNet18 на общей выборке, 20 эпох');
chart(s5, 'Функция потерь при обучении', loss, { left: 40, top: 137, width: 425, height: 250 }, 'Функция потерь', 0, 0.01, 0.002, '0.000', '0,0022');
chart(s5, 'Средняя точность на валидации', ap, { left: 495, top: 137, width: 425, height: 250 }, 'AP, %', 98.5, 100, 0.5, '0.0', '99,25 %');
text(s5, 'Рис. 4 – Функция потерь по эпохам', 40, 396, 425, 25, { fontSize: 18, alignment: 'center' });
text(s5, 'Рис. 5 – Средняя точность AP на валидации', 495, 396, 425, 25, { fontSize: 18, alignment: 'center' });
text(s5, 'Таблица 1 – Результаты на тестовой выборке', 42, 433, 876, 32, { fontSize: 26, bold: true });
table(s5, [
  ['Точность\n(precision)', 'Полнота\n(recall)', 'Мера F1', 'Доля верных\nответов', 'Средняя\nточность AP'],
  ['98,71 %', '99,89 %', '99,30 %', '99,61 %', '99,72 %'],
], { left: 40, top: 479, width: 880, height: 92 }, [176, 176, 176, 176, 176]);
text(s5, '13 ошибок на 3 337 тестовых кадрах', 42, 590, 876, 35, { fontSize: 28, bold: true, color: C.blue });
text(s5, 'Похожие кадры и использование теста при разработке могут завышать оценку.', 42, 639, 864, 35, { fontSize: 20, color: C.muted });

const s6 = base('Проверка на экспериментальном принтере', 6, 'Порог классификации 0,3. Выбор весов модели');
chart(s6, 'Полнота обнаружения по эпохам', recall, { left: 40, top: 140, width: 435, height: 275 }, 'Полнота, %', 0, 100, 25, '0', '54,55 %');
text(s6, 'Рис. 6 – Полнота обнаружения на кадрах принтера', 40, 427, 435, 25, { fontSize: 18, alignment: 'center' });
text(s6, 'Таблица 2 – Сравнение эпох', 501, 150, 419, 30, { fontSize: 25, bold: true });
table(s6, [
  ['Эпоха', 'Полнота,\n%', 'Ложные\nтревоги, %', 'AP, %'],
  ['9', '72,73', '7,03', '75,12'],
  ['18', '54,55', '0,00', '92,31'],
  ['19', '54,55', '0,00', '94,63'],
  ['20', '54,55', '0,00', '92,45'],
], { left: 500, top: 193, width: 420, height: 231 }, [67, 111, 132, 110], 3);
line(s6, 40, 461, 880);
text(s6, '6 из 11', 42, 481, 205, 61, { fontSize: 48, bold: true, color: C.blue });
text(s6, 'дефектных кадров обнаружены\n5 кадров пропущены', 262, 480, 657, 65, { fontSize: 24 });
text(s6, 'Выбрана 19-я эпоха: среди эпох 18–20 при одинаковой полноте\nи отсутствии ложных тревог получено наибольшее значение AP.', 42, 567, 878, 62, { fontSize: 23 });
text(s6, 'Ложные тревоги допустимы в пределах 1 %. Проверка на 11 дефектных кадрах\nпредварительная. Требуется расширение независимой выборки.', 42, 638, 868, 43, { fontSize: 18, color: C.muted });

assert.equal(p.slides.items.length, 2);
assert.equal(s5.charts.items.length, 2);
assert.equal(s6.charts.items.length, 1);
await fs.mkdir(build, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });
await fs.writeFile(path.join(build, 'source-data.json'), JSON.stringify(data, null, 2));
const candidate = path.join(build, 'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
for (const [i, s] of p.slides.items.entries()) {
  const png = await p.export({ slide: s, format: 'png', scale: 1.5 });
  await fs.writeFile(path.join(build, `slide${i + 5}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({ candidate, previews: [path.join(build, 'slide5.png'), path.join(build, 'slide6.png')] }));
if (process.argv.includes('--finalize')) {
  const result = await finalizePresentation({
    workspaceDir: workspace, candidatePath: candidate, finalPath: output,
    explicitTotalSlideCount: 2,
    pythonExecutable: path.join(runtime, 'python', 'python.exe'),
    integrityValidatorPath: path.join(skill, 'container_tools', 'inspect_presentation_package_integrity.py'),
    layoutValidatorPath: path.join(skill, 'container_tools', 'inspect_presentation_layout_geometry.py'),
    layoutArgs: ['--expected-slide-size-emu', '9144000,6858000', '--validate-heading-fit', '--require-native-table-slide', '1', '--require-native-table-slide', '2'],
    requiredNativeTableOwnerSlides: [1, 2], requiredNativeChartOwnerSlides: [1, 2],
    materializeLiteralChartWorkbooks: true,
    fontPolicy: { basis: 'reference', families: [FONT], referencePath: source, referenceSha256: data.sha256 },
    verifyArtifactToolImport: true,
    receiptPath: path.join(build, 'validation-v2.json'),
  });
  console.log(JSON.stringify(result));
}
