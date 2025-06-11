import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, Tuple, List
import plotly.express as px
import plotly.graph_objects as go
import json

class DataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        """Initialize the analyzer with a pandas DataFrame"""
        self.df = df
        
        # Basic validation
        if df.empty:
            raise ValueError("DataFrame is empty")
    
    def analyze(self) -> Dict[str, Any]:
        """Perform all analyses and return results as a dictionary"""
        analysis_results = {
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
        
        # Generate visualizations
        visualizations = self.generate_visualizations()
        analysis_results["visualizations"] = visualizations
        
        return analysis_results

    def generate_visualizations(self) -> Dict[str, Any]:
        """Generate various visualizations for the dataset"""
        visualizations = {
            "histograms": self._generate_histograms(),
            "correlation_heatmap": self._generate_correlation_heatmap(),
            "boxplots": self._generate_boxplots()
        }
        return visualizations
    
    def _generate_histograms(self) -> Dict[str, Any]:
        """Generate histograms for numeric columns"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        histograms = {}
        
        for col in numeric_cols:
            # Create histogram using plotly
            fig = px.histogram(
                self.df,
                x=col,
                nbins=30,
                title=f"Distribution of {col}",
                labels={col: col},
                marginal="box"  # Add a box plot on the margin
            )
            
            # Update layout
            fig.update_layout(
                showlegend=False,
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            # Convert to JSON-serializable format
            histograms[col] = {
                "data": json.loads(fig.to_json()),
                "type": "histogram"
            }
        
        return histograms
    
    def _generate_correlation_heatmap(self) -> Dict[str, Any]:
        """Generate correlation heatmap for numeric columns"""
        numeric_df = self.df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return None
        
        corr_matrix = numeric_df.corr()
        
        # Create heatmap using plotly
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmin=-1,
            zmax=1,
            colorbar=dict(
                title='Correlation',
                titleside='right',
                titlefont=dict(size=14)
            ),
            text=[[f'{val:.2f}' for val in row] for row in corr_matrix.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False,
            hoverinfo='text'
        ))
        
        # Update layout for better readability
        fig.update_layout(
            title={
                'text': "Correlation Heatmap",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=20)
            },
            height=600,
            width=800,
            margin=dict(l=20, r=20, t=60, b=20),
            xaxis=dict(
                tickangle=45,
                tickfont=dict(size=10),
                tickmode='array',
                ticktext=corr_matrix.columns,
                tickvals=corr_matrix.columns
            ),
            yaxis=dict(
                tickfont=dict(size=10),
                tickmode='array',
                ticktext=corr_matrix.columns,
                tickvals=corr_matrix.columns
            )
        )
        
        # Ensure the figure is properly serialized
        return {
            "data": json.loads(fig.to_json()),
            "type": "heatmap",
            "layout": {
                "height": 600,
                "width": "100%",
                "autosize": True,
                "margin": {"l": 20, "r": 20, "t": 60, "b": 20}
            }
        }
    
    def _generate_boxplots(self) -> Dict[str, Any]:
        """Generate boxplots for numeric columns"""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        boxplots = {}
        
        for col in numeric_cols:
            # Create boxplot using plotly
            fig = px.box(
                self.df,
                y=col,
                title=f"Boxplot of {col}",
                points="outliers"  # Show outliers as points
            )
            
            # Update layout
            fig.update_layout(
                showlegend=False,
                height=400,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            
            # Convert to JSON-serializable format
            boxplots[col] = {
                "data": json.loads(fig.to_json()),
                "type": "boxplot"
            }
        
        return boxplots
    
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
            # Get non-null values for the column
            col_data = self.df[col].dropna()
            
            # Z-score method
            z_scores = np.abs(stats.zscore(col_data))
            z_score_threshold = 3
            # Get indices of anomalies relative to the non-null data
            z_score_anomaly_indices = col_data.index[z_scores > z_score_threshold].tolist()
            
            # IQR method
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            # Get indices of anomalies relative to the non-null data
            iqr_anomaly_indices = col_data.index[
                (col_data < (Q1 - 1.5 * IQR)) | 
                (col_data > (Q3 + 1.5 * IQR))
            ].tolist()
            
            anomalies[col] = {
                "z_score_anomalies": {
                    "count": len(z_score_anomaly_indices),
                    "indices": z_score_anomaly_indices[:100]  # Limit to first 100 for JSON serialization
                },
                "iqr_anomalies": {
                    "count": len(iqr_anomaly_indices),
                    "indices": iqr_anomaly_indices[:100]  # Limit to first 100 for JSON serialization
                }
            }
        
        return anomalies

def analyze_file(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Analyze a CSV file and return both the DataFrame and analysis results"""
    df = pd.read_csv(file_path)
    analyzer = DataAnalyzer(df)
    results = analyzer.analyze()
    return df, results
