import os
from pathlib import Path
import psycopg
with psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')) as connection:
    connection.execute(Path(__file__).with_name('db').joinpath('001_init.sql').read_text())
print('Schema v1 ready')
