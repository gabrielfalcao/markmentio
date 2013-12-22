"""start

Revision ID: 2d72eb3902f6
Revises: 4d7b1801b86a
Create Date: 2013-09-29 23:43:44.306468

"""

# revision identifiers, used by Alembic.
revision = '2d72eb3902f6'
down_revision = None

from datetime import datetime
from alembic import op
import sqlalchemy as db



def now():
    return datetime.now()


def upgrade():
    op.create_table('md_user',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('github_id', db.Integer, nullable=False, unique=True),
        db.Column('github_token', db.String(256), nullable=True),
        db.Column('gravatar_id', db.String(40), nullable=False, unique=True),
        db.Column('username', db.String(80), nullable=False, unique=True),
        db.Column('md_token', db.String(40), nullable=False, unique=True),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )
    op.create_table('md_organization',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('owner_id', db.Integer, nullable=False),
        db.Column('name', db.String(80), nullable=False),
        db.Column('email', db.String(100), nullable=False, unique=True),
        db.Column('company', db.UnicodeText, nullable=True),
        db.Column('blog', db.UnicodeText, nullable=True),
        db.Column('avatar_url', db.UnicodeText, nullable=True),
        db.Column('created_at', db.DateTime, default=now),
        db.Column('updated_at', db.DateTime, default=now),
    )
    op.create_table('md_organization_users',
        db.Column('id', db.Integer, primary_key=True),
        db.Column('user_id', db.Integer, nullable=False),
        db.Column('organization_id', db.Integer, nullable=False),

    )
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

def downgrade():
    op.drop_table('md_log')
    op.drop_table('md_http_cache')
    op.drop_table('md_organization_users')
    op.drop_table('md_organization')
    op.drop_table('md_user')
