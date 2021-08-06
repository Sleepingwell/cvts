"""Module providing an ORM for objects of interest."""

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

DBase = declarative_base()

class Traversal(DBase):
    """A traversal of a :py:class:`Segment`."""
    __tablename__ = 'traversals'
    id            = Column(Integer, primary_key=True)
    way           = Column(String)
    rego          = Column(String)
    hour          = Column(Integer)
    weekday       = Column(Integer)
    speed         = Column(Float)
    weight        = Column(Float)

class Base(DBase):
    """The location a vehicle is garraged."""
    __tablename__ = 'bases'
    id            = Column(Integer, primary_key=True)
    rego          = Column(String)
    lng           = Column(Float)
    lat           = Column(Float)
