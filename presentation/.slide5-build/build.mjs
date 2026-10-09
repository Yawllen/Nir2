import fs from 'node:fs/promises';
import {Presentation, PresentationFile} from 'file:///C:/Users/Yawllen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {applyPresentationChartFont} from 'file:///C:/Users/Yawllen/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations/container_tools/artifact_tool_utils.mjs';

const root='C:/Users/Yawllen/Documents/GitHub/Nir2';
const out=root+'/presentation/.slide5-build';
const model='C:/Users/Yawllen/Documents/GitHub/printer-defect-server/models/spaghetti_presence_v12';
const metrics=JSON.parse(await fs.readFile(root+'/outputs/model_v12_report/metrics_v12.json','utf8'));
const history=JSON.parse(await fs.readFile(model+'/history.json','utf8'));
const m=metrics.splits.valid.printer_at_0_3;
if(history.length!==20 || metrics.best_epoch!==19 || m.tp!==6 || m.fp!==0 || m.fn!==5 || m.tn!==128) throw Error('Unexpected source data');
const p=Presentation.create({slideSize:{width:960,height:720}});
let s=p.slides.add();s.background.fill='#ffffff';
function text(name,t,x,y,w,h,size=24,bold=false,align='left',border=false,color='#1d2733'){
 const sh=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:border?'#000000':'none',style:border?'dash':'solid',width:border?1:0}});
 sh.text.style={typeface:'Times New Roman',fontSize:size,color,bold,alignment:align,verticalAlignment:'top',insets:border?9:0,autoFit:'none'};sh.text=t;return sh;
}
const b=t=>({run:t,style:{bold:true}});
text('Заголовок','Проверка модели на кадрах принтера',45,5,870,70,48,false,'center');
text('Ошибка обучения','Ошибка обучения',38,88,418,30,25.333,true,'center',false,'#2467b2');
text('Валидация','Полнота на кадрах принтера',502,88,418,30,25.333,true,'center',false,'#7c4bb1');
function curve(key,x,lo,hi,unit,format){
 const color=key==='loss'?'#2467b2':'#7c4bb1';
 const chart=s.charts.add('line',{
  position:{left:x,top:131,width:433,height:185},categories:history.map(r=>String(r.epoch)),
  series:[{name:key==='loss'?'Ошибка обучения':'Полнота на кадрах принтера, %',values:history.map(r=>Number((key==='loss'?r.loss:r.target_at_0_3.recall*100).toFixed(6))),line:{fill:color,width:2.4},marker:{symbol:'none'},dataLabels:{showValue:false}}],
  hasLegend:false,lineOptions:{smooth:false},xAxis:{title:'Эпоха',textStyle:{fontSize:15,fill:'#000000'},line:{fill:'#000000',width:.8}},
  yAxis:{min:lo,max:hi,majorUnit:unit,numberFormatCode:format,textStyle:{fontSize:15,fill:'#000000'},majorGridlines:{fill:'#d0d0d0',width:.6}},chartFill:'#ffffff',plotAreaFill:'#ffffff'});
 applyPresentationChartFont(chart,{fontFamily:'Times New Roman'});
 const label=chart.series.getItemAt(0).dataLabelOverrides.add(18);
 label.text='19';label.position='top';label.showValue=true;
 label.textStyle.typeface='Times New Roman';label.textStyle.fontSize=17;label.textStyle.fill=color;label.textStyle.bold=true;
 chart.series.getItemAt(0).dataLabels.textStyle.typeface='Times New Roman';
}
curve('loss',31,0,0.010,0.002,'0.000');
curve('recall',494,0,100,25,'0" %"');
text('Матрица ошибок','Матрица ошибок на валидации',38,345,412,30,25.333,true,'center');
text('Порог','139 кадров принтера; порог 0,3',41,381,405,26,20,false,'center');
text('Предсказание','Ответ модели',175,414,265,23,18.667,false,'center');
text('Разметка','По\nразметке',45,424,111,45,18.667,false,'right');
text('Нет дефекта','Нет дефекта',170,440,131,23,18.667,false,'center');
text('Спагетти','«Спагетти»',310,440,131,23,18.667,false,'center');
text('Истинный нет','Нет\nдефекта',45,484,111,52,20,false,'right');
text('Истинный да','«Спагетти»',40,588,116,27,20,false,'right');
for(const [name,v,x,y,fill,color,label] of [
 ['TN',m.tn,170,469,'#e3f3eb','#176749','Дефекта нет'],
 ['FP',m.fp,308,469,'#ffe7bf','#92510c','Ложная тревога'],
 ['FN',m.fn,170,559,'#ffdddd','#a52b37','Пропуск дефекта'],
 ['TP',m.tp,308,559,'#ccebdc','#176749','Дефект найден']]){
 s.shapes.add({name,geometry:'rect',position:{left:x,top:y,width:138,height:90},fill,line:{fill:'#ffffff',width:2,style:'solid'}});
 text('Число '+name,String(v),x,y+12,138,38,32,true,'center',false,color);
 text('Смысл '+name,label,x+3,y+56,132,24,17.333,false,'center',false,color);
}
text('Метрики заголовок','Результат валидации принтера',500,345,422,30,25.333,true,'center');
const fmt=v=>(v*100).toFixed(2).replace('.',',')+' %';
s.shapes.add({name:'Рамка метрик',geometry:'rect',position:{left:498,top:381,width:424,height:154},fill:'none',line:{fill:'#000000',style:'dash',width:1}});
text('Основной результат','Полнота '+fmt(m.recall),509,391,405,46,38,true,'left',false,'#2467b2');
text('Обнаружения','Обнаружены 6 из 11; пропущены 5',509,444,405,28,22);
text('Ложные тревоги','Ложные тревоги: 0 из 128',509,475,405,28,22);
text('F1','Мера F1: '+fmt(m.f1),509,506,405,26,21.333);
text('Смысл проверки','Почему выбрана 19-я эпоха',498,553,424,29,24,true,'left',false,'#7c4bb1');
text('Объяснение','При пределе ложных тревог 1 % это максимальная полнота. Среди эпох с таким результатом у 19-й выше средняя точность: 94,63 %. Выборку нужно расширить новыми сессиями.',498,589,424,99,19.333);
text('Номер','6',898,690,34,27,26.667,false,'right');
s.speakerNotes.text='Источники: '+root+'/outputs/model_v12_report/metrics_v12.json; '+model+'/history.json; '+model+'/training_config.json. Показан срез valid.printer_at_0_3: TP=6, FP=0, FN=5, TN=128, всего 139 кадров. Полнота 54.55 %, F1 70.59 %. Это валидация принтера, а не независимый тест и не оценка обнаружения по печатным заданиям. Веса 19-й эпохи выбирались по этой валидации при пороге 0.3. Общие тестовые метрики из смешанного набора не показаны. Обучение выполнено из ранее полученных весов.';
const slide5=s;
s=p.slides.add();s.background.fill='#ffffff';
text('Заголовок выбора','Почему выбраны веса 19-й эпохи',45,5,870,70,49.333,false,'center');
text('Правило выбора','Максимум полноты при доле ложных тревог не выше 1 %',44,88,874,35,26,true,'center',false,'#2467b2');
text('Выборка для выбора','Валидация принтера: 11 кадров с дефектом и 128 без него; порог 0,3',45,131,870,28,20,false,'center');
text('Полнота заголовок','Полнота обнаружения, %',38,179,418,31,25.333,true,'center',false,'#2467b2');
text('Тревоги заголовок','Доля ложных тревог, %',500,179,418,31,25.333,true,'center',false,'#a52b37');
function targetCurve(key,x,max,unit,color){
 const series=[{name:key==='recall'?'Полнота, %':'Ложные тревоги, %',values:history.map(r=>Number((r.target_at_0_3[key]*100).toFixed(6))),line:{fill:color,width:2.4},marker:{symbol:'circle',size:3,fill:color},dataLabels:{showValue:false}}];
 if(key==='false_alarm_rate')series.push({name:'Допустимый предел 1 %',values:history.map(()=>1),line:{fill:'#d48923',width:1.7,style:'dash'},marker:{symbol:'none'}});
 const chart=s.charts.add('line',{position:{left:x,top:224,width:433,height:191},categories:history.map(r=>String(r.epoch)),series,hasLegend:false,lineOptions:{smooth:false},
 xAxis:{title:'Эпоха',textStyle:{fontSize:15,fill:'#000000'}},yAxis:{min:0,max,majorUnit:unit,numberFormatCode:'0" %"',textStyle:{fontSize:15,fill:'#000000'},majorGridlines:{fill:'#d0d0d0',width:.6}},chartFill:'#ffffff',plotAreaFill:'#ffffff'});
 applyPresentationChartFont(chart,{fontFamily:'Times New Roman'});
 const label=chart.series.getItemAt(0).dataLabelOverrides.add(18);
 label.text='19';label.position='top';label.showValue=true;
 label.textStyle.typeface='Times New Roman';label.textStyle.fontSize=18;label.textStyle.fill=color;label.textStyle.bold=true;
 chart.series.getItemAt(0).dataLabels.textStyle.typeface='Times New Roman';
}
targetCurve('recall',31,100,25,'#2467b2');
targetCurve('false_alarm_rate',494,8,2,'#a52b37');
text('Предел','Пунктир — допустимая доля ложных тревог 1 %',499,421,425,24,18.667,false,'center',false,'#92510c');
const cols=[75,164,207,168,250];
const labels=['Эпоха','Полнота, %','Ложные тревоги, %','Средняя точность','Решение'];
const rows=[9,18,19,20].map(epoch=>{
 const t=history[epoch-1].target_at_0_3;
 return [String(epoch),(t.recall*100).toFixed(2).replace('.',','),(t.false_alarm_rate*100).toFixed(2).replace('.',','),(t.image_AP*100).toFixed(2).replace('.',',')+' %',epoch===9?'Превышен предел 1 %':epoch===19?'Выбрана':'Средняя точность ниже'];
});
const eligible=history.filter(r=>r.target_at_0_3.false_alarm_rate<=.01);
const best=eligible.sort((a,b)=>b.target_at_0_3.recall-a.target_at_0_3.recall || a.target_at_0_3.false_alarm_rate-b.target_at_0_3.false_alarm_rate || b.target_at_0_3.image_AP-a.target_at_0_3.image_AP || b.image_AP-a.image_AP)[0];
if(best.epoch!==19)throw Error('Selection criterion does not match epoch 19');
[labels,...rows].forEach((row,i)=>{
 let x=48;
 row.forEach((value,j)=>{
  const fill=i===0?'#e7edf6':i===3?'#d3edde':i===1?'#fff0dc':'#ffffff';
  s.shapes.add({name:'Таблица '+i+' '+j,geometry:'rect',position:{left:x,top:459+i*33,width:cols[j],height:33},fill,line:{fill:'#b4bec9',width:.7,style:'solid'}});
  text('Текст '+i+' '+j,value,x+4,466+i*33,cols[j]-8,25,i===0?17.333:20,i===0||i===3,'center',false,i===3?'#176749':'#1d2733');
  x+=cols[j];
 });
});
text('Обоснование','19-я эпоха: 6 из 11 дефектных кадров, ни одной ложной тревоги. При равной полноте средняя точность на кадрах принтера максимальна.',48,643,864,51,22);
text('Номер','6',898,690,34,27,26.667,false,'right');
s.speakerNotes.text='Источник: '+model+'/history.json; '+model+'/training_config.json. Правило выбора: максимальная полнота при false_alarm_rate <= 0.01 на валидации принтера и пороге 0.3. При равной полноте предпочтение отдаётся меньшей доле ложных тревог, затем большей AP принтера, затем общей AP. Эпохи 11,17,18,19,20 имеют полноту 6/11 и FP=0; AP принтера: 88.47,90.26,92.31,94.63,92.45 %. Тест не использован для выбора весов. Общие графики на слайде 5 описывают другой срез качества. Оценка по 11 положительным и 128 отрицательным кадрам предварительная.';
await fs.mkdir(out,{recursive:true});
await (await PresentationFile.exportPptx(p)).save(out+'/slide5.pptx');
await fs.writeFile(out+'/slide5.png',new Uint8Array(await (await p.export({slide:slide5,format:'png',scale:1.6})).arrayBuffer()));
await fs.writeFile(out+'/slide6.png',new Uint8Array(await (await p.export({slide:s,format:'png',scale:1.6})).arrayBuffer()));
console.log('Slide built');
