from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as E
import posixpath
import re

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(__file__).resolve().parent
SOURCE = ROOT / 'presentation/NIR2_slide01_v2.pptx'
DEST = BUILD / 'candidate.pptx'
R = 'http://schemas.openxmlformats.org/package/2006/relationships'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
O = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'
E.register_namespace('p', P)
E.register_namespace('a', A)
E.register_namespace('r', O)

def relpath(part):
    folder, name = posixpath.split(part)
    return posixpath.join(folder, '_rels', name + '.rels')

def serial(root):
    return E.tostring(root, encoding='utf-8', xml_declaration=True)

with ZipFile(SOURCE) as original, ZipFile(BUILD / 'slide5.pptx') as generated:
    files = {n: original.read(n) for n in original.namelist()}
    types = E.fromstring(files['[Content_Types].xml'])
    gen_types = E.fromstring(generated.read('[Content_Types].xml'))
    overrides = {e.get('PartName').lstrip('/'): e.get('ContentType') for e in gen_types if e.tag.endswith('Override')}
    defaults = {e.get('Extension'): e.get('ContentType') for e in gen_types if e.tag.endswith('Default')}
    mapped = {'ppt/slides/slide1.xml': 'ppt/slides/slide5.xml', 'ppt/slides/slide2.xml': 'ppt/slides/slide11.xml'}
    additions = set()

    def copy_part(part):
        if part in mapped:
            return mapped[part]
        dest = 'ppt/slide5_result/' + part
        mapped[part] = dest
        data = generated.read(part)
        relationships = relpath(part)
        if relationships in generated.namelist():
            rels = E.fromstring(generated.read(relationships))
            for rel in rels:
                if rel.get('TargetMode') == 'External':
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(part), rel.get('Target'))).lstrip('/')
                target_dest = copy_part(target)
                rel.set('Target', posixpath.relpath(target_dest, posixpath.dirname(dest)))
            files[relpath(dest)] = serial(rels)
        files[dest] = data
        additions.add(dest)
        if part in overrides:
            E.SubElement(types, '{' + C + '}Override', PartName='/' + dest, ContentType=overrides[part])
        return dest

    def graft_slide(number, destination):
        source_slide = E.fromstring(original.read('ppt/slides/slide5.xml'))
        target_slide = E.fromstring(generated.read(f'ppt/slides/slide{number}.xml'))
        old_tree = source_slide.find('{' + P + '}cSld/{' + P + '}spTree')
        parent = source_slide.find('{' + P + '}cSld')
        parent.remove(old_tree)
        parent.insert(0, target_slide.find('{' + P + '}cSld/{' + P + '}spTree'))
        old_rels = E.fromstring(original.read('ppt/slides/_rels/slide5.xml.rels'))
        new_rels = E.Element('{' + R + '}Relationships')
        for rel in old_rels:
            if rel.get('Type').endswith('/slideLayout'):
                rel.set('Id', 'rIdOriginalLayout')
                new_rels.append(rel)
        rel_ids = {}
        for idx, rel in enumerate(E.fromstring(generated.read(f'ppt/slides/_rels/slide{number}.xml.rels')), 1):
            if rel.get('Type').endswith('/slideLayout'):
                continue
            old_id = rel.get('Id')
            new_id = 'rIdResult' + str(idx)
            rel_ids[old_id] = new_id
            rel.set('Id', new_id)
            if rel.get('TargetMode') != 'External':
                target = posixpath.normpath(posixpath.join('ppt/slides', rel.get('Target'))).lstrip('/')
                rel.set('Target', posixpath.relpath(copy_part(target), 'ppt/slides'))
            new_rels.append(rel)
        for element in source_slide.iter():
            for key, value in list(element.attrib.items()):
                if key.startswith('{' + O + '}') and value in rel_ids:
                    element.set(key, rel_ids[value])
        files[destination] = serial(source_slide)
        files[relpath(destination)] = serial(new_rels)
    graft_slide(1, 'ppt/slides/slide5.xml')
    graft_slide(2, 'ppt/slides/slide11.xml')
    E.SubElement(types, '{' + C + '}Override', PartName='/ppt/slides/slide11.xml', ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
    presentation = E.fromstring(files['ppt/presentation.xml'])
    slide_ids = presentation.find('{' + P + '}sldIdLst')
    new_id = str(max(int(e.get('id')) for e in slide_ids) + 1)
    slide_ids.insert(5, E.Element('{' + P + '}sldId', {'id': new_id, '{' + O + '}id': 'rIdChoiceSlide'}))
    files['ppt/presentation.xml'] = serial(presentation)
    presentation_rels = E.fromstring(files['ppt/_rels/presentation.xml.rels'])
    assert not any(e.get('Id') == 'rIdChoiceSlide' for e in presentation_rels)
    E.SubElement(presentation_rels, '{' + R + '}Relationship', Id='rIdChoiceSlide', Type=O+'/slide', Target='slides/slide11.xml')
    files['ppt/_rels/presentation.xml.rels'] = serial(presentation_rels)
    for i in range(6, 11):
        part = f'ppt/slides/slide{i}.xml'
        data = files[part].decode('utf-8')
        pattern = r'(<a:fld\b[^>]*\btype="slidenum"[^>]*>.*?<a:t>)'+str(i)+r'(</a:t>)'
        changed, count = re.subn(pattern, lambda m: m.group(1)+str(i+1)+m.group(2), data, flags=re.S)
        assert count == 1, (i, 'slide number missing')
        files[part] = changed.encode('utf-8')
    files['docProps/app.xml'] = re.sub(rb'<Slides>10</Slides>', b'<Slides>11</Slides>', files['docProps/app.xml'])
    present_defaults = {e.get('Extension') for e in types if e.tag.endswith('Default')}
    for ext, mime in defaults.items():
        if ext not in present_defaults:
            E.SubElement(types, '{' + C + '}Default', Extension=ext, ContentType=mime)
    E.register_namespace('', C)
    files['[Content_Types].xml'] = serial(types)
    with ZipFile(DEST, 'w', ZIP_DEFLATED) as final:
        for name, content in files.items():
            final.writestr(name, content)
    allowed = {'ppt/slides/slide5.xml', 'ppt/slides/_rels/slide5.xml.rels', '[Content_Types].xml', 'ppt/presentation.xml', 'ppt/_rels/presentation.xml.rels', 'docProps/app.xml'} | {f'ppt/slides/slide{i}.xml' for i in range(6,11)}
    unchanged = [n for n in original.namelist() if n not in allowed]
    assert all(files[n] == original.read(n) for n in unchanged)
    assert all(files[f'ppt/slides/slide{i}.xml'] == original.read(f'ppt/slides/slide{i}.xml') for i in range(1,5))
    assert len(slide_ids) == 11
    print(f'Preserved {len(unchanged)} original parts; replaced slide 5, inserted slide 6, updated later footer numbers.')
