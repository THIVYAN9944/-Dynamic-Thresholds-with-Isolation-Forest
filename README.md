# CampusPulse

**End-to-End Network Experience Recorder and Intermittent Degradation Localisation System**

## 1. Project Overview
CampusPulse is a prototype system that continuously records campus network experience metrics. It is designed to capture intermittent degradations that often disappear before network engineers can investigate manually.

## 2. Problem Statement
A campus network serves diverse locations (classrooms, hostels, offices). Users often experience intermittent slowness and service degradation. Because legacy workflows rely on manual user reports and delayed investigation, the root cause is frequently missed.

## 3. Architecture
The project is built using a modular architecture:
- `frontend/`: Streamlit dashboard and multi-page UI.
- `backend/`: FastAPI application handling data ingestion and APIs.
- `services/`: Core logic for anomaly detection, localisation, and recommendations.
- `simulation/`: Synthetic data generator and failure injection system.
- `data/`: SQLite database and legacy CSV data.

## 4. Features
- **Live Experience Monitoring:** Real-time metrics visualization using Plotly.
- **Automated Incident Detection:** Rule-based evaluation of telemetry data.
- **Localisation:** Pinpoints the most affected campus locations.
- **User Reports Engine:** Correlates manual reports with automated metrics.
- **Failure Simulator:** Interactively inject faults to test system responsiveness.
- **Migration & Rollback:** Compare legacy workflows, import legacy CSVs, and demonstrate system rollbacks.

## 5. Technology Stack
- **Frontend:** Streamlit, Plotly
- **Backend:** FastAPI, Pydantic, SQLAlchemy
- **Database:** SQLite
- **Data Processing:** Pandas
- **Testing:** Pytest

## 6. Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 7. Running Backend
```bash
source venv/bin/activate
uvicorn backend.main:app --reload
```
The API documentation will be available at `http://127.0.0.1:8000/docs`.

## 8. Running Streamlit
Open a new terminal:
```bash
source venv/bin/activate
streamlit run frontend/app.py
```

## 9. API Documentation
The system provides endpoints for ingestion (`POST /api/probe`, `/api/wifi`, `/api/application`) and retrieval (`GET /api/dashboard`, `/api/incidents`). See `/docs` for swagger UI.

## 10. Dataset Description
The system generates realistic synthetic campus network data including metrics for latency, packet loss, wifi RSSI, wifi quality, and application response time, tagged with location coordinates.

## 11. Failure Simulation
Using the `Failure Simulator` Streamlit page, users can inject High Latency, Packet Loss, Weak Wi-Fi, and Application Slowdowns to trigger automatic incidents.

## 12. Baseline Comparison
The `Baseline vs Prototype` page contrasts the delayed manual legacy process with the real-time CampusPulse telemetry.

## 13. Migration
Legacy CSVs can be uploaded in the Migration page, where columns are validated and historical logs are mapped to the new database schema.

## 14. Rollback
The `Rollback Demonstration` page toggles the active system state between automated Prototype Mode and manual Legacy Mode, pausing automated data processing.

## 15. Testing
Run tests using:
```bash
pytest tests/
```

## 16. Evaluation
The `Evaluation Report` page shows simulated results highlighting a 98.5% detection rate, alongside detailed error analysis on False Positives and Negatives.

## 17. Limitations
- Static thresholds for anomaly detection can lead to false positives (e.g. temporary Wi-Fi drops).
- Localisation precision relies on AP to building mapping.

## 18. Future Improvements
- Implement machine learning for dynamic thresholds (e.g., Isolation Forest).
- Enhance the recommendation engine with LLM-based root cause analysis.
# -Dynamic-Thresholds-with-Isolation-Forest
