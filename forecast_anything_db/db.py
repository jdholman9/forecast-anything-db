"""Lazy engine / session factory. Importing this module does not connect;
the engine is created on first use so pure-logic code stays DB-free."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import database_url

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), future=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine(), expire_on_commit=False, class_=Session)
    return _Session


def session() -> Session:
    return get_sessionmaker()()
