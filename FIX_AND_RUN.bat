@echo off
echo ==========================================
echo  ADORKABLE AI - FIX AND RUN SCRIPT
echo ==========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

echo [1/6] Installing core dependencies...
pip install fastapi uvicorn sqlalchemy aiosqlite python-jose passlib python-multipart python-dotenv requests aiofiles pydantic email-validator -q

echo [2/6] Installing ML/Computer Vision packages...
pip install opencv-python Pillow scikit-learn tensorflow -q

echo [3/6] Installing MediaPipe (compatible version)...
pip install mediapipe==0.10.35 -q

echo [4/6] Installing Frontend packages...
pip install streamlit plotly httpx pandas -q

echo [5/6] Installing test packages...
pip install pytest -q

echo [6/6] All dependencies installed!
echo.
echo ==========================================
echo  STARTING BACKEND SERVER
echo ==========================================
echo.
echo API will be available at: http://localhost:8000
echo API Docs at: http://localhost:8000/docs
echo.
echo Press CTRL+C to stop, then run frontend in new terminal
echo.

python -m uvicorn backend.main:app --reload --port 8000
