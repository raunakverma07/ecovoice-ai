"""Local Flask server for the EcoVoice AI assistant."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

SYSTEM_INSTRUCTIONS = (
	"You are EcoVoice, a helpful assistant focused on sustainability and the environment. "
	"Give practical, balanced answers, distinguish established facts from uncertainty, and "
	"never invent statistics, sources, or environmental claims. Keep answers concise and "
	"ask a clarifying question when location or context materially changes the advice."
)


@app.get("/")
def home():
	return send_from_directory(app.static_folder, "index.html")


@app.post("/chat")
def chat():
	api_key = os.getenv("GEMINI_API_KEY", "").strip()
	if not api_key or api_key in {"your_api_key_here", "your_gemini_api_key_here"}:
		return jsonify(error="Add your Gemini API key to the .env file, then restart EcoVoice."), 503

	payload = request.get_json(silent=True)
	if not isinstance(payload, dict):
		return jsonify(error="Send a JSON object containing your question."), 400

	messages = payload.get("messages")
	if not isinstance(messages, list) or not messages or len(messages) > 20:
		return jsonify(error="Conversation must contain between 1 and 20 messages."), 400

	safe_messages = []
	for message in messages:
		if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
			return jsonify(error="Each message must have a user or assistant role."), 400
		content = message.get("content")
		if not isinstance(content, str) or not content.strip() or len(content) > 4000:
			return jsonify(error="Each message must contain 1 to 4000 characters."), 400
		safe_messages.append({"role": message["role"], "content": content.strip()})

	if safe_messages[-1]["role"] != "user":
		return jsonify(error="The latest message must be a user question."), 400

	model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
	fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
	models_to_try = [model]
	if fallback_model != model:
		models_to_try.append(fallback_model)

	client = genai.Client(
		api_key=api_key,
		http_options=types.HttpOptions(
			timeout=12_000,
			retry_options=types.HttpRetryOptions(attempts=1),
		),
	)
	contents = [
		types.Content(
			role="user" if message["role"] == "user" else "model",
			parts=[types.Part.from_text(text=message["content"])],
		)
		for message in safe_messages
	]
	last_api_error = None
	for index, model_to_try in enumerate(models_to_try):
		try:
			result = client.models.generate_content(
				model=model_to_try,
				contents=contents,
				config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
			)
			break
		except genai_errors.APIError as error:
			last_api_error = error
			app.logger.error("Gemini API error %s for %s: %s", error.code, model_to_try, error.message)
			if error.code not in {429, 503, 504} or index == len(models_to_try) - 1:
				if error.code in {401, 403}:
					message = "Gemini rejected the API key or this key does not have API access. Check GEMINI_API_KEY in .env."
				elif error.code == 404:
					message = f"Gemini model '{model_to_try}' is unavailable to this key. Set GEMINI_MODEL to a model enabled in Google AI Studio."
				elif error.code == 429:
					message = "Gemini quota or rate limit was reached for both models. Wait for the limit to reset or check this key's quota and billing in Google AI Studio."
				elif error.code in {503, 504}:
					message = "Gemini is temporarily busy or slow. Both configured models were tried; wait briefly and try again."
				else:
					message = "Gemini request failed. Check the server terminal for the API error details."
				return jsonify(error=message), 503 if error.code == 503 else 504 if error.code == 504 else 502
			app.logger.warning("Trying Gemini fallback model %s after API error %s", fallback_model, error.code)
		except Exception:
			app.logger.exception("Gemini request failed unexpectedly")
			return jsonify(error="Could not reach Gemini. Check the server connection and try again."), 502
	else:
		app.logger.error("Gemini models failed: %s", last_api_error)
		return jsonify(error="Gemini is temporarily unavailable. Please try again shortly."), 503

	answer = (result.text or "").strip()
	if not answer:
		return jsonify(error="The AI service returned an empty answer. Please try again."), 502
	return jsonify(answer=answer)


@app.errorhandler(413)
def request_too_large(_error):
	return jsonify(error="The request is too large. Shorten the conversation and try again."), 413


if __name__ == "__main__":
	app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)