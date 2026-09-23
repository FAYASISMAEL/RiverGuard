"""Validate display CRS and geometry using GeoPandas without changing coordinates."""
from pathlib import Path
import geopandas as gpd
from backend.app.river_impact_engine import RiverImpactEngine

def main():
    directory=Path(__file__).resolve().parents[1]/'data'
    for path in directory.glob('*.geojson'):
        frame=gpd.read_file(path)
        if frame.crs is None or frame.crs.to_epsg()!=4326:
            raise ValueError(f'{path.name}: expected EPSG:4326, got {frame.crs}')
        if not frame.geometry.is_valid.all() or frame.geometry.is_empty.any():
            raise ValueError(f'{path.name}: invalid or empty geometry')
        print(f'{path.name}: {len(frame)} valid EPSG:4326 features')
    gis=RiverImpactEngine(directory)
    print(f'Directed graph: {len(gis.flow_engine.graph)} segments, {gis.flow_engine.graph.number_of_edges()} downstream links')

if __name__=='__main__':main()
