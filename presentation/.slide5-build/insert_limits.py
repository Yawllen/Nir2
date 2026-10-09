from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import posixpath

ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(__file__).resolve().parent
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
O='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
R='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'
ns={'p':P,'a':A}
def relpath(part):
 folder,name=posixpath.split(part)
 return posixpath.join(folder,'_rels',name+'.rels')
def serial(root):return E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
with ZipFile(ROOT/'presentation/NIR2_slide01_v2.pptx') as original,ZipFile(BUILD/'limits.pptx') as generated:
 files={n:original.read(n) for n in original.namelist()}
 presentation=E.fromstring(files['ppt/presentation.xml'])
 ids=presentation.find('{'+P+'}sldIdLst')
 assert len(ids)==11
 rels=E.fromstring(files['ppt/_rels/presentation.xml.rels'])
 targets={r.get('Id'):posixpath.normpath(posixpath.join('ppt',r.get('Target'))).lstrip('/') for r in rels}
 types=E.fromstring(files['[Content_Types].xml'])
 gen_types=E.fromstring(generated.read('[Content_Types].xml'))
 overrides={e.get('PartName').lstrip('/'):e.get('ContentType') for e in gen_types if e.tag.endswith('Override')}
 mapped={'ppt/slides/slide1.xml':'ppt/slides/slide12.xml'}
 def copy_part(part):
  if part in mapped and part!='ppt/slides/slide1.xml':return mapped[part]
  dest=mapped.get(part,'ppt/limits7/'+part)
  if dest in files:return dest
  mapped[part]=dest
  files[dest]=generated.read(part)
  rp=relpath(part)
  if rp in generated.namelist():
   links=E.fromstring(generated.read(rp))
   for link in links:
    if link.get('TargetMode')=='External':continue
    target=posixpath.normpath(posixpath.join(posixpath.dirname(part),link.get('Target'))).lstrip('/')
    link.set('Target',posixpath.relpath(copy_part(target),posixpath.dirname(dest)))
   files[relpath(dest)]=serial(links)
  if part in overrides:E.SubElement(types,'{'+C+'}Override',PartName='/'+dest,ContentType=overrides[part])
  return dest
 copy_part('ppt/slides/slide1.xml')
 rid='rIdLimits7'
 assert rid not in targets
 E.SubElement(rels,'{'+R+'}Relationship',Id=rid,Type=O+'/slide',Target='slides/slide12.xml')
 entry=E.Element('{'+P+'}sldId',id=str(max(int(i.get('id')) for i in ids)+1))
 entry.set('{'+O+'}id',rid)
 ids.insert(6,entry)
 changed=set()
 for index in range(7,12):
  part=targets[ids[index].get('{'+O+'}id')]
  slide=E.fromstring(files[part])
  count=0
  for shape in slide.findall('.//p:sp',ns):
   ph=shape.find('p:nvSpPr/p:nvPr/p:ph',ns)
   if ph is not None and ph.get('type')=='sldNum':
    for t in shape.findall('.//a:t',ns):
     if t.text==str(index):t.text=str(index+1);count+=1
  assert count==1,(index,part,count)
  files[part]=serial(slide);changed.add(part)
 files['ppt/presentation.xml']=serial(presentation)
 files['ppt/_rels/presentation.xml.rels']=serial(rels)
 files['[Content_Types].xml']=serial(types)
 changed.update({'ppt/presentation.xml','ppt/_rels/presentation.xml.rels','[Content_Types].xml'})
 assert all(files[n]==original.read(n) for n in original.namelist() if n not in changed)
 for index in [4,5]:
  part=targets[ids[index].get('{'+O+'}id')]
  assert files[part]==original.read(part)
 with ZipFile(BUILD/'candidate_slide6.pptx','w',ZIP_DEFLATED) as dest:
  for name,data in files.items():dest.writestr(name,data)
 print('Inserted slide 7. Original slides 5 and 6 preserved. Following footers incremented.')
