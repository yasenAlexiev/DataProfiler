from fastapi import BackgroundTasks
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from scipy import stats
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import UploadedFile, ReportEntry, CorrelationEntry, AnomalyEntry

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAnalysisTask:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.db = SessionLocal()
        
    def __del__(self):
        self.db.close()
        
    def analyze(self) -> Dict[str, Any]:
        """Main analysis function that orchestrates all analysis tasks"""
        try:
            # Read the CSV file
            df = pd.read_csv(self.file_path)
            
            # Basic validation
            if df.empty:
                raise ValueError("File is empty")
            
            # Create file entry in database
            file_entry = UploadedFile(
                filename=str(self.file_path),
                original_filename=self.file_path.name,
                status="processing",
                file_size=self.file_path.stat().st_size,
                row_count=len(df),
                column_count=len(df.columns)
            )
            self.db.add(file_entry)
            self.db.commit()
            self.db.refresh(file_entry)
            
            try:
                # Perform all analyses
                basic_stats = self._calculate_basic_stats(df)
                missing_values = self._analyze_missing_values(df)
                correlations = self._analyze_correlations(df)
                anomalies = self._detect_anomalies(df)
                
                # Save results to database
                self._save_results_to_db(
                    file_entry.id,
                    df,
                    basic_stats,
                    missing_values,
                    correlations,
                    anomalies
                )
                
                # Update file status
                file_entry.status = "completed"
                file_entry.analysis_completed_at = datetime.utcnow()
                self.db.commit()
                
                # Return results for immediate display
                return {
                    "basic_stats": basic_stats,
                    "missing_values": missing_values,
                    "correlations": correlations,
                    "anomalies": anomalies,
                    "timestamp": datetime.now().isoformat(),
                    "file_name": self.file_path.name,
                    "rows": len(df),
                    "columns": list(df.columns)
                }
                
            except Exception as e:
                file_entry.status = "failed"
                file_entry.error_message = str(e)
                self.db.commit()
                raise
                
        except Exception as e:
            logger.error(f"Error analyzing file {self.file_path}: {str(e)}")
            raise
    
    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic statistics for numeric columns"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        stats_dict = {}
        for col in numeric_cols:
            stats_dict[col] = {
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "median": float(df[col].median()),
                "q1": float(df[col].quantile(0.25)),
                "q3": float(df[col].quantile(0.75)),
                "skew": float(df[col].skew()),
                "kurtosis": float(df[col].kurtosis())
            }
        
        return stats_dict
    
    def _analyze_missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze missing values in the dataset"""
        missing_stats = {
            "total_missing": int(df.isnull().sum().sum()),
            "missing_per_column": df.isnull().sum().to_dict(),
            "missing_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict()
        }
        return missing_stats
    
    def _analyze_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate correlations between numeric columns"""
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return {"message": "Not enough numeric columns for correlation analysis"}
        
        corr_matrix = numeric_df.corr()
        
        # Get strong correlations (absolute value > 0.5)
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if abs(corr_matrix.iloc[i, j]) > 0.5:
                    strong_correlations.append({
                        "column1": corr_matrix.columns[i],
                        "column2": corr_matrix.columns[j],
                        "correlation": float(corr_matrix.iloc[i, j])
                    })
        
        return {
            "correlation_matrix": corr_matrix.round(3).to_dict(),
            "strong_correlations": sorted(strong_correlations, 
                                       key=lambda x: abs(x["correlation"]), 
                                       reverse=True)
        }
    
    def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies using Z-score and IQR methods"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        anomalies = {}
        
        for col in numeric_cols:
            # Z-score method
            z_scores = np.abs(stats.zscore(df[col].dropna()))
            z_score_threshold = 3
            z_score_anomalies = df[z_scores > z_score_threshold].index.tolist()
            
            # IQR method
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            iqr_anomalies = df[(df[col] < (Q1 - 1.5 * IQR)) | 
                             (df[col] > (Q3 + 1.5 * IQR))].index.tolist()
            
            anomalies[col] = {
                "z_score_anomalies": {
                    "count": len(z_score_anomalies),
                    "indices": z_score_anomalies[:100]  # Limit to first 100 for JSON serialization
                },
                "iqr_anomalies": {
                    "count": len(iqr_anomalies),
                    "indices": iqr_anomalies[:100]  # Limit to first 100 for JSON serialization
                }
            }
        
        return anomalies
    
    def _save_results_to_db(
        self,
        file_id: int,
        df: pd.DataFrame,
        basic_stats: Dict[str, Any],
        missing_values: Dict[str, Any],
        correlations: Dict[str, Any],
        anomalies: Dict[str, Any]
    ) -> None:
        """Save analysis results to the database"""
        try:
            # Save basic stats and missing values for each column
            for col in df.columns:
                report = ReportEntry(
                    file_id=file_id,
                    column=col,
                    data_type=str(df[col].dtype)
                )
                
                # Add numeric statistics if column is numeric
                if col in basic_stats:
                    stats = basic_stats[col]
                    report.mean = stats["mean"]
                    report.stddev = stats["std"]
                    report.min_value = stats["min"]
                    report.max_value = stats["max"]
                    report.median = stats["median"]
                    report.q1 = stats["q1"]
                    report.q3 = stats["q3"]
                    report.skew = stats["skew"]
                    report.kurtosis = stats["kurtosis"]
                
                # Add missing value statistics
                report.missing_count = missing_values["missing_per_column"][col]
                report.missing_percentage = missing_values["missing_percentage"][col]
                
                self.db.add(report)
            
            # Save correlations
            if "strong_correlations" in correlations:
                for corr in correlations["strong_correlations"]:
                    correlation_entry = CorrelationEntry(
                        file_id=file_id,
                        column1=corr["column1"],
                        column2=corr["column2"],
                        correlation=corr["correlation"]
                    )
                    self.db.add(correlation_entry)
            
            # Save anomalies
            for col, anomaly_data in anomalies.items():
                # Save Z-score anomalies
                if anomaly_data["z_score_anomalies"]["count"] > 0:
                    z_score_entry = AnomalyEntry(
                        file_id=file_id,
                        column=col,
                        method="z_score",
                        anomaly_indices=anomaly_data["z_score_anomalies"]["indices"],
                        threshold=3.0,
                        count=anomaly_data["z_score_anomalies"]["count"]
                    )
                    self.db.add(z_score_entry)
                
                # Save IQR anomalies
                if anomaly_data["iqr_anomalies"]["count"] > 0:
                    iqr_entry = AnomalyEntry(
                        file_id=file_id,
                        column=col,
                        method="iqr",
                        anomaly_indices=anomaly_data["iqr_anomalies"]["indices"],
                        count=anomaly_data["iqr_anomalies"]["count"]
                    )
                    self.db.add(iqr_entry)
            
            self.db.commit()
            logger.info(f"Analysis results saved to database for file_id {file_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving results to database: {str(e)}")
            raise

async def analyze_file_background(file_path: Path, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Background task to analyze a CSV file"""
    try:
        analyzer = DataAnalysisTask(file_path)
        results = analyzer.analyze()
        return results
    except Exception as e:
        logger.error(f"Background task failed: {str(e)}")
        raise
