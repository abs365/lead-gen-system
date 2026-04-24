import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./leadgen.db")
FOOD_DATA_BASE_URL: str = os.getenv("FOOD_DATA_BASE_URL", "https://api.ratings.food.gov.uk")
