from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from .auth import require_admin
from .database import get_db
from .models import Report, CaseFile, AdminAction, Alert
from pydantic import BaseModel
from typing import Literal
from uuid import uuid4
from .services import serialize, event

router = APIRouter(prefix='/api/admin', tags=['Admin portal'], dependencies=[Depends(require_admin)])

@router.get('/reports')
def reports(db=Depends(get_db)):
    return [serialize(r) for r in db.scalars(select(Report).order_by(Report.created_at.desc())).all()]

@router.get('/dashboard')
def dashboard(db=Depends(get_db)):
    rows = db.scalars(select(Report).order_by(Report.created_at.desc())).all()
    return {'total':len(rows), 'statuses':{s:sum(r.status==s for r in rows) for s in ['UNVERIFIED','UNDER REVIEW','VERIFIED','REJECTED','RESOLVED']}, 'high':sum(r.priority_level=='HIGH' for r in rows), 'critical':sum(r.priority_level=='CRITICAL' for r in rows), 'recent':[serialize(r) for r in rows[:8]]}

@router.get('/cases')
def cases(db=Depends(get_db)):
    return [serialize(c.report) for c in db.scalars(select(CaseFile).order_by(CaseFile.review_started_at.desc())).all()]

@router.post('/reports/{report_id}/opened')
def opened(report_id: str, admin=Depends(require_admin), db=Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, 'Report not found')
    report.timeline = [*report.timeline, event('Admin opened report', admin.username)]
    db.commit()
    return serialize(report)

class ActionInput(BaseModel):
    action: Literal['Generate Authority Alert','Notify Water Intake','Request Field Inspection','Notify Monitoring Point','Generate Community Advisory','Mark Under Control']

@router.get('/reports/{report_id}/actions')
def actions(report_id: str, db=Depends(get_db)):
    if not db.get(Report,report_id):raise HTTPException(404,'Report not found')
    return db.scalars(select(AdminAction).where(AdminAction.report_id==report_id).order_by(AdminAction.created_at)).all()

@router.post('/reports/{report_id}/actions', status_code=201)
def take_action(report_id: str, payload: ActionInput, admin=Depends(require_admin), db=Depends(get_db)):
    report=db.get(Report,report_id)
    if not report:raise HTTPException(404,'Report not found')
    if report.status!='VERIFIED' or report.priority_level not in ['HIGH','CRITICAL']:
        raise HTTPException(409,'Emergency actions require a verified HIGH or CRITICAL case.')
    kinds={'Generate Authority Alert':'local_bodies','Notify Water Intake':'water_intakes','Notify Monitoring Point':'monitoring_points','Generate Community Advisory':'settlements'}
    kind=kinds.get(payload.action)
    targets=report.impact['affected'].get(kind,[]) if kind else []
    if kind and not targets:raise HTTPException(409,'No mapped recipients of this type were found downstream.')
    recipients=[t['name'] for t in targets] if kind else ['Field operations team' if payload.action=='Request Field Inspection' else 'Case operations log']
    action=AdminAction(id='ACT-'+uuid4().hex[:12],report_id=report_id,action=payload.action,actor=admin.username,details={'simulated':True,'recipients':recipients})
    db.add(action)
    for name in recipients:
        if payload.action!='Mark Under Control':
            db.add(Alert(id='ALT-'+uuid4().hex[:12],report_id=report_id,target=name,target_type=kind or 'field_inspection',state='Sent - Simulated',message=f'SIMULATED {payload.action} | {report.id} | VERIFIED observation | Potential impact {report.priority_level} | {name}. No external message has been sent.'))
    report.timeline=[*report.timeline,event(payload.action+' — Simulated',f'{admin.username}: '+', '.join(recipients))]
    db.commit()
    return action
