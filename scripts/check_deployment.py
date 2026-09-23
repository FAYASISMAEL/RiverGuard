"""Read-only checks for deployment file inclusion and Linux import spelling."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def exact_path(path):
    relative = path.relative_to(ROOT)
    parent = ROOT
    for part in relative.parts:
        if part not in {p.name for p in parent.iterdir()}:
            return False
        parent /= part
    return True

def python_module(path):
    return any(p.exists() and exact_path(p) for p in (path.with_suffix('.py'), path/'__init__.py'))

def main():
    for source in (ROOT/'backend').rglob('*.py'):
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8-sig'))):
            if isinstance(node, ast.ImportFrom) and node.level:
                parent = source.parent
                for _ in range(node.level-1):
                    parent = parent.parent
                if node.module:
                    assert python_module(parent.joinpath(*node.module.split('.'))), (source, node.module)
                else:
                    for alias in node.names:
                        assert python_module(parent/alias.name), (source, alias.name)
    for source in (ROOT/'frontend/src').rglob('*'):
        if source.suffix not in ('.js','.jsx'):
            continue
        for path in re.findall(r'''(?:from\s*|import\s*)["'](\.[^"']+)["']''', source.read_text(encoding='utf-8')):
            target = (source.parent/path).resolve()
            candidates = [target] if target.suffix else [target.with_suffix('.js'), target.with_suffix('.jsx'), target/'index.js']
            assert any(p.is_file() and exact_path(p) for p in candidates), (source, path)
    data = ['river_network','settlements','water_intakes','monitoring_points','local_bodies']
    for name in data:
        path = ROOT/'data'/f'{name}.geojson'
        assert exact_path(path)
        assert json.loads(path.read_text(encoding='utf-8'))['type'] == 'FeatureCollection'
    config = json.loads((ROOT/'vercel.json').read_text())
    assert config['functions']['api/server.py']['includeFiles'] == 'data/{*.geojson,metadata.json}'
    assert config['rewrites'][0]['source'] == '/api/:path*'
    assert config['rewrites'][-1]['destination'] == '/index.html'
    assert 'data\n' not in (ROOT/'.vercelignore').read_text()
    bundle_size = sum(p.stat().st_size for p in (ROOT/'data').glob('*.geojson'))
    print(f'Import capitalization, five packaged GeoJSON layers, and routing checks passed. Active GeoJSON bytes: {bundle_size:,}')
    print('This is a static check, not a Linux runtime or authenticated Vercel build.')

if __name__ == '__main__':
    main()
