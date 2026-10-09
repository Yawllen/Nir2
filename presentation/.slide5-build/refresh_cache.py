from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as E
from decimal import Decimal
import sys

BUILD = Path(__file__).resolve().parent
sys.path.insert(0, r'C:\Users\Yawllen\.codex\plugins\cache\openai-primary-runtime\presentations\26.1007.11041\skills\presentations\container_tools')
import native_quantitative_chart_gate as gate

source = BUILD / 'candidate_slide6.pptx'
ns = gate.NS
changes = {}
with ZipFile(source) as package:
    for name in package.namelist():
        if not name.endswith('.xml') or '/charts/' not in name:
            continue
        chart = E.fromstring(package.read(name))
        external = chart.find('c:externalData', ns)
        if external is None:
            continue
        relation = gate._relationships(package, name)[external.get('{' + ns['r'] + '}id')]
        workbook = gate._workbook_cells(package, relation['target'])
        updated = 0
        for reference in chart.findall('.//c:numRef', ns):
            formula = reference.find('c:f', ns).text
            cells = gate._referenced_cells(workbook, formula, label=name)
            points = reference.findall('c:numCache/c:pt', ns)
            assert len(points) == len(cells)
            for point in points:
                cell = cells[int(point.get('idx'))]
                value = point.find('c:v', ns)
                assert cell.kind == 'number'
                difference = abs(Decimal(value.text) - cell.value)
                if difference:
                    assert difference < Decimal('1e-12'), (name, value.text, cell.value)
                    print(name, point.get('idx'), value.text, '->', str(cell.value))
                    value.text = str(cell.value)
                    updated += 1
        if updated:
            changes[name] = E.tostring(chart, encoding='utf-8', xml_declaration=True)
    with ZipFile(BUILD / 'candidate_slide6_synced.pptx', 'w', ZIP_DEFLATED) as output:
        for name in package.namelist():
            output.writestr(name, changes.get(name, package.read(name)))
print('Refreshed chart cache parts:', len(changes))
