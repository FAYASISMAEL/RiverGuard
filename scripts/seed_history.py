"""Add clearly labelled sample histories without deleting existing observations."""
from datetime import timedelta, datetime
from sqlalchemy import select
from backend.app.database import Base, engine, SessionLocal
from backend.app.models import Report, now
from backend.app.schemas import ReportInput
from backend.app.services import create_report, change_status
from backend.app.river_impact_engine import RiverImpactEngine
from backend.app.config import DATA_DIR, PROXIMITY_M, CORRIDOR_M

def main():
    Base.metadata.create_all(engine)
    gis=RiverImpactEngine(DATA_DIR,PROXIMITY_M,CORRIDOR_M)
    point=gis.metadata['demo_location']
    samples=[('Dead Fish',['UNDER REVIEW']),('Foam',['UNDER REVIEW','VERIFIED']),('Plastic / Solid Waste',['UNDER REVIEW','VERIFIED','RESOLVED']),('Oil / Fuel',[])]
    with SessionLocal() as db:
        for i,(category,statuses) in enumerate(samples):
            description=f'SAMPLE HISTORY {i+1}: synthetic {category.lower()} observation for the prototype. Not an actual pollution incident.'
            if db.scalar(select(Report).where(Report.description==description)):continue
            r=create_report(db,gis,ReportInput(**point,contamination_type=category,description=description,observed_at=now()-timedelta(days=i+1,hours=1)))
            for status in statuses:change_status(db,r,status,'Demonstration review only','sample-admin')
            # Deliberately synthetic past timeline, labelled in description/UI.
            submitted=now()-timedelta(days=i+1)
            r.created_at=submitted
            r.timeline=[{**e,'timestamp':(submitted+timedelta(minutes=j*2)).isoformat()} for j,e in enumerate(r.timeline)]
            if r.case_file:r.case_file.review_started_at=submitted+timedelta(minutes=10)
            from backend.app.models import Alert
            for alert in db.scalars(select(Alert).where(Alert.report_id==r.id)).all():alert.created_at=submitted+timedelta(minutes=8)
            db.commit()
            print(r.id,category,r.status,r.case_file.case_id if r.case_file else 'No case yet')
    engine.dispose()

if __name__=='__main__':main()
