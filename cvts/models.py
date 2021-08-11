"""Module providing an ORM for objects of interest."""

from sqlalchemy import Table, Column, Integer, String, Text, Float, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref, reconstructor
from sqlalchemy.ext.declarative import declarative_base
from cvts.settings import POSTGRES_CONNECTION_STRING

Base = declarative_base()



class Traversal(Base):
    """A traversal of a :py:class:`Segment`."""
    __tablename__ = 'traversals'
    id            = Column(Integer, primary_key=True)
    way           = Column(String)
    rego          = Column(String)
    hour          = Column(Integer)
    weekday       = Column(Integer)
    speed         = Column(Float)
    weight        = Column(Float)
