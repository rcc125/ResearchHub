"""ResearchHub phase 1 API. Educational local prototype; never use real participant data in demo mode."""
import os
import io
from datetime import datetime, timedelta, timezone, date, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import jwt
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, String, ForeignKey, DateTime, Date, Time, Numeric, JSON, UniqueConstraint, select, func, and_, text, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

class Settings(BaseSettings):
    database_url: str = 'mysql+pymysql://researchhub:local_dev_password@127.0.0.1:3306/researchhub?charset=utf8mb4'
    jwt_secret: str = ''
    wechat_appid: str = ''
    wechat_appsecret: str = ''
    demo_mode: bool = False
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / '.env', extra='ignore')

settings = Settings()
if len(settings.jwt_secret) < 32:
    raise RuntimeError('JWT_SECRET must have at least 32 characters; set it in backend/.env')
if settings.demo_mode and (os.getenv('RENDER') or os.getenv('FLY_APP_NAME')):
    raise RuntimeError('Do not enable DEMO_MODE in deployed environments')
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Subject(Base):
    __tablename__ = 'subjects'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True)
    subject_code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gender: Mapped[str] = mapped_column(String(24))
    birth_date: Mapped[date] = mapped_column(Date)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500))
    form_schema: Mapped[list] = mapped_column(JSON, nullable=False)
    leader_name: Mapped[str] = mapped_column(String(80), nullable=False, default='待设置')
    workdays: Mapped[list] = mapped_column(JSON, nullable=False, default=lambda: [1, 2, 3, 4, 5])
    workday_start: Mapped[time] = mapped_column(Time, nullable=False, default=time(9, 0))
    workday_end: Mapped[time] = mapped_column(Time, nullable=False, default=time(17, 0))

class Enrollment(Base):
    __tablename__ = 'enrollments'
    __table_args__ = (UniqueConstraint('project_id', 'subject_id', name='uq_project_subject'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey('subjects.id'))
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FormResponse(Base):
    __tablename__ = 'form_responses'
    __table_args__ = (UniqueConstraint('enrollment_id', name='uq_form_enrollment'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey('enrollments.id'))
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectMember(Base):
    __tablename__ = 'project_members'
    __table_args__ = (UniqueConstraint('project_id', 'user_id', name='uq_member_project_user'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    member_role: Mapped[str] = mapped_column(String(24), nullable=False, default='researcher')

class Collection(Base):
    __tablename__ = 'collections'
    __table_args__ = (UniqueConstraint('enrollment_id', 'attempt_no', name='uq_collection_attempt'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey('enrollments.id'), nullable=False)
    attempt_no: Mapped[int] = mapped_column(nullable=False)
    collection_code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    data_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Appointment(Base):
    __tablename__ = 'appointments'
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey('enrollments.id'), nullable=False)
    previous_collection_id: Mapped[int | None] = mapped_column(ForeignKey('collections.id'), nullable=True)
    appointment_type: Mapped[str] = mapped_column(String(20), nullable=False, default='reschedule')
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')
    note: Mapped[str] = mapped_column(String(300), nullable=False, default='')
    admin_note: Mapped[str] = mapped_column(String(300), nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    gender: str
    birth_date: date
    height_cm: Decimal = Field(gt=50, le=250, max_digits=5, decimal_places=1)
    weight_kg: Decimal = Field(gt=10, le=350, max_digits=5, decimal_places=1)

    @field_validator('gender')
    @classmethod
    def gender_allowed(cls, v: str) -> str:
        if v not in ('男', '女', '不愿透露'):
            raise ValueError('性别选项无效')
        return v

class WechatIn(BaseModel):
    code: str = Field(min_length=1, max_length=512)

class FormIn(BaseModel):
    answers: dict[str, Any]

app = FastAPI(title='ResearchHub API', version='0.3.0')
security = HTTPBearer(auto_error=False)

def db_session():
    with SessionLocal() as db:
        yield db

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(db_session)) -> User:
    if not credentials:
        raise HTTPException(401, '请先登录')
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'])
        user_id = int(payload['sub'])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, '登录已失效')
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, '用户不存在')
    return user

def token_for(user_id: int):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(user_id), 'iat': now, 'exp': now + timedelta(hours=12)}, settings.jwt_secret, algorithm='HS256')

def get_or_create_user(db: Session, openid: str):
    user = db.scalar(select(User).where(User.openid == openid))
    if not user:
        user = User(openid=openid)
        db.add(user)
        db.commit()
        db.refresh(user)
    return {'access_token': token_for(user.id), 'token_type': 'bearer'}

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/api/v1/auth/demo')
def demo_login(request: Request, db: Session = Depends(db_session)):
    # Strictly local, for UI testing with synthetic data only.
    if not settings.demo_mode or request.client is None or request.client.host not in ('127.0.0.1', '::1'):
        raise HTTPException(404, '不存在此接口')
    return get_or_create_user(db, 'DEMO_LOCAL_USER')

@app.post('/api/v1/auth/wechat')
async def wechat_login(payload: WechatIn, db: Session = Depends(db_session)):
    if not settings.wechat_appid or not settings.wechat_appsecret:
        raise HTTPException(503, '尚未配置微信登录凭据')
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get('https://api.weixin.qq.com/sns/jscode2session', params={
                'appid': settings.wechat_appid, 'secret': settings.wechat_appsecret,
                'js_code': payload.code, 'grant_type': 'authorization_code'})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, '微信登录服务暂不可用')
    if data.get('errcode') not in (None, 0) or not data.get('openid'):
        raise HTTPException(401, '微信登录失败或凭据已过期')
    return get_or_create_user(db, data['openid'])

def format_profile(subject: Subject):
    age = date.today().year - subject.birth_date.year - ((date.today().month, date.today().day) < (subject.birth_date.month, subject.birth_date.day))
    return {'subject_code': subject.subject_code, 'name': subject.name or '', 'gender': subject.gender,
            'birth_date': subject.birth_date.isoformat(), 'age': age,
            'height_cm': float(subject.height_cm), 'weight_kg': float(subject.weight_kg),
            'bmi': round(float(subject.weight_kg) / (float(subject.height_cm) / 100)**2, 1)}

@app.get('/api/v1/subjects/me')
def get_profile(user: User = Depends(current_user), db: Session = Depends(db_session)):
    subject = db.scalar(select(Subject).where(Subject.user_id == user.id))
    return {'profile': format_profile(subject) if subject else None}

@app.put('/api/v1/subjects/me')
def put_profile(payload: ProfileIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    if payload.birth_date > date.today() or payload.birth_date.year < 1900:
        raise HTTPException(422, '出生日期不合理')
    subject = db.scalar(select(Subject).where(Subject.user_id == user.id))
    if not subject:
        subject = Subject(user_id=user.id, subject_code=f'SUB{user.id:08d}', **payload.model_dump())
        db.add(subject)
    else:
        for key, value in payload.model_dump().items():
            setattr(subject, key, value)
    db.commit()
    db.refresh(subject)
    return {'profile': format_profile(subject)}

@app.get('/api/v1/projects')
def list_projects(user: User = Depends(current_user), db: Session = Depends(db_session)):
    return [{'id': p.id, 'project_code': p.project_code, 'title': p.title,
             'leader_name': p.leader_name, 'workdays': p.workdays, 'workdays_text': '、'.join({1:'周一',2:'周二',3:'周三',4:'周四',5:'周五',6:'周六',7:'周日'}[d] for d in (p.workdays or [1,2,3,4,5])),
             'workday_start': p.workday_start.strftime('%H:%M'), 'workday_end': p.workday_end.strftime('%H:%M'),
             'description': p.description, 'form_schema': p.form_schema}
            for p in db.scalars(select(Project).order_by(Project.id)).all()]

@app.get('/api/v1/enrollments/{enrollment_id}/context')
def enrollment_context(enrollment_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    subject = current_subject(db, user.id)
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment or enrollment.subject_id != subject.id:
        raise HTTPException(403, '无权查看该项目参与记录')
    project = db.get(Project, enrollment.project_id)
    return {'enrollment_id': enrollment.id, 'project_id': project.id, 'title': project.title,
            'leader_name': project.leader_name, 'workdays': project.workdays,
            'workdays_text': '、'.join({1:'周一',2:'周二',3:'周三',4:'周四',5:'周五',6:'周六',7:'周日'}[d] for d in (project.workdays or [1,2,3,4,5])),
            'workday_start': project.workday_start.strftime('%H:%M'), 'workday_end': project.workday_end.strftime('%H:%M')}

@app.get('/api/v1/projects/{project_id}/my-form')
def get_form(project_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, '项目不存在')
    subject = db.scalar(select(Subject).where(Subject.user_id == user.id))
    answers = {}
    if subject:
        enrollment = db.scalar(select(Enrollment).where(Enrollment.subject_id == subject.id, Enrollment.project_id == p.id))
        if enrollment:
            form = db.scalar(select(FormResponse).where(FormResponse.enrollment_id == enrollment.id))
            answers = dict(form.answers) if form else {}
            if p.project_code == 'PPG' and answers.get('site') in ('食指', '中指'):
                answers['site'] = '左手' + answers['site']
    return {'project': {'id': p.id, 'title': p.title, 'leader_name': p.leader_name, 'form_schema': p.form_schema}, 'enrollment_id': enrollment.id if subject and enrollment else None, 'answers': answers}

@app.put('/api/v1/projects/{project_id}/my-form')
def put_form(project_id: int, payload: FormIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, '项目不存在')
    subject = db.scalar(select(Subject).where(Subject.user_id == user.id))
    if not subject:
        raise HTTPException(400, '请先填写基础信息')
    schema = {field['key']: field for field in p.form_schema}
    if set(payload.answers) - set(schema):
        raise HTTPException(422, '包含未知问卷字段')
    for key, field in schema.items():
        value = payload.answers.get(key)
        if field.get('required') and (value is None or value == ''):
            raise HTTPException(422, f"请填写：{field['label']}")
        if value is not None and value != '':
            if field['type'] == 'select' and value not in field['options']:
                raise HTTPException(422, f"{field['label']}选项无效")
            if field['type'] == 'text' and (not isinstance(value, str) or len(value) > 200):
                raise HTTPException(422, f"{field['label']}长度或类型错误")
    enrollment = db.scalar(select(Enrollment).where(Enrollment.subject_id == subject.id, Enrollment.project_id == p.id))
    if not enrollment:
        enrollment = Enrollment(subject_id=subject.id, project_id=p.id)
        db.add(enrollment)
        db.flush()
    response = db.scalar(select(FormResponse).where(FormResponse.enrollment_id == enrollment.id))
    if response:
        response.answers = payload.answers
    else:
        db.add(FormResponse(enrollment_id=enrollment.id, answers=payload.answers))
    db.commit()
    return {'success': True, 'enrollment_id': enrollment.id}

# --- V0.2: project-scoped research staff, collection, rescheduling and exports ---
class CollectionIn(BaseModel):
    enrollment_id: int = Field(gt=0)
    status: str
    failure_reason: str = Field(default='', max_length=300)
    data_reference: str = Field(default='', max_length=120)
    collected_at: datetime

class AppointmentIn(BaseModel):
    enrollment_id: int = Field(gt=0)
    previous_collection_id: int | None = Field(default=None, gt=0)
    appointment_type: str = 'reschedule'
    requested_at: datetime
    note: str = Field(default='', max_length=300)

class AppointmentReview(BaseModel):
    status: str
    confirmed_at: datetime | None = None
    admin_note: str = Field(default='', max_length=300)

class ProjectSettingsIn(BaseModel):
    leader_name: str = Field(min_length=1, max_length=80)
    workdays: list[int] = Field(min_length=1, max_length=7)
    workday_start: str
    workday_end: str

    @field_validator('workdays')
    @classmethod
    def validate_workdays(cls, values):
        if any(v not in range(1, 8) for v in values) or len(set(values)) != len(values):
            raise ValueError('工作日请使用 1-7，周一为1，周日为7')
        return sorted(values)

    @field_validator('workday_start', 'workday_end')
    @classmethod
    def validate_clock(cls, value):
        try: time.fromisoformat(value)
        except ValueError: raise ValueError('时间格式应为 HH:MM')
        return value

def ensure_member(db: Session, user_id: int, project_id: int):
    membership = db.scalar(select(ProjectMember).where(
        ProjectMember.user_id == user_id, ProjectMember.project_id == project_id))
    if not membership:
        raise HTTPException(403, '无此项目的科研管理权限')
    return membership

def current_subject(db: Session, user_id: int):
    subject = db.scalar(select(Subject).where(Subject.user_id == user_id))
    if not subject:
        raise HTTPException(400, '请先填写基本信息')
    return subject

def collection_out(c: Collection):
    return {'id': c.id, 'enrollment_id': c.enrollment_id, 'collection_code': c.collection_code,
            'attempt_no': c.attempt_no, 'status': c.status, 'failure_reason': c.failure_reason or '',
            'data_reference': c.data_reference or '', 'collected_at': c.collected_at.isoformat()}

def appointment_out(a: Appointment):
    return {'id': a.id, 'enrollment_id': a.enrollment_id,
            'previous_collection_id': a.previous_collection_id, 'appointment_type': a.appointment_type,
            'requested_at': a.requested_at.isoformat(),
            'confirmed_at': a.confirmed_at.isoformat() if a.confirmed_at else None,
            'status': a.status, 'note': a.note, 'admin_note': a.admin_note}

@app.post('/api/v1/dev/enable-demo-admin')
def enable_demo_admin(request: Request, user: User = Depends(current_user), db: Session = Depends(db_session)):
    # Strictly local-only learning shortcut; NEVER use for real participants.
    if not settings.demo_mode or request.client is None or request.client.host not in ('127.0.0.1','::1') or user.openid != 'DEMO_LOCAL_USER':
        raise HTTPException(404, '不存在此接口')
    for project in db.scalars(select(Project)).all():
        if not db.scalar(select(ProjectMember).where(ProjectMember.project_id == project.id,
                                                     ProjectMember.user_id == user.id)):
            db.add(ProjectMember(project_id=project.id, user_id=user.id, member_role='admin'))
    db.commit()
    return {'success': True, 'demo_only': True}

@app.get('/api/v1/admin/projects')
def admin_projects(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.execute(select(Project.id, Project.title, Project.project_code).join(
        ProjectMember, ProjectMember.project_id == Project.id).where(ProjectMember.user_id == user.id)).all()
    return [{'id': id, 'title': title, 'project_code': code, 'leader_name': db.get(Project, id).leader_name,
             'workdays': db.get(Project, id).workdays, 'workdays_text': '、'.join({1:'周一',2:'周二',3:'周三',4:'周四',5:'周五',6:'周六',7:'周日'}[d] for d in (db.get(Project, id).workdays or [1,2,3,4,5])), 'workday_start': db.get(Project, id).workday_start.strftime('%H:%M'),
             'workday_end': db.get(Project, id).workday_end.strftime('%H:%M')} for id, title, code in rows]

@app.patch('/api/v1/admin/projects/{project_id}/settings')
def update_project_settings(project_id: int, payload: ProjectSettingsIn,
                            user: User = Depends(current_user), db: Session = Depends(db_session)):
    ensure_member(db, user.id, project_id)
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, '项目不存在')
    start, end = time.fromisoformat(payload.workday_start), time.fromisoformat(payload.workday_end)
    if start >= end: raise HTTPException(422, '工作日结束时间必须晚于开始时间')
    project.leader_name = payload.leader_name.strip()
    project.workdays = payload.workdays
    project.workday_start = start
    project.workday_end = end
    db.commit()
    return {'success': True, 'id': project.id, 'leader_name': project.leader_name,
            'workdays': project.workdays, 'workday_start': start.strftime('%H:%M'), 'workday_end': end.strftime('%H:%M')}

@app.get('/api/v1/admin/enrollments/{enrollment_id}/collection-context')
def collection_context(enrollment_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment: raise HTTPException(404, '项目参与记录不存在')
    ensure_member(db, user.id, enrollment.project_id)
    project = db.get(Project, enrollment.project_id)
    subject = db.get(Subject, enrollment.subject_id)
    latest = db.scalar(select(Appointment).where(Appointment.enrollment_id == enrollment.id,
        Appointment.status == 'confirmed').order_by(Appointment.id.desc()))
    if latest and latest.confirmed_at:
        suggested = latest.confirmed_at
    elif latest:
        suggested = latest.requested_at
    else:
        suggested = datetime.now().replace(second=0, microsecond=0)
    return {'enrollment_id': enrollment.id, 'subject_code': subject.subject_code, 'subject_name': subject.name or '',
            'project_title': project.title, 'appointment_at': suggested.isoformat(),
            'has_appointment': latest is not None}

@app.get('/api/v1/admin/projects/{project_id}/subjects')
def admin_subjects(project_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    ensure_member(db, user.id, project_id)
    rows = db.execute(select(Enrollment, Subject).join(Subject, Subject.id == Enrollment.subject_id)
                      .where(Enrollment.project_id == project_id).order_by(Enrollment.id.desc())).all()
    return [{'enrollment_id': e.id, **format_profile(s)} for e, s in rows]

@app.post('/api/v1/admin/collections')
def add_collection(payload: CollectionIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    e = db.get(Enrollment, payload.enrollment_id)
    if not e:
        raise HTTPException(404, '项目参与记录不存在')
    ensure_member(db, user.id, e.project_id)
    if payload.status not in ('success', 'failed', 'aborted'):
        raise HTTPException(422, '采集状态不合法')
    if payload.status == 'failed' and not payload.failure_reason.strip():
        raise HTTPException(422, '采集失败时必须填写原因')
    if payload.collected_at.tzinfo is not None:
        raise HTTPException(422, '请传本地时间，不附加时区偏移')
    if payload.collected_at < datetime(2000,1,1):
        raise HTTPException(422, '采集日期不能早于 2000 年')
    if payload.collected_at > datetime.now() + timedelta(minutes=5):
        # If the entered time exactly matches this enrollment's confirmed booking,
        # accept it to avoid a false mismatch from the appointment-prefill workflow.
        matching_booking = db.scalar(select(Appointment).where(
            Appointment.enrollment_id == e.id, Appointment.status == 'confirmed',
            (Appointment.confirmed_at == payload.collected_at) | (Appointment.requested_at == payload.collected_at)))
        if not matching_booking:
            raise HTTPException(422, '采集时间晚于当前时间，且不匹配已确认预约时间。请确认实际采集时间，或先审核预约。')
    last_attempt = db.scalar(select(func.max(Collection.attempt_no)).where(
        Collection.enrollment_id == e.id)) or 0
    attempt = last_attempt + 1
    project = db.get(Project, e.project_id)
    subject = db.get(Subject, e.subject_id)
    code = f'{project.project_code}-{subject.subject_code}-{attempt:03d}'
    record = Collection(enrollment_id=e.id, attempt_no=attempt, collection_code=code,
                        status=payload.status, failure_reason=payload.failure_reason.strip() if payload.status == 'failed' else None,
                        data_reference=payload.data_reference.strip() or None,
                        collected_at=payload.collected_at, created_by=user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return collection_out(record)

@app.get('/api/v1/admin/projects/{project_id}/collections')
def admin_collections(project_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    ensure_member(db, user.id, project_id)
    rows = db.execute(select(Collection, Subject.subject_code).join(Enrollment,
        Enrollment.id == Collection.enrollment_id).join(Subject, Subject.id == Enrollment.subject_id)
        .where(Enrollment.project_id == project_id).order_by(Collection.id.desc())).all()
    return [{'subject_code': code, **collection_out(c)} for c, code in rows]

@app.get('/api/v1/collections/me')
def my_collections(user: User = Depends(current_user), db: Session = Depends(db_session)):
    subject = current_subject(db, user.id)
    rows = db.execute(select(Collection, Project.title).join(Enrollment, Enrollment.id == Collection.enrollment_id)
       .join(Project, Project.id == Enrollment.project_id).where(Enrollment.subject_id == subject.id)
       .order_by(Collection.id.desc())).all()
    return [{'project_title': title, **collection_out(c)} for c, title in rows]

@app.post('/api/v1/appointments')
def request_appointment(payload: AppointmentIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    subject = current_subject(db, user.id)
    enrollment = db.get(Enrollment, payload.enrollment_id)
    if not enrollment or enrollment.subject_id != subject.id:
        raise HTTPException(403, '不能预约其他受试者的项目')
    project = db.get(Project, enrollment.project_id)
    if payload.requested_at.tzinfo is not None or not datetime.now() < payload.requested_at < datetime.now() + timedelta(days=180):
        raise HTTPException(422, '预约时间需为未来180天内的本地时间')
    if payload.appointment_type not in ('first', 'reschedule'):
        raise HTTPException(422, '预约类型无效')
    if payload.appointment_type == 'first':
        duplicate = db.scalar(select(Appointment).where(Appointment.enrollment_id == enrollment.id,
            Appointment.appointment_type == 'first', Appointment.status.in_(['pending','confirmed'])))
        if duplicate: raise HTTPException(409, '该项目已有待审核或已确认的首次采集预约，请查看我的预约记录')
    previous = None
    if payload.appointment_type == 'reschedule':
        previous = db.get(Collection, payload.previous_collection_id) if payload.previous_collection_id else None
        if not previous or previous.enrollment_id != enrollment.id or previous.status != 'failed':
            raise HTTPException(422, '只能针对本人本项目失败的采集记录重新预约')
        pending = db.scalar(select(Appointment).where(Appointment.previous_collection_id == previous.id,
                                                Appointment.status.in_(['pending','confirmed'])))
        if pending:
            raise HTTPException(409, '这次失败记录已有待处理或已确认预约')
    elif payload.previous_collection_id is not None:
        raise HTTPException(422, '首次预约不应关联历史采集记录')
    # Project working-day window: weekdays use ISO values Monday=1 ... Sunday=7.
    if payload.requested_at.isoweekday() not in (project.workdays or [1,2,3,4,5]):
        raise HTTPException(422, '所选日期不在项目设置的工作日内')
    requested_clock = payload.requested_at.time().replace(tzinfo=None)
    if requested_clock < project.workday_start or requested_clock > project.workday_end:
        raise HTTPException(422, f'预约时间需在项目工作时段 {project.workday_start.strftime("%H:%M")}–{project.workday_end.strftime("%H:%M")} 内')
    a = Appointment(enrollment_id=enrollment.id, previous_collection_id=previous.id if previous else None,
                    appointment_type=payload.appointment_type, requested_at=payload.requested_at,
                    note=payload.note.strip(), status='pending')
    db.add(a)
    db.commit()
    db.refresh(a)
    return appointment_out(a)

@app.get('/api/v1/appointments/me')
def my_appointments(user: User = Depends(current_user), db: Session = Depends(db_session)):
    subject = current_subject(db, user.id)
    rows = db.execute(select(Appointment, Project.title).join(Enrollment,
        Enrollment.id == Appointment.enrollment_id).join(Project, Project.id == Enrollment.project_id)
        .where(Enrollment.subject_id == subject.id).order_by(Appointment.id.desc())).all()
    return [{'project_title': title, **appointment_out(a)} for a, title in rows]

@app.get('/api/v1/admin/projects/{project_id}/appointments')
def admin_appointments(project_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    ensure_member(db, user.id, project_id)
    rows = db.execute(select(Appointment, Subject.subject_code, Subject.name).join(Enrollment,
        Enrollment.id == Appointment.enrollment_id).join(Subject, Subject.id == Enrollment.subject_id)
        .where(Enrollment.project_id == project_id).order_by(Appointment.id.desc())).all()
    return [{'subject_code': code, 'subject_name': name or '', **appointment_out(a)} for a, code, name in rows]

@app.patch('/api/v1/admin/appointments/{appointment_id}')
def review_appointment(appointment_id: int, payload: AppointmentReview,
                       user: User = Depends(current_user), db: Session = Depends(db_session)):
    a = db.get(Appointment, appointment_id)
    if not a:
        raise HTTPException(404, '预约不存在')
    e = db.get(Enrollment, a.enrollment_id)
    ensure_member(db, user.id, e.project_id)
    if a.status != 'pending':
        raise HTTPException(409, '预约已经审核，不能重复审核')
    if payload.status not in ('confirmed','rejected'):
        raise HTTPException(422, '审核状态无效')
    if payload.status == 'confirmed' and (payload.confirmed_at is None or payload.confirmed_at.tzinfo is not None or payload.confirmed_at < datetime.now()):
        raise HTTPException(422, '确认预约需要填写将来的本地时间')
    a.status = payload.status
    a.confirmed_at = payload.confirmed_at if payload.status == 'confirmed' else None
    a.admin_note = payload.admin_note.strip()
    db.commit()
    return appointment_out(a)

@app.get('/api/v1/admin/projects/{project_id}/export')
def export_project(project_id: int, user: User = Depends(current_user), db: Session = Depends(db_session)):
    # Pseudonymized export only. Identity/contact data are intentionally excluded.
    ensure_member(db, user.id, project_id)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from fastapi.responses import StreamingResponse
    wb = Workbook()
    ws = wb.active
    ws.title = '受试者资料'
    ws.append(['受试者编号','姓名','性别','出生日期','身高(cm)','体重(kg)','BMI','项目问卷(JSON)'])
    rows = db.execute(select(Enrollment, Subject, FormResponse).join(Subject,
         Subject.id == Enrollment.subject_id).outerjoin(FormResponse,
         FormResponse.enrollment_id == Enrollment.id).where(Enrollment.project_id == project_id)).all()
    import json
    def safe_excel(value):
        # Prevent spreadsheet formula injection from user-provided strings.
        if isinstance(value, str) and value[:1] in ('=', '+', '-', '@', '\t', '\r'):
            return chr(39) + value
        return value
    for en, sub, response in rows:
        info = format_profile(sub)
        ws.append([info['subject_code'], safe_excel(info['name']), info['gender'],info['birth_date'], info['height_cm'],
                   info['weight_kg'], info['bmi'],safe_excel(json.dumps(response.answers if response else {},ensure_ascii=False))])
    ws2 = wb.create_sheet('采集记录')
    ws2.append(['受试者编号','采集编号','第几次','状态','失败原因','数据关联编号','采集日期','采集时间'])
    for c, code in db.execute(select(Collection,Subject.subject_code).join(Enrollment,
         Enrollment.id == Collection.enrollment_id).join(Subject,
         Subject.id == Enrollment.subject_id).where(Enrollment.project_id == project_id)).all():
        ws2.append([code,c.collection_code,c.attempt_no,c.status,safe_excel(c.failure_reason or ''),safe_excel(c.data_reference or ''),c.collected_at.date().isoformat(), c.collected_at.strftime('%H:%M:%S')])
    ws3 = wb.create_sheet('预约记录')
    ws3.append(['受试者编号','前次采集编号','预约类型','期望时间','确认时间','状态','受试者备注','管理员备注'])
    for a, code, prev_code in db.execute(select(Appointment, Subject.subject_code, Collection.collection_code)
        .join(Enrollment, Enrollment.id == Appointment.enrollment_id).join(Subject,
        Subject.id == Enrollment.subject_id).outerjoin(Collection, Collection.id == Appointment.previous_collection_id)
        .where(Enrollment.project_id == project_id)).all():
        ws3.append([code,prev_code or '',a.appointment_type,a.requested_at.isoformat(sep=' '),
                    a.confirmed_at.isoformat(sep=' ') if a.confirmed_at else '',a.status,safe_excel(a.note),safe_excel(a.admin_note)])
    for sheet in wb.worksheets:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True,color='FFFFFF')
            cell.fill = PatternFill('solid',fgColor='1F6282')
            cell.alignment = Alignment(wrap_text=True)
        for col in sheet.columns:
            letter = col[0].column_letter
            sheet.column_dimensions[letter].width = min(48,max(14,max(len(str(cell.value or '')) for cell in col)+3))
        sheet.row_dimensions[1].height=30
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="ResearchHub_project_{project_id}.xlsx"',
                 'Cache-Control': 'no-store'})

def seed_projects(db: Session):
    samples = [
        ('CVP', '无创中心静脉压采集研究', '演示用项目：多模态生理信号采集。', '项目负责人A', [
            {'key': 'position', 'label': '本次计划采集体位', 'type': 'select', 'options': ['仰卧', '坐位', '其他'], 'required': True},
            {'key': 'comment', 'label': '其他说明', 'type': 'text', 'required': False}]),
        ('PPG', 'PPG 血压信号采集研究', '演示用项目：光电容积脉搏波采集。', '项目负责人B', [
            {'key': 'site', 'label': '本次采集部位', 'type': 'select', 'options': ['左手拇指','左手食指','左手中指','左手无名指','左手小指','右手拇指','右手食指','右手中指','右手无名指','右手小指','其他'], 'required': True},
            {'key': 'comment', 'label': '其他说明', 'type': 'text', 'required': False}])
    ]
    for code, title, description, leader_name, form_schema in samples:
        existing = db.scalar(select(Project).where(Project.project_code == code))
        if not existing:
            db.add(Project(project_code=code, title=title, description=description, leader_name=leader_name, form_schema=form_schema))
        else:
            existing.leader_name = leader_name if existing.leader_name in (None, '', '待设置') else existing.leader_name
            if code == 'PPG': existing.form_schema = form_schema
    db.commit()

def upgrade_existing_schema():
    # Small additive migration for local V0.2 installations; preserves existing records.
    insp = inspect(engine)
    with engine.begin() as conn:
        if insp.has_table('subjects'):
            cols = {c['name'] for c in inspect(engine).get_columns('subjects')}
            if 'name' not in cols:
                conn.execute(text('ALTER TABLE subjects ADD COLUMN name VARCHAR(80) NULL'))
        if insp.has_table('projects'):
            cols = {c['name'] for c in inspect(engine).get_columns('projects')}
            additions = [
                ('leader_name', "ALTER TABLE projects ADD COLUMN leader_name VARCHAR(80) NOT NULL DEFAULT '待设置'"),
                ('workdays', 'ALTER TABLE projects ADD COLUMN workdays JSON NULL'),
                ('workday_start', "ALTER TABLE projects ADD COLUMN workday_start TIME NOT NULL DEFAULT '09:00:00'"),
                ('workday_end', "ALTER TABLE projects ADD COLUMN workday_end TIME NOT NULL DEFAULT '17:00:00'")]
            for col, sql in additions:
                if col not in cols: conn.execute(text(sql))
            conn.execute(text("UPDATE projects SET workdays=" + ("JSON_ARRAY(1,2,3,4,5)" if engine.dialect.name == 'mysql' else "'[1,2,3,4,5]'") + " WHERE workdays IS NULL"))
        if insp.has_table('appointments'):
            cols = {c['name']: c for c in inspect(engine).get_columns('appointments')}
            if 'appointment_type' not in cols:
                conn.execute(text("ALTER TABLE appointments ADD COLUMN appointment_type VARCHAR(20) NOT NULL DEFAULT 'reschedule'"))
            if 'previous_collection_id' in cols and not cols['previous_collection_id'].get('nullable', True):
                id_type = str(inspect(engine).get_columns('collections')[0]['type']).upper()
                fk_type = 'BIGINT' if 'BIGINT' in id_type else 'INT'
                conn.execute(text(f'ALTER TABLE appointments MODIFY previous_collection_id {fk_type} NULL'))

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    upgrade_existing_schema()
    with SessionLocal() as db:
        seed_projects(db)
