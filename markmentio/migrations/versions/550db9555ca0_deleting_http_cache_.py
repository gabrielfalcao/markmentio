"""deleting http cache model

Revision ID: 550db9555ca0
Revises: 2d72eb3902f6
Create Date: 2013-10-13 23:13:42.964641

"""

# revision identifiers, used by Alembic.
revision = '550db9555ca0'
down_revision = '2d72eb3902f6'

from datetime import datetime
from alembic import op
import sqlalchemy as db



def now():
    return datetime.now()


def upgrade():
    op.drop_table('md_log')
    op.drop_table('md_http_cache')


def downgrade():
    op.create_table('md_http_cache',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('url', db.Unicode(length=200), nullable=False),
        db.Column('token', db.String(length=200), nullable=True),
        db.Column('content', db.UnicodeText, nullable=True),
        db.Column('headers', db.UnicodeText, nullable=True),
        db.Column('status_code', db.Integer, nullable=True),
        db.Column('updated_at', db.DateTime, default=now)
    )
    op.create_table('md_log',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('level', db.Integer, nullable=True),
        db.Column('user_id', db.Integer, nullable=True),
        db.Column('message', db.UnicodeText, nullable=True),
        db.Column('data', db.UnicodeText, nullable=True),
        db.Column('created_at', db.DateTime, default=now),
    )
