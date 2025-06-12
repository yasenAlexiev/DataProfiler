# DataProfiler

A web application for automated data analysis and visualization of CSV files. Perfect for analyzing biomedical experiments, IoT device data, financial datasets, and more.

## Features

### Data Analysis
- **Basic Statistics**: Mean, median, standard deviation, quartiles, skewness, and kurtosis
- **Missing Data Analysis**: Total missing values, missing values per column, and missing percentages
- **Correlation Analysis**: Strong correlations between variables with correlation coefficients
- **Anomaly Detection**: Identifies outliers using both Z-score and IQR methods

### Visualizations
- **Histograms**: Distribution analysis for each numeric column
- **Correlation Heatmaps**: Visual representation of variable correlations
- **Box Plots**: Distribution and outlier visualization for numeric columns

### Data Management
- **Automatic Storage**: Analysis results are stored in a database for quick access
- **S3 Integration**: Old analyses are automatically archived to S3 for long-term storage
- **Smart Retrieval**: Results are fetched from database or S3 based on availability

## Technical Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Background processing for analysis tasks
- **Storage**: AWS S3 for long-term data archival
- **Visualization**: Plotly for interactive charts
- **Frontend**: HTML, JavaScript, Bootstrap

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/DataProfiler.git
cd DataProfiler
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/dataprofiler
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
S3_BUCKET=your_bucket_name
```

5. Initialize the database:
```bash
alembic upgrade head
```

6. Run the application:
```bash
uvicorn app.main:app --reload
```

## Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Upload a CSV file through the web interface
3. Wait for the analysis to complete (progress is shown in real-time)
4. View the comprehensive analysis report including:
   - Basic statistics for each column
   - Missing data analysis
   - Correlation analysis
   - Anomaly detection results
   - Interactive visualizations

## Data Retention

- Recent analyses (last 3 hours) are kept in the database for quick access
- Older analyses are automatically archived to S3
- Archived analyses can still be accessed through the web interface
- The system automatically manages storage by moving old data to S3

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

