from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as E
import posixpath

ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(__file__).resolve().parent
SOURCE = ROOT / 'presentation/NIR2_slide01_v2.pptx'
DEST = BUILD / 'candidate_slide6.pptx'
R = 'http://schemas.openxmlformats.org/package/2006/relationships'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
O = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C = 'http://schemas.openxmlformats.org/package/2006/content-types'
for prefix, uri in [('p', P), ('a', A), ('r', O)]:
    E.register_namespace(prefix, uri)

def relpath(part):
    folder, name = posixpath.split(part)
    return posixpath.join(folder, '_rels', name + '.rels')

def serial(root):
    return E.tostring(root, encoding='utf-8', xml_declaration=True)

with ZipFile(SOURCE) as original, ZipFile(BUILD / 'slide5.pptx') as generated:
    files = {n: original.read(n) for n in original.namelist()}
    presentation = E.fromstring(files['ppt/presentation.xml'])
    ids = presentation.find('{' + P + '}sldIdLst')
    assert len(ids) == 11
    root_rels = {r.get('Id'): posixpath.normpath(posixpath.join('ppt', r.get('Target'))).lstrip('/') for r in E.fromstring(files['ppt/_rels/presentation.xml.rels'])}
    target_part = root_rels[ids[5].get('{' + O + '}id')]
    fifth_part = root_rels[ids[4].get('{' + O + '}id')]
    types = E.fromstring(files['[Content_Types].xml'])
    gen_types = E.fromstring(generated.read('[Content_Types].xml'))
    overrides = {e.get('PartName').lstrip('/'): e.get('ContentType') for e in gen_types if e.tag.endswith('Override')}
    defaults = {e.get('Extension'): e.get('ContentType') for e in gen_types if e.tag.endswith('Default')}
    mapped = {'ppt/slides/slide1.xml': target_part}

    def copy_part(part):
        if part in mapped:
            return mapped[part]
        dest = 'ppt/printer_validation6/' + part
        assert dest not in files
        mapped[part] = dest
        files[dest] = generated.read(part)
        relationships = relpath(part)
        if relationships in generated.namelist():
            rels = E.fromstring(generated.read(relationships))
            for rel in rels:
                if rel.get('TargetMode') == 'External':
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(part), rel.get('Target'))).lstrip('/')
                rel.set('Target', posixpath.relpath(copy_part(target), posixpath.dirname(dest)))
            files[relpath(dest)] = serial(rels)
        if part in overrides:
            E.SubElement(types, '{' + C + '}Override', PartName='/' + dest, ContentType=overrides[part])
        return dest

    target_slide = E.fromstring(files[target_part])
    new_slide = E.fromstring(generated.read('ppt/slides/slide1.xml'))
    parent = target_slide.find('{' + P + '}cSld')
    old_tree = parent.find('{' + P + '}spTree')
    parent.remove(old_tree)
    parent.insert(0, new_slide.find('{' + P + '}cSld/{' + P + '}spTree'))
    new_rels = E.Element('{' + R + '}Relationships')
    for rel in E.fromstring(files[relpath(target_part)]):
        if rel.get('Type').endswith('/slideLayout'):
            rel.set('Id', 'rIdOriginalLayout')
            new_rels.append(rel)
    id_map = {}
    for i, rel in enumerate(E.fromstring(generated.read('ppt/slides/_rels/slide1.xml.rels')), 1):
        if rel.get('Type').endswith('/slideLayout'):
            continue
        id_map[rel.get('Id')] = new_id = 'rIdValidation' + str(i)
        rel.set('Id', new_id)
        if rel.get('TargetMode') != 'External':
            target = posixpath.normpath(posixpath.join('ppt/slides', rel.get('Target'))).lstrip('/')
            rel.set('Target', posixpath.relpath(copy_part(target), posixpath.dirname(target_part)))
        new_rels.append(rel)
    for element in target_slide.iter():
        for key, value in list(element.attrib.items()):
            if key.startswith('{' + O + '}') and value in id_map:
                element.set(key, id_map[value])
    files[target_part] = serial(target_slide)
    files[relpath(target_part)] = serial(new_rels)
    present_defaults = {e.get('Extension') for e in types if e.tag.endswith('Default')}
    for extension, mime in defaults.items():
        if extension not in present_defaults:
            E.SubElement(types, '{' + C + '}Default', Extension=extension, ContentType=mime)
    E.register_namespace('', C)
    files['[Content_Types].xml'] = serial(types)
    allowed = {target_part, relpath(target_part), '[Content_Types].xml'}
    assert all(files[n] == original.read(n) for n in original.namelist() if n not in allowed)
    assert files[fifth_part] == original.read(fifth_part)
    text = ' '.join(t.text or '' for t in target_slide.findall('.//{' + A + '}t'))
    assert '54,55' in text and 'валидации' in text and 'Обнаружены 6 из 11; пропущены 5' in text
    assert all(v not in text for v in ('99,89', '99,61', '3 337'))
    with ZipFile(DEST, 'w', ZIP_DEFLATED) as final:
        for name, content in files.items():
            final.writestr(name, content)
    print('Replaced slide 6 only; slide 5 and every unrelated original part preserved.')
