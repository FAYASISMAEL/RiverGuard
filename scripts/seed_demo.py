"""Run from repository root: python -m scripts.seed_demo. Safe to repeat."""
from datetime import timedelta
from sqlalchemy import select
from backend.app.database import Base, engine, SessionLocal
from backend.app.models import Report, now
from backend.app.schemas import ReportInput
from backend.app.services import create_report
from backend.app.river_impact_engine import RiverImpactEngine
from backend.app.config import DATA_DIR, PROXIMITY_M, CORRIDOR_M

def main():
    Base.metadata.create_all(engine)
    gis=RiverImpactEngine(DATA_DIR, PROXIMITY_M, CORRIDOR_M)
    point=gis.metadata.get('demo_location', {'latitude':10.1253,'longitude':76.418})
    examples=[(category,point['latitude'],point['longitude']) for category in ['Industrial Discharge','Foam','Plastic / Solid Waste']]
    with SessionLocal() as db:
        for index,(category,latitude,longitude) in enumerate(examples):
            description=f'DEMO SEED {index+1}: illustrative {category.lower()} observation awaiting field verification.'
            if db.scalar(select(Report).where(Report.description==description)):
                continue
            report=create_report(db,gis,ReportInput(contamination_type=category,latitude=latitude,longitude=longitude,description=description,observed_at=now()-timedelta(hours=index+1)))
            print(report.id,report.contamination_type,report.status,report.priority_level)
    engine.dispose()

if __name__=='__main__':
    main()
