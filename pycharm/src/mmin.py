import asyncio
import httpx
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


class AegisMaritimeAgent:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.ais_key = os.getenv("AISSTREAM_API_KEY")
        if not self.groq_key or not self.ais_key:
            raise EnvironmentError("❌ API Keys missing in .env")
        self.client_ai = Groq(api_key=self.groq_key)

    def _safe_float(self, value):
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    async def fetch_intel(self, target):
        """Asynchronous data collection from AIS and Weather sources."""
        async with httpx.AsyncClient(timeout=25.0) as client:
            ais_url = "https://datadocked.com/api/vessels_operations/get-vessel-info"
            try:
                res = await client.get(ais_url, params={"imo_or_mmsi": target}, headers={"x-api-key": self.ais_key})
                res.raise_for_status()
                ais = res.json()

                # Normalize types for UI and Map safety
                ais['latitude'] = self._safe_float(ais.get('latitude'))
                ais['longitude'] = self._safe_float(ais.get('longitude'))
                ais['speed'] = self._safe_float(ais.get('speed', 0))

                # Fetch Live Marine Weather
                try:
                    w_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={ais['latitude']}&longitude={ais['longitude']}&current=wave_height"
                    w_res = await client.get(w_url)
                    weather = w_res.json().get('current', {'wave_height': 0.0})
                except Exception:
                    weather = {'wave_height': 0.0}

                return ais, weather
            except Exception:
                return None

    def generate_audit(self, ais, weather):
        """Generates a professional AI maritime compliance summary."""
        try:
            prompt = (f"Role: Senior Maritime QA Auditor. Vessel: {ais.get('name')}. "
                      f"Sea State: {weather.get('wave_height')}m waves. "
                      f"Action: Provide a 2-sentence professional compliance summary.")
            chat = self.client_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile"
            )
            return chat.choices[0].message.content
        except Exception:
            return "AI Analysis temporarily offline. Manual registry verification required."