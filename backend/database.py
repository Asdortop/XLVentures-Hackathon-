from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./praxis.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Domain(Base):
    __tablename__ = "domains"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    industry = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="domain")
    nbas = relationship("NBA", back_populates="domain")
    memory_patterns = relationship("MemoryPattern", back_populates="domain")


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    entity_name = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    domain = relationship("Domain", back_populates="interactions")
    nba = relationship("NBA", back_populates="interaction", uselist=False)


class NBA(Base):
    __tablename__ = "nbas"
    id = Column(Integer, primary_key=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=False)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    hitl_status = Column(String, default="pending")  # pending / approved / rejected
    rejection_reason = Column(Text, nullable=True)
    agent_log = Column(JSON, default=list)
    matched_intent = Column(String, default="")
    severity = Column(String, default="medium")
    blast_radius = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    interaction = relationship("Interaction", back_populates="nba")
    domain = relationship("Domain", back_populates="nbas")
    actions = relationship("NBAAction", back_populates="nba", order_by="NBAAction.rank")


class NBAAction(Base):
    __tablename__ = "nba_actions"
    id = Column(Integer, primary_key=True)
    nba_id = Column(Integer, ForeignKey("nbas.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    action = Column(Text, nullable=False)
    owner = Column(String, default="")
    priority = Column(String, default="medium")
    action_type = Column(String, default="task")
    confidence = Column(Float, default=0.5)
    estimated_hours = Column(Float, default=1.0)
    evidence = Column(JSON, default=list)

    nba = relationship("NBA", back_populates="actions")


class MemoryPattern(Base):
    __tablename__ = "memory_patterns"
    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    issue_type = Column(String, nullable=False)
    issue_text = Column(Text, default="")
    resolution = Column(Text, default="")
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_used = Column(DateTime, default=datetime.utcnow)

    domain = relationship("Domain", back_populates="memory_patterns")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    nba_id = Column(Integer, nullable=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
