from datetime import timedelta
from uuid import uuid4
from sqlalchemy import select
from .models import Report, Alert, CaseFile, ReportImage, ReportClassification, now
from .image_classifier import aggregate
from fastapi import HTTPException

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
                message=f'Potential Downstream Contamination Alert | {report.contamination_type} | Observation status at generation: {report.status} | {asset["name"]} ({asset["id"]}) | Potential impact: {report.priority_level}. Dataset: {report.impact.get("dataset_mode","Legacy demo data")}. Alerts and assets are simulated. This is not confirmation of pollution.')
            db.add(alert)
            alerts.append(alert)
    report.timeline = [*report.timeline, event('Alerts generated', f'{len(alerts)} simulated recipients')]
    return alerts

def create_report(db, engine, payload):
    snap = engine.snap_engine.snap(payload.latitude, payload.longitude)
    impact = engine.analyze(payload.latitude, payload.longitude, repeats(db, snap['segment_id']))
    image_urls = list(dict.fromkeys(([payload.image_url] if payload.image_url else []) + payload.image_urls))
    if payload.ai_image_results and len(payload.ai_image_results) != len(image_urls):
        raise HTTPException(422, 'Image analysis must match all attached evidence photos.')
    fields=payload.model_dump(exclude={'image_urls','image_url','ai_image_results'})
    report = Report(id='REP-'+uuid4().hex[:10].upper(), **fields, image_url=image_urls[0] if image_urls else None, segment_id=snap['segment_id'], impact=impact,
                    priority_score=impact['priority']['score'], priority_level=impact['priority']['level'], status='UNVERIFIED',
                    timeline=[event('Report submitted'), event('Location snapped', snap['segment_id']), event('Impact analysis completed'), event('Potential impact priority generated', impact['priority']['level'])])
    db.add(report)
    suggestion = aggregate(payload.ai_image_results) if payload.ai_image_results else None
    report.classification = ReportClassification(
        ai_detected_category=suggestion['suggested_category'] if suggestion else None,
        ai_confidence=suggestion['confidence'] if suggestion else None,
        final_category=payload.contamination_type,
        category_source=('AI_CONFIRMED' if payload.contamination_type == suggestion['suggested_category'] else 'USER_CORRECTED') if suggestion else 'MANUAL',
        image_results=[result.model_dump() for result in payload.ai_image_results])
    db.flush()
    for position,url in enumerate(image_urls):
        report.images.append(ReportImage(id=uuid4().hex, image_url=url, position=position))
    if image_urls:
        report.timeline = [report.timeline[0], event('Evidence images uploaded', f'{len(image_urls)} image(s)'), *report.timeline[1:]]
    generate_alerts(db, report)
    db.commit()
    return report

def serialize(report):
    # Reporter contact is deliberately omitted from public API responses.
    result = {key: getattr(report, key) for key in ['id','contamination_type','description','observed_at','created_at','latitude','longitude','segment_id','status','image_url','impact','priority_score','priority_level','timeline']}
    result['case'] = {'id':report.case_file.case_id,'original_report_id':report.id,'review_started_at':report.case_file.review_started_at,'status':report.status} if report.case_file else None
    result['image_urls'] = [image.image_url for image in report.images] or ([report.image_url] if report.image_url else [])
    result['is_demo'] = report.description.upper().startswith(('DEMO', 'SAMPLE'))
    result['location_name'] = report.impact['snapped_location'].get('name','Periyar River (legacy dataset)')
    classification = report.classification
    result.update(ai_detected_category=classification.ai_detected_category if classification else None,
        ai_confidence=classification.ai_confidence if classification else None,
        final_category=report.contamination_type,
        category_source=classification.category_source if classification else 'MANUAL')
    return result

def change_status(db, report, status, note='', actor='admin'):
    allowed = {'UNVERIFIED':['UNDER REVIEW','VERIFIED','REJECTED'], 'UNDER REVIEW':['VERIFIED','REJECTED'], 'VERIFIED':['RESOLVED'], 'REJECTED':[], 'RESOLVED':[]}
    if status not in allowed[report.status]:
        raise ValueError(f'Cannot change {report.status} to {status}')
    report.status = status
    report.timeline = [*report.timeline, event('Status changed to '+status, f'{actor}: {note}'.rstrip(': '))]
    if status in ['UNDER REVIEW','VERIFIED'] and not report.case_file:
        case = CaseFile(report=report, review_started_at=now())
        db.add(case)
        db.flush()
        report.timeline = [*report.timeline, event('Case file created', case.case_id)]
    db.commit()
    return report
