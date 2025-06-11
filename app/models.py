from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

Base = declarative_base()

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # size in bytes
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    analysis_completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    reports = relationship("ReportEntry", back_populates="file", cascade="all, delete-orphan")
    correlations = relationship("CorrelationEntry", back_populates="file", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyEntry", back_populates="file", cascade="all, delete-orphan")

class ReportEntry(Base):
    __tablename__ = "file_reports"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.id', ondelete='CASCADE'))
    column = Column(String, nullable=False)
    mean = Column(Float, nullable=True)
    stddev = Column(Float, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    median = Column(Float, nullable=True)
    q1 = Column(Float, nullable=True)
    q3 = Column(Float, nullable=True)
    skew = Column(Float, nullable=True)
    kurtosis = Column(Float, nullable=True)
    missing_count = Column(Integer, default=0)
    missing_percentage = Column(Float, nullable=True)
    data_type = Column(String, nullable=True)  # numeric, categorical, datetime, etc.
    
    # Relationship
    file = relationship("UploadedFile", back_populates="reports")

class CorrelationEntry(Base):
    __tablename__ = "correlations"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.id', ondelete='CASCADE'))
    column1 = Column(String, nullable=False)
    column2 = Column(String, nullable=False)
    correlation = Column(Float, nullable=False)
    
    # Relationship
    file = relationship("UploadedFile", back_populates="correlations")

class AnomalyEntry(Base):
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('uploaded_files.id', ondelete='CASCADE'))
    column = Column(String, nullable=False)
    method = Column(String, nullable=False)  # z_score or iqr
    anomaly_indices = Column(JSON, nullable=False)  # Store as JSON array
    threshold = Column(Float, nullable=True)
    count = Column(Integer, nullable=False)
    
    # Relationship
    file = relationship("UploadedFile", back_populates="anomalies")
