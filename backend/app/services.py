from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from .models import Report, Alert, now

def event(label, note=''):
    return {'label': label, 'note': note, 'timestamp': now().isoformat()}

def repeats(db, segment):
    return len(db.scalars(select(Report).where(Report.segment_id == segment, Report.created_at >= now()-timedelta(days=30), Report.status != 'REJECTED')).all())

def generate_alerts(db, report):
    existing = db.scalars(select(Alert).where(Alert.report_id == report.id)).all()
    if existing:
        return existing
    alerts = []
    for kind, assets in report.impact['affected'].items():
        for asset in assets:
            alert = Alert(id='ALT-'+uuid4().hex[:12], report_id=report.id, target=asset['name'], target_type=kind,
                message=f'Potential Downstream Contamination Alert | {report.contamination_type} | Observation status at generation: {report.status} | {asset["name"]} ({asset["id"]}) | Potential impact: {report.priority_level}. Potential impact generated from river network analysis using DEMO data. This is not confirmation of pollution.')
            db.add(alert)
            alerts.append(alert)
    report.timeline = [*report.timeline, event('Alerts generated', f'{len(alerts)} simulated recipients')]
    return alerts

def create_report(db, engine, payload):
    snap = engine.snap_engine.snap(payload.latitude, payload.longitude)
    impact = engine.analyze(payload.latitude, payload.longitude, repeats(db, snap['segment_id']))
    report = Report(id='REP-'+uuid4().hex[:10].upper(), **payload.model_dump(), segment_id=snap['segment_id'], impact=impact,
                    priority_score=impact['priority']['score'], priority_level=impact['priority']['level'], status='UNVERIFIED',
                    timeline=[event('Report submitted'), event('Location snapped', snap['segment_id']), event('Impact analysis completed')])
    db.add(report)
    db.flush()
    generate_alerts(db, report)
    db.commit()
    return report

def serialize(report):
    # Reporter contact is deliberately omitted from public API responses.
    return {key: getattr(report, key) for key in ['id','contamination_type','description','observed_at','created_at','latitude','longitude','segment_id','status','image_url','impact','priority_score','priority_level','timeline']}
