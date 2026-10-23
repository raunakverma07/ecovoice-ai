# EcoVoice AI

An AI assistant for exploring sustainability and environmental topics.

## Getting started

Create and activate a Python virtual environment, then install the dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a Gemini API key in Google AI Studio, then put it in the local `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Never share or commit your API key. The `.env` file is ignored by Git.

Start EcoVoice from the project folder:

```powershell
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Ask questions by typing or using the microphone button. Microphone input depends on browser support and permission; the assistant can also read answers aloud using your browser's speech synthesis.

The app runs locally and sends conversation text to Google's Gemini API to generate answers. Availability, quotas, and possible charges depend on your Google AI Studio account and current plan. Keep the server bound to localhost unless you add appropriate authentication and deployment security.