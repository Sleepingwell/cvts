from sqlalchemy import Table, Column, Integer, String, Text, Float, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from cvts.settings import POSTGRES_CONNECTION_STRING

Base = declarative_base()



class Vehicle(Base):
    __tablename__ = 'vehicles'
    id       = Column(Integer, primary_key=True)
    rego     = Column(String, unique=True, nullable=False)

class GeoLocation(Base):
    __tablename__ = 'geolocations'
    id       = Column(Integer, primary_key=True)
    x        = Column(Float, nullable=False)
    y        = Column(Float, nullable=False)

class Stop(Base):
    __tablename__ = 'stops'
    id       = Column(Integer, primary_key=True)
    location = relationship('GeoLocation')
    time     = Column(Integer)
    location_id = Column(Integer, ForeignKey('geolocations.id'))

class Segment(Base):
    __tablename__ = 'segments'
    id       = Column(Integer, primary_key=True)
    name     = Column(String, unique=True, nullable=True)

class Traversal(Base):
    __tablename__ = 'traversals'
    id       = Column(Integer, primary_key=True)
    time     = Column(Integer)
    segment  = relationship('Segment', backref='segments')
    trip     = relationship('Trip', backref='trips')
    segment_id = Column(Integer, ForeignKey('segments.id'))
    trip_id  = Column(Integer, ForeignKey('trips.id'))

class MeasurementType(Base):
    __tablename__ = 'measurementtypes'
    id       = Column(Integer, primary_key=True)
    name     = Column(String, unique=True, nullable=False)

class Mearsument(Base):
    __tablename__ = 'measurements'
    id       = Column(Integer, primary_key=True)
    value    = Column(Float)
    mtype    = relationship('MeasurmentType')
    traversal= relationship('Traversal', backref='measurements')
    mtype_id = Column(Integer, ForeignKey('measurementtypes.id'))
    traversal_id = Column(Integer, ForeignKey('traversals.id'))

class Trip(Base):
    __tablename__ = "trips"
    id       = Column(Integer, primary_key=True)
    start    = relationship('Stop')
    end      = relationship('Stop')
    journey  = relationship('Journey', backref='trips')
    start_id = Column(Integer, ForeignKey('stops.id'))
    end_id   = Column(Integer, ForeignKey('stops.id'))
    journey_id = Column(Integer, ForeignKey('journeys.id'))

class Journey(Base):
    __tablename__ = 'journeys'
    id = Column(Integer, primary_key=True)
    vehicle  = relationship('Vehicle', backref='journeys')
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'))
