from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import os
from pathlib import Path
from .tasks import analyze_file_background
from sqlalchemy.orm import Session
from .database import get_db, engine, Base
from .models import UploadedFile, ReportEntry, CorrelationEntry, AnomalyEntry, VisualizationEntry
from sqlalchemy import desc
import shutil
from datetime import datetime
from .scheduler import setup_scheduler, shutdown_scheduler
import logging
from .tasks import DataAnalysisTask
from contextlib import asynccontextmanager
from .analysis_s3 import get_analysis_from_s3

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    try:
        setup_scheduler()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    try:
        shutdown_scheduler()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}")
        raise

app = FastAPI(title="Data Profiler", lifespan=lifespan)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Create database tables
Base.metadata.create_all(bind=engine)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main upload page"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Handle file upload and start analysis"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Save the file
        file_path = UPLOAD_DIR / file.filename
        contents = await file.read()
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        # Create base URL for the application
        base_url = str(request.base_url).rstrip('/')
        
        # Start background analysis
        if background_tasks:
            background_tasks.add_task(analyze_file_background, file_path, background_tasks)
            return {
                "message": "File uploaded successfully. Analysis started in background.",
                "filename": file.filename,
                "status": "processing",
                "analysis_url": f"{base_url}/view/{file.filename}"
            }
        else:
            # If no background tasks, perform analysis immediately
            results = await analyze_file_background(file_path, None)
            return {
                "message": "File uploaded and analyzed successfully",
                "filename": file.filename,
                "status": "completed",
                "analysis": results,
                "analysis_url": f"{base_url}/view/{file.filename}"
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await file.close()

@app.get("/analysis/{filename}")
async def get_analysis(filename: str, db: Session = Depends(get_db)):
    """Get analysis results for a specific file from the database or S3"""
    try:
        # First try to get from database
        file_entry = db.query(UploadedFile)\
            .filter(UploadedFile.original_filename == filename)\
            .order_by(desc(UploadedFile.upload_time))\
            .first()
        
        if file_entry:
            if file_entry.status == "failed":
                raise HTTPException(status_code=500, detail=f"Analysis failed: {file_entry.error_message}")
            
            if file_entry.status == "processing":
                return {
                    "status": "processing",
                    "message": "Analysis in progress"
                }
            
            # Get all analysis results from database
            reports = db.query(ReportEntry)\
                .filter(ReportEntry.file_id == file_entry.id)\
                .all()
            
            correlations = db.query(CorrelationEntry)\
                .filter(CorrelationEntry.file_id == file_entry.id)\
                .all()
            
            anomalies = db.query(AnomalyEntry)\
                .filter(AnomalyEntry.file_id == file_entry.id)\
                .all()
            
            visualizations = db.query(VisualizationEntry)\
                .filter(VisualizationEntry.file_id == file_entry.id)\
                .all()
            
            # Format results from database
            return format_analysis_results(file_entry, reports, correlations, anomalies, visualizations)
        
        # If not in database, try to get from S3
        s3_data = get_analysis_from_s3(filename)
        if s3_data:
            return {
                **s3_data,
                "source": "s3",
                "status": "completed"
            }
        
        raise HTTPException(status_code=404, detail="Analysis not found in database or S3")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def format_analysis_results(file_entry, reports, correlations, anomalies, visualizations):
    """Format analysis results from database entries"""
    # Format basic stats and missing values
    basic_stats = {}
    missing_values = {
        "total_missing": 0,
        "missing_per_column": {},
        "missing_percentage": {}
    }
    
    for report in reports:
        # Basic stats
        if report.mean is not None:  # Only numeric columns have these stats
            basic_stats[report.column] = {
                "mean": report.mean,
                "std": report.stddev,
                "min": report.min_value,
                "max": report.max_value,
                "median": report.median,
                "q1": report.q1,
                "q3": report.q3,
                "skew": report.skew,
                "kurtosis": report.kurtosis
            }
        
        # Missing values
        missing_values["missing_per_column"][report.column] = report.missing_count
        missing_values["missing_percentage"][report.column] = report.missing_percentage
        missing_values["total_missing"] += report.missing_count
    
    # Format correlations
    strong_correlations = [
        {
            "column1": corr.column1,
            "column2": corr.column2,
            "correlation": corr.correlation
        }
        for corr in correlations
    ]
    
    # Format anomalies
    anomalies_dict = {}
    for anomaly in anomalies:
        if anomaly.column not in anomalies_dict:
            anomalies_dict[anomaly.column] = {
                "z_score_anomalies": {"count": 0, "indices": []},
                "iqr_anomalies": {"count": 0, "indices": []}
            }
        
        if anomaly.method == "z_score":
            anomalies_dict[anomaly.column]["z_score_anomalies"] = {
                "count": anomaly.count,
                "indices": anomaly.anomaly_indices
            }
        else:  # iqr
            anomalies_dict[anomaly.column]["iqr_anomalies"] = {
                "count": anomaly.count,
                "indices": anomaly.anomaly_indices
            }
    
    # Format visualizations
    vis_dict = {
        "histograms": {},
        "correlation_heatmap": None,
        "boxplots": {}
    }
    
    for vis in visualizations:
        if vis.visualization_type == "histogram":
            vis_dict["histograms"][vis.column] = {
                "data": vis.data,
                "type": "histogram"
            }
        elif vis.visualization_type == "heatmap":
            vis_dict["correlation_heatmap"] = {
                "data": vis.data,
                "type": "heatmap"
            }
        elif vis.visualization_type == "boxplot":
            vis_dict["boxplots"][vis.column] = {
                "data": vis.data,
                "type": "boxplot"
            }
    
    return {
        "basic_stats": basic_stats,
        "missing_values": missing_values,
        "correlations": {
            "strong_correlations": sorted(strong_correlations, 
                                       key=lambda x: abs(x["correlation"]), 
                                       reverse=True)
        },
        "anomalies": anomalies_dict,
        "visualizations": vis_dict,
        "timestamp": file_entry.analysis_completed_at.isoformat(),
        "file_name": file_entry.original_filename,
        "rows": file_entry.row_count,
        "columns": [report.column for report in reports],
        "source": "database",
        "status": "completed"
    }

@app.get("/view/{filename}")
async def view_analysis(filename: str, request: Request):
    """Serve the analysis results page"""
    return templates.TemplateResponse(
        "analysis.html",
        {
            "request": request,
            "file_name": filename
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
