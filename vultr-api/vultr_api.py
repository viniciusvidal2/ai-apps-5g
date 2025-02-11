import requests
import json
from typing import Dict, List
import streamlit as st

class VultrLLMAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.vultrinference.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def list_models(self) -> List[Dict]:
        """Lista todos os modelos disponíveis na API Vultr."""
        response = requests.get(
            f"{self.base_url}/models",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def generate_response(self, messages: List[Dict], model_id: str = "llama-3.1-70b-instruct-fp8") -> str:
        """Gera uma resposta usando o modelo especificado, mantendo o histórico do chat."""
        payload = {
            "model": model_id,
            "messages": messages,  # Passando todas as mensagens do histórico
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            st.error(f"Erro na API: {str(e)}")
            st.error(f"Resposta da API: {response.text}")
            return "Desculpe, ocorreu um erro ao gerar a resposta." 