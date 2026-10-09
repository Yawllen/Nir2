import fs from 'node:fs/promises';
import {Presentation,PresentationFile} from 'file:///C:/Users/Yawllen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/Yawllen/Documents/GitHub/Nir2';
const m=JSON.parse(await fs.readFile(root+'/outputs/model_v12_report/metrics_v12.json','utf8')).splits.valid.printer_at_0_3;
if(m.tp!==6||m.fn!==5||m.fp!==0||m.tn!==128)throw Error('Unexpected validation data');
const p=Presentation.create({slideSize:{width:960,height:720}}),s=p.slides.add();
s.background.fill='#ffffff';
function text(name,value,x,y,w,h,size=25,bold=false,color='#000000',align='left'){
 const sh=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text.style={typeface:'Times New Roman',fontSize:size,color,bold,alignment:align,verticalAlignment:'top',insets:0,autoFit:'none'};sh.text=value;
}
function box(name,x,y,w,h,fill,line='none'){
 s.shapes.add({name,geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:line==='none'?0:1,style:line==='none'?'solid':'dash'}});
}
text('Заголовок','Ограничения обнаружения дефектов',40,10,880,65,47,false,'#000000','center');
text('Выборка','Валидация на кадрах собственного принтера, порог 0,3',45,100,870,32,24,false,'#000000','center');
text('Полнота','54,55 %',48,158,310,83,64,true,'#2467b2');
text('Расшифровка','Полнота обнаружения:\nмодель нашла 6 из 11\nкадров с дефектом',49,252,310,110,27);
text('Кадры','11 кадров с дефектом',384,170,526,35,29,true,'#000000','center');
for(let i=0;i<11;i++){
 const x=390+i*47;
 box('Кадр '+(i+1),x,229,41,71,i<6?'#ccebdc':'#ffdddd');
 text('Номер кадра '+(i+1),String(i+1),x,249,41,30,24,true,i<6?'#176749':'#a52b37','center');
}
text('Найденные','6 обнаружены',390,318,280,36,28,true,'#176749','center');
text('Пропущенные','5 пропущены',672,318,234,36,28,true,'#a52b37','center');
box('Проверка без дефекта',48,401,393,202,'none','#000000');
text('Ложные тревоги','Кадры без дефекта',62,413,365,35,28,true);
text('Ложные тревоги число','0 из 128',62,455,365,46,36,true,'#176749');
text('Ложные тревоги смысл','На этой выборке модель\nне выдала ложных тревог.\nНужны новые сессии проверки.',62,505,365,87,23);
box('Смысл оценки',468,401,444,202,'none','#000000');
text('Ограничение заголовок','Как понимать результат',482,413,414,35,28,true);
text('Ограничение текст','54,55 % относится к кадрам\nс дефектом в этой выборке.\nОценка по 11 таким кадрам\nне даёт надёжного прогноза\nдля новых печатных заданий.',482,461,414,134,24);
text('Отличие общего теста','Высокие показатели на общем наборе не подтверждают такую же полноту на кадрах собственного принтера.',48,635,860,58,25);
text('Номер','7',898,690,34,27,26.667,false,'#000000','right');
s.speakerNotes.text='Источник: '+root+'/outputs/model_v12_report/metrics_v12.json; срез valid.printer_at_0_3: TP6 FN5 FP0 TN128, N139. Полнота = TP/(TP+FN) = 6/11 = 54,55 %. Это валидационная выборка выбора весов, не независимый тест. Один кадр меняет оценку полноты на 9,09 процентного пункта. Частота обнаружения по печатным заданиям не измерена. Причина различий с общим набором экспериментально не установлена.';
await (await PresentationFile.exportPptx(p)).save(root+'/presentation/.slide5-build/limits.pptx');
console.log('Created one distinct limitations slide, without training curves');
