import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {FileBlob,PresentationFile} from 'file:///C:/Users/Yawllen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {finalizePresentation} from 'file:///C:/Users/Yawllen/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations/container_tools/artifact_tool_utils.mjs';
const root='C:/Users/Yawllen/Documents/GitHub/Nir2';
const skill='C:/Users/Yawllen/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const build=root+'/presentation/.slide5-build';
const final=root+'/presentation/results/NIR2_corrected_with_separate_slide.pptx';
process.env.RUNTIME_NODE_MODULES='C:/Users/Yawllen/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
// Публикуем новый файл без hard link, недоступного в текущей Windows-среде.
fs.link=async(source,destination)=>fs.copyFile(source,destination,fs.constants.COPYFILE_EXCL);
await fs.mkdir(path.dirname(final),{recursive:true});
const result=await finalizePresentation({workspaceDir:root,candidatePath:build+'/candidate_slide6_synced.pptx',finalPath:final,
 pythonExecutable:'C:/Users/Yawllen/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','9144000,6858000'],explicitTotalSlideCount:12,
 fontPolicy:{basis:'reference',families:['Times New Roman'],referencePath:root+'/presentation/NIR2_slide01_v2.pptx',referenceSha256:createHash('sha256').update(await fs.readFile(root+'/presentation/NIR2_slide01_v2.pptx')).digest('hex')},
 requiredNativeChartOwnerSlides:[5,6],verifyArtifactToolImport:true,receiptPath:build+'/validation-corrected-separate-slide.json'});
console.log(JSON.stringify({finalPath:result.finalPath,slideCount:result.firstPartyImport.slideCount,integrity:result.packageIntegrity.status,charts:result.nativeChartValidation.passed}));
const p=await PresentationFile.importPptx(await FileBlob.load(final));
for(const index of [5,6]){
 await fs.writeFile(root+'/presentation/results/slide'+String(index+1).padStart(2,'0')+'_limits_added_preview.png',new Uint8Array(await (await p.export({slide:p.slides.items[index],format:'png',scale:1.6})).arrayBuffer()));
}
console.log('Final slide preview saved');
