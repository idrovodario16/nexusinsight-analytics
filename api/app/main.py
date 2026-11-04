import os
import secrets
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.domain import Event
from app.repository import PostgresRepository

Sector = Literal['logistics', 'retail', 'services']
Status = Literal['pending', 'in_progress', 'completed', 'cancelled']

def create_app(repository=None):
    key = os.environ.get('API_KEY', '')
    if len(key) < 32:
        raise RuntimeError('API_KEY must contain at least 32 characters')
    tenant = UUID(os.environ['ORGANIZATION_ID'])
    repo = repository or PostgresRepository(os.environ['DATABASE_URL'])
    app = FastAPI(title='NexusInsight API', version='0.1.0')
    app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get('WEB_ORIGIN', 'http://localhost:5174')],
                       allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'X-Organization-ID', 'Content-Type'])

    def authorize(authorization: str = Header(default=''), x_organization_id: str = Header(default='')):
        if not secrets.compare_digest(authorization, 'Bearer ' + key):
            raise HTTPException(401, 'Invalid credential')
        if x_organization_id != str(tenant):
            raise HTTPException(403, 'Organization not authorized')
        return tenant

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'nexusinsight', 'version': '0.1.0'}

    @app.post('/v1/events')
    def ingest(events: List[Event], org: UUID = Depends(authorize)):
        if len(events) > 1000:
            raise HTTPException(422, 'Batch limit: 1000 events')
        if any(e.organization_id != org for e in events):
            raise HTTPException(403, 'Cross-organization event rejected')
        return repo.ingest(events)

    @app.get('/v1/operations')
    def operations(sector: Optional[Sector] = None, status: Optional[Status] = None,
                   offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), org: UUID = Depends(authorize)):
        return repo.rows(org, sector, status, offset, limit)

    @app.get('/v1/metrics')
    def aggregate(sector: Optional[Sector] = None, status: Optional[Status] = None, org: UUID = Depends(authorize)):
        return repo.aggregate(org, sector, status)

    return app
