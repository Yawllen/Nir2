import importlib.util
import os
import shutil
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
SKILL = Path(r'C:\Users\Yawllen\.codex\plugins\cache\openai-primary-runtime\presentations\26.1007.11041\skills\presentations\container_tools')
sys.path.insert(0, str(SKILL))
spec = importlib.util.spec_from_file_location('chart_snapshot', SKILL / 'materialize_literal_chart_workbooks.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def copy_new(source, destination):
    # На Windows публикация копированием не требует разрешения на hard link.
    with open(source, 'rb') as src, open(destination, 'xb') as dest:
        shutil.copyfileobj(src, dest)

os.link = copy_new
result = module.materialize_literal_chart_workbooks(
    BUILD / 'candidate_slide6_synced.pptx', BUILD / 'portable_limits_added.pptx',
    receipt=BUILD / 'chart-snapshot-limits-added.json', workspace=BUILD.parents[1])
print('Chart workbook validation:', result['portable_chart_validation_passed'])
