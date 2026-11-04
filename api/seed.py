import json
from pathlib import Path
from app.domain import Event
from app.main import create_app
from app.repository import PostgresRepository
import os
events = [Event.model_validate(e) for e in json.loads(Path(__file__).resolve().parents[1].joinpath('examples/operations.events.json').read_text())]
print(PostgresRepository(os.environ['DATABASE_URL']).ingest(events))
