import boto3
import os
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .models import UploadedFile, ReportEntry, CorrelationEntry, AnomalyEntry, VisualizationEntry
from .database import SessionLocal

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

def upload_to_s3(file_path: str, s3_key: str):
    """Upload a file to S3"""
    bucket = os.getenv("S3_BUCKET")
    s3.upload_file(file_path, bucket, s3_key)
    print(f"✅ Uploaded {file_path} to S3 as {s3_key}")

def format_analysis_data(file_entry: UploadedFile, db: Session) -> dict:
    """Format analysis data from database entries into a JSON-serializable dictionary"""
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
        "metadata": {
            "timestamp": file_entry.analysis_completed_at.isoformat(),
            "file_name": file_entry.original_filename,
            "rows": file_entry.row_count,
            "columns": [report.column for report in reports],
            "upload_time": file_entry.upload_time.isoformat(),
            "analysis_time": (file_entry.analysis_completed_at - file_entry.upload_time).total_seconds()
        }
    }

def upload_old_analyses(hours_threshold: int = 3):
    """Upload analysis results older than the specified hours to S3 and delete from database"""
    db = SessionLocal()
    try:
        # Calculate the cutoff time in UTC
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
        
        # Get all completed analyses older than the cutoff time
        # Convert database timestamps to UTC for comparison
        old_files = db.query(UploadedFile)\
            .filter(UploadedFile.status == "completed")\
            .filter(UploadedFile.analysis_completed_at.astimezone(timezone.utc) < cutoff_time)\
            .all()
        
        bucket = os.getenv("S3_BUCKET")
        uploaded_count = 0
        deleted_count = 0
        
        for file_entry in old_files:
            try:
                # Format the analysis data
                analysis_data = format_analysis_data(file_entry, db)
                
                # Create S3 key with UTC timestamp
                timestamp = file_entry.analysis_completed_at.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
                s3_key = f"analysis_results/{timestamp}_{file_entry.original_filename}.json"
                
                # Convert to JSON and upload to S3
                json_data = json.dumps(analysis_data, indent=2)
                s3.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=json_data,
                    ContentType='application/json'
                )
                
                # Delete related entries from database
                db.query(VisualizationEntry).filter(VisualizationEntry.file_id == file_entry.id).delete()
                db.query(AnomalyEntry).filter(AnomalyEntry.file_id == file_entry.id).delete()
                db.query(CorrelationEntry).filter(CorrelationEntry.file_id == file_entry.id).delete()
                db.query(ReportEntry).filter(ReportEntry.file_id == file_entry.id).delete()
                db.delete(file_entry)
                db.commit()
                
                print(f"✅ Uploaded and deleted analysis for {file_entry.original_filename}")
                uploaded_count += 1
                deleted_count += 1
                
            except Exception as e:
                db.rollback()
                print(f"❌ Error processing {file_entry.original_filename}: {str(e)}")
                continue
        
        print(f"\n📊 Summary: Uploaded {uploaded_count} and deleted {deleted_count} analysis results")
        
    finally:
        db.close()

def get_analysis_from_s3(filename: str) -> dict:
    """Fetch analysis results for a specific file from S3"""
    bucket = os.getenv("S3_BUCKET")
    try:
        # List objects in the bucket with the filename
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=f"analysis_results/",
            MaxKeys=1000
        )
        
        # Find the most recent analysis for this filename
        matching_files = []
        for obj in response.get('Contents', []):
            if filename in obj['Key']:
                matching_files.append(obj)
        
        if not matching_files:
            return None
            
        # Sort by last modified time and get the most recent
        latest_file = max(matching_files, key=lambda x: x['LastModified'])
        
        # Get the file content
        response = s3.get_object(
            Bucket=bucket,
            Key=latest_file['Key']
        )
        
        # Parse and return the JSON data
        analysis_data = json.loads(response['Body'].read().decode('utf-8'))
        return analysis_data
        
    except Exception as e:
        print(f"❌ Error fetching analysis from S3: {str(e)}")
        return None

if __name__ == "__main__":
    # Run the upload for analyses older than 3 hours
    upload_old_analyses(hours_threshold=3)
