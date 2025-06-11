import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, Tuple

class DataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        """Initialize the analyzer with a pandas DataFrame"""
        self.df = df
        
        # Basic validation
        if df.empty:
            raise ValueError("DataFrame is empty")
    
    def analyze(self) -> Dict[str, Any]:
        """Perform all analyses and return results as a dictionary"""
        return {
            "basic_stats": self.calculate_basic_stats(),
            "missing_values": self.analyze_missing_values(),
            "correlations": self.analyze_correlations(),
            "anomalies": self.detect_anomalies(),
            "metadata": {
                "rows": len(self.df),
                "columns": list(self.df.columns),
                "dtypes": {col: str(dtype) for col, dtype in self.df.dtypes.items()}
            }
        }
    
    def calculate_basic_stats(self) -> Dict[str, Any]:
        """Calculate basic statistics for numeric columns"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        
        stats_dict = {}
        for col in numeric_cols:
            stats_dict[col] = {
                "mean": float(self.df[col].mean()),
                "std": float(self.df[col].std()),
                "min": float(self.df[col].min()),
                "max": float(self.df[col].max()),
                "median": float(self.df[col].median()),
                "q1": float(self.df[col].quantile(0.25)),
                "q3": float(self.df[col].quantile(0.75)),
                "skew": float(self.df[col].skew()),
                "kurtosis": float(self.df[col].kurtosis())
            }
        
        return stats_dict
    
    def analyze_missing_values(self) -> Dict[str, Any]:
        """Analyze missing values in the dataset"""
        missing_stats = {
            "total_missing": int(self.df.isnull().sum().sum()),
            "missing_per_column": self.df.isnull().sum().to_dict(),
            "missing_percentage": (self.df.isnull().sum() / len(self.df) * 100).round(2).to_dict()
        }
        return missing_stats
    
    def analyze_correlations(self) -> Dict[str, Any]:
        """Calculate correlations between numeric columns"""
        numeric_df = self.df.select_dtypes(include=[np.number])
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
    
    def detect_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies using Z-score and IQR methods"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        anomalies = {}
        
        for col in numeric_cols:
            # Z-score method
            z_scores = np.abs(stats.zscore(self.df[col].dropna()))
            z_score_threshold = 3
            z_score_anomalies = self.df[z_scores > z_score_threshold].index.tolist()
            
            # IQR method
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            iqr_anomalies = self.df[(self.df[col] < (Q1 - 1.5 * IQR)) | 
                                  (self.df[col] > (Q3 + 1.5 * IQR))].index.tolist()
            
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

def analyze_file(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Analyze a CSV file and return both the DataFrame and analysis results"""
    df = pd.read_csv(file_path)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()
    return df, results
