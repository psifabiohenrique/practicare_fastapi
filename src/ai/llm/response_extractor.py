from langchain_core.messages import AIMessage


class ResponseExtractor:
    @staticmethod
    def extract_text(response: AIMessage) -> str:
        if isinstance(response.content, str):
            return response.content

        if isinstance(response.content, list):
            texts = [
                block["text"]
                for block in response.content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "\n".join(texts)

        raise ValueError("Formato de resposta inesperado do LLM")
