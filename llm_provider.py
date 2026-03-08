import os
from enum import Enum
from typing import Optional


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    HUGGINGFACE = "huggingface"


PROVIDER_DEFAULTS = {
    "gemini": {
        "model": "gemini-3.1-flash-lite-preview",
        "description": "Google Gemini 3.1 Flash Lite (free API key)",
    },
    "huggingface": {
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "description": "Llama 3.1 8B via HuggingFace Inference API",
        
    }
}

def create_llm(
    provider: str = "ollama",
    model: Optional[str] = None,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
):
    provider = provider.lower()
    if model is None:
        model = PROVIDER_DEFAULTS.get(provider, {}).get("model", "llama3.1")

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        gemini_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            raise ValueError(
                "Gemini requires an API key. Set GEMINI_API_KEY env var or pass api_key.\n"
                "Get a free key at: https://ai.google.dev/gemini-api/docs/api-key"
            )

        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=gemini_key,
            convert_system_message_to_human=True, 
        )
    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

        hf_token = api_key or os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
        if not hf_token:
            raise ValueError(
                "HuggingFace requires an API token. Set HF_TOKEN env var or pass api_key.\n"
                "Get a free token at: https://huggingface.co/settings/tokens"
            )

        # Create the endpoint
        endpoint = HuggingFaceEndpoint(
            repo_id=model,
            temperature=temperature,
            huggingfacehub_api_token=hf_token,
            max_new_tokens=2048,
            task="text-generation",
        )

        return ChatHuggingFace(
            llm=endpoint,
            huggingfacehub_api_token=hf_token,
        )

    else:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Supported: gemini, huggingface"
        )


