import os
from typing import List, Literal, Optional
from uuid import UUID
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.access import IntegrationAccess, AccessDenied
from app.domain import Event
from app.repository import PostgresRepository

Sector = Literal['logistics', 'retail', 'services']
Status = Literal['pending', 'in_progress', 'completed', 'cancelled']

def create_app(repository=None):
    access = IntegrationAccess(os.environ)
    repo = repository or PostgresRepository(os.environ['DATABASE_URL'])
    app = FastAPI(title='NexusInsight API', version='0.1.0')
    app.add_middleware(CORSMiddleware, allow_origins=[os.environ.get('WEB_ORIGIN', 'http://localhost:5174')],
                       allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'X-Organization-ID', 'Content-Type'])

    def require(permission):
        def authorize(authorization: str = Header(default=''), x_organization_id: str = Header(default='')):
            try:
                return access.authorize(authorization, x_organization_id, permission)
            except AccessDenied as exc:
                raise HTTPException(exc.status, 'Invalid credential' if exc.status == 401 else 'Access denied') from None
        return authorize

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'nexusinsight', 'version': '0.1.0'}

    @app.get('/ready', responses={503: {'description': 'Database unavailable'}})
    def readiness():
        try:
            repo.ping()
        except SQLAlchemyError:
            raise HTTPException(503, 'Database unavailable', headers={'Cache-Control': 'no-store'}) from None
        return JSONResponse(
            {'status': 'ready', 'service': 'nexusinsight', 'version': '0.1.0'},
            headers={'Cache-Control': 'no-store'})

    @app.post('/v1/events')
    def ingest(events: List[Event], org: UUID = Depends(require('write'))):
        if len(events) > 1000:
            raise HTTPException(422, 'Batch limit: 1000 events')
        if any(e.organization_id != org for e in events):
            raise HTTPException(403, 'Cross-organization event rejected')
        return repo.ingest(events)

    @app.get('/v1/operations')
    def operations(sector: Optional[Sector] = None, status: Optional[Status] = None,
                   offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), org: UUID = Depends(require('read'))):
        return repo.rows(org, sector, status, offset, limit)

    @app.get('/v1/metrics')
    def aggregate(sector: Optional[Sector] = None, status: Optional[Status] = None, org: UUID = Depends(require('read'))):
        return repo.aggregate(org, sector, status)

    return app
