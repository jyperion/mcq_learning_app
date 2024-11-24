import aiohttp
import asyncio
from typing import Dict, Any

class OllamaClient:
    """Client for interacting with Ollama API"""
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = None
        self._semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate(self, prompt: str, model: str = "llama3.2:latest", **kwargs) -> str:
        """Generate a response from Ollama"""
        async with self._semaphore:
            if not self.session:
                raise RuntimeError("Client not initialized. Use 'async with' context manager.")

            data = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get('temperature', 0.7),
                    "top_p": kwargs.get('top_p', 0.9),
                    "top_k": kwargs.get('top_k', 40),
                    "num_predict": kwargs.get('num_predict', 1024),
                    "repeat_penalty": kwargs.get('repeat_penalty', 1.1),
                }
            }

            try:
                async with self.session.post(f"{self.base_url}/api/generate", json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error (status {response.status}): {error_text}")
                    
                    result = await response.json()
                    return result.get('response', '')

            except aiohttp.ClientError as e:
                raise Exception(f"Failed to connect to Ollama API: {str(e)}")
            except Exception as e:
                raise Exception(f"Error querying Ollama: {str(e)}")

async def query_ollama(prompt: str, model: str = "llama3.2:latest", **kwargs) -> str:
    """Convenience function to query Ollama without explicitly managing the client"""
    async with OllamaClient() as client:
        return await client.generate(prompt, model, **kwargs)
