# 👗 Adorkable AI — Fashion Intelligence Platform

> **Eliminate outfit decision fatigue. Wear what already works, perfectly.**

Adorkable AI is a complete, production-quality fashion intelligence web application that combines computer vision, color theory, and weather data to curate personalized outfit recommendations.

## ✨ Features & Core Screens

- 👤 **My Profile:** The personalized setup area where the app gets to know the user. Uses MediaPipe to analyze uploaded selfies for skin tone, and gathers body shape details to unlock custom-tailored color palettes.
- 👕 **My Wardrobe:** The digital closet hub where users view, filter, and manage their uploaded garments. It acts as the foundation for all AI recommendations.
- 🎨 **Smart Color Matching & AI Classification:** Leverages MobileNetV2 for garment classification and K-Means for extracting dominant colors to pair complementary and analogous harmonies.
- 🌤️ **Daily Outfit:** A smart, real-time recommendation engine that suggests the perfect outfit for the day, factored around live weather data and temperature.
- 📅 **Weekly Planner:** A comprehensive 7-day outfit calendar. It syncs with the weekly weather forecast to plan a week’s worth of cohesive, varied outfits.
- 🎯 **Smart Combo:** An intelligent pairing tool where users select a single garment, and the AI instantly generates complete, color-coordinated outfits around that specific piece.
- 📊 **Analytics Dashboard:** An interactive visual hub built with Plotly that provides deep insights into wardrobe combinability, color distributions, and usage frequency.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Streamlit     │────▶│   FastAPI        │────▶│   SQLite        │
│   Frontend      │     │   Backend        │     │   Database      │
│   (Port 8501)   │     │   (Port 8000)    │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
      ┌──────────┐      ┌──────────┐      ┌──────────┐
      │MediaPipe │      │OpenWeather│     │ TensorFlow│
      │CV Models │      │   API    │      │ MobileNet │
      └──────────┘      └──────────┘      └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/mutahhar-mudassar/Adorkable_AI.git
cd adorkable_ai
```

2. **Create virtual environment (recommended):**
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your OpenWeatherMap API key
```

### Running the Application

**Start the backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

**Start the frontend (in a new terminal):**
```bash
cd frontend
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`

## 📁 Project Structure

```
adorkable_ai/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── database.py                # SQLAlchemy ORM models
│   ├── auth.py                    # JWT authentication
│   ├── config.py                  # Configuration & constants
│   ├── routers/
│   │   ├── wardrobe.py            # Garment CRUD endpoints
│   │   ├── profile.py             # Skin tone & body shape
│   │   ├── recommendations.py     # Daily outfit generation
│   │   ├── planner.py             # Weekly planning
│   │   ├── combo.py               # Smart combos
│   │   └── analytics.py           # Statistics endpoints
│   ├── ml/
│   │   ├── classifier.py          # MobileNetV2 classifier
│   │   ├── color_extractor.py     # K-Means dominant colors
│   │   ├── skin_tone.py           # MediaPipe face analysis
│   │   ├── body_shape.py          # Pose-based body shape
│   │   └── model_training.py      # Training script
│   ├── engine/
│   │   ├── color_theory.py        # Color harmony rules
│   │   ├── weather_rules.py       # Temperature-based rules
│   │   ├── outfit_scorer.py       # Master scoring engine
│   │   ├── stochastic_selector.py # Weighted random selection
│   │   ├── combo_generator.py     # Outfit pairing
│   │   └── weekly_planner.py      # 7-day planning
│   ├── data/
│   │   ├── trends_2026.json       # Seasonal trends
│   │   ├── color_mapping.json     # 60+ fashion colors
│   │   └── skin_tone_palette.json # Flattering color maps
│   └── utils/
│       ├── image_utils.py         # OpenCV helpers
│       └── weather_api.py         # OpenWeatherMap client
├── frontend/
│   ├── app.py                     # Streamlit entry
│   └── pages/
│       ├── 1_Register_Login.py
│       ├── 2_My_Profile.py
│       ├── 3_My_Wardrobe.py
│       ├── 4_Daily_Outfit.py
│       ├── 5_Weekly_Planner.py
│       ├── 6_Smart_Combo.py
│       └── 7_Analytics.py
├── tests/
│   ├── test_color_theory.py
│   ├── test_outfit_scorer.py
│   ├── test_classifier.py
│   └── test_api.py
├── requirements.txt
├── .env.example
└── README.md
```

## 🔌 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get JWT |
| GET | `/api/v1/auth/me` | Get current user |

### Wardrobe
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/wardrobe/` | List all garments |
| POST | `/api/v1/wardrobe/upload` | Upload garment image |
| DELETE | `/api/v1/wardrobe/{id}` | Delete garment |
| PATCH | `/api/v1/wardrobe/{id}/wear` | Mark as worn |
| GET | `/api/v1/wardrobe/stats` | Wardrobe statistics |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/profile/` | Get profile |
| POST | `/api/v1/profile/selfie` | Upload selfie for skin analysis |
| POST | `/api/v1/profile/body` | Upload body photo for shape analysis |
| GET | `/api/v1/profile/color-palette` | Get color recommendations |

### Recommendations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/recommend/daily` | Get daily outfit recommendation |

### Planning
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/plan/weekly` | Generate 7-day plan |
| GET | `/api/v1/plan/quick` | Quick plan with defaults |

### Combo Generator
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/combo/{item_id}` | Get matching outfits |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/wardrobe-colors` | Color distribution |
| GET | `/api/v1/analytics/garment-usage` | Usage statistics |
| GET | `/api/v1/analytics/combinability` | Outfit combination count |
| GET | `/api/v1/analytics/outfit-history` | Score history |

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=backend tests/

# Run specific test file
pytest tests/test_color_theory.py

# Run with verbose output
pytest -v tests/
```

## 🎓 Model Training

To train the clothing classifier with your own dataset:

```bash
# Prepare dataset in structure: category/style/image.jpg
python -m backend.ml.model_training --dataset ./dataset --epochs 20 --fine-tune
```

The trained model will be saved to `./models/clothing_classifier/`

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key | Required |
| `SECRET_KEY` | JWT signing key | Auto-generated |
| `DATABASE_URL` | SQLite database path | `sqlite:///./adorkable.db` |
| `MODEL_PATH` | Trained model directory | `./models/clothing_classifier` |
| `UPLOAD_DIR` | User uploads directory | `./uploads` |

## 🛠️ Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async SQLite), JWT
- **Frontend:** Streamlit, Plotly
- **ML/AI:** TensorFlow/Keras (MobileNetV2), MediaPipe, scikit-learn
- **Computer Vision:** OpenCV, Pillow
- **Testing:** pytest, httpx

## 🗺️ Roadmap

- [ ] Integration with clothing retailers
- [ ] Outfit try-on with AR
- [ ] Social features (share outfits)
- [ ] Calendar integration for event-based planning
- [ ] Outfit rating and feedback loop
- [ ] Multi-user family wardrobes
- [ ] Mobile app (React Native)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- MobileNetV2 architecture by Google
- MediaPipe by Google
- OpenWeatherMap for weather data
- Color theory based on Itten's color wheel

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the API docs at `/docs` when running locally

---

**Made with 💕 by Adorkable AI**

*Fashion is what you buy. Style is what you do with it.*
