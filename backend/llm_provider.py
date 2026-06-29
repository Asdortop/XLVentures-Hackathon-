"""
Multi-provider LLM client: Groq → Gemini → Ollama (fallback chain)
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def generate(self, prompt: str, system: str = "You are a helpful AI assistant.") -> str:
        errors = []

        if self.groq_key:
            try:
                result = self._call_groq(prompt, system)
                print(f"[LLM] Using Groq ({self.groq_model})")
                return result
            except Exception as e:
                errors.append(f"Groq: {e}")
                print(f"[LLM] Groq failed: {e}")

        if self.gemini_key:
            try:
                result = self._call_gemini(prompt, system)
                print(f"[LLM] Using Gemini ({self.gemini_model})")
                return result
            except Exception as e:
                errors.append(f"Gemini: {e}")
                print(f"[LLM] Gemini failed: {e}")

        try:
            result = self._call_ollama(prompt, system)
            print(f"[LLM] Using Ollama ({self.ollama_model})")
            return result
        except Exception as e:
            errors.append(f"Ollama: {e}")

        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")

    def _call_groq(self, prompt: str, system: str) -> str:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.groq_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 4096,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, prompt: str, system: str) -> str:
        full_prompt = f"{system}\n\n{prompt}"
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}",
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _call_ollama(self, prompt: str, system: str) -> str:
        resp = requests.post(
            f"{self.ollama_base}/api/generate",
            json={
                "model": self.ollama_model,
                "prompt": f"{system}\n\n{prompt}",
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"]


# Singleton
llm = LLMProvider()
