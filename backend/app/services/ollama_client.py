"""
Ollama client for open-source LLM interactions.
"""
import os
from typing import List, Dict, Any, Optional, AsyncIterator
import logging
import httpx
import json

logger = logging.getLogger(__name__)

# Default Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


class OllamaClient:
    """Client for interacting with Ollama API for LLM inference."""
    
    def __init__(
        self,
        host: str = OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
        timeout: float = 120.0
    ):
        """
        Initialize the Ollama client.
        
        Args:
            host: Ollama server URL
            model: Default model to use
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        context: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The prompt to send to the model
            model: Model to use (defaults to self.model)
            system: Optional system prompt
            context: Optional conversation context
            options: Optional model options (temperature, top_p, etc.)
            stream: Whether to stream the response
            
        Returns:
            Dictionary containing the response
        """
        try:
            url = f"{self.host}/api/generate"
            
            payload = {
                "model": model or self.model,
                "prompt": prompt,
                "stream": stream
            }
            
            if system:
                payload["system"] = system
            
            if context:
                payload["context"] = context
            
            if options:
                payload["options"] = options
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream a completion from the LLM.
        
        Args:
            prompt: The prompt to send to the model
            model: Model to use (defaults to self.model)
            system: Optional system prompt
            options: Optional model options
            
        Yields:
            Dictionary chunks containing partial responses
        """
        try:
            url = f"{self.host}/api/generate"
            
            payload = {
                "model": model or self.model,
                "prompt": prompt,
                "stream": True
            }
            
            if system:
                payload["system"] = system
            
            if options:
                payload["options"] = options
            
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)
                        
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Chat with the LLM using message format.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.model)
            options: Optional model options
            stream: Whether to stream the response
            
        Returns:
            Dictionary containing the response
        """
        try:
            url = f"{self.host}/api/chat"
            
            payload = {
                "model": model or self.model,
                "messages": messages,
                "stream": stream
            }
            
            if options:
                payload["options"] = options
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream a chat response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to self.model)
            options: Optional model options
            
        Yields:
            Dictionary chunks containing partial responses
        """
        try:
            url = f"{self.host}/api/chat"
            
            payload = {
                "model": model or self.model,
                "messages": messages,
                "stream": True
            }
            
            if options:
                payload["options"] = options
            
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        yield json.loads(line)
                        
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            raise
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models in Ollama."""
        try:
            url = f"{self.host}/api/tags"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            url = f"{self.host}/api/tags"
            response = await self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


# Global singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client(
    host: str = OLLAMA_HOST,
    model: str = DEFAULT_MODEL
) -> OllamaClient:
    """Get or create the Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient(host=host, model=model)
    return _ollama_client
