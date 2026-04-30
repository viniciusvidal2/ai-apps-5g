import cv2
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import numpy as np
import base64
import io

import requests


class MedicalDocsOCR:
    def __init__(self) -> None:
        """Class constructor to init the agent capabilities"""
        # Documents to be converted
        self.document_paths = []
        # OCR model initialization
        self.ocr_paddle = PaddleOCR(use_angle_cls=True, lang='pt')
        # OCR using LLM model from ollama with langchain
        self.ocr_llm = ChatOllama(model="glm-ocr:latest",
                                  base_url="http://localhost:11434",
                                  debug=False)
        # Document classification model from ollama with langchain
        self.classify_improve_llm = ChatOllama(model="gemma4:latest",
                                               base_url="http://localhost:11434",
                                               debug=False)


# region Sets

    def set_documents_to_process(self, document_paths: list) -> None:
        # Store the document paths for processing
        self.document_paths = document_paths

#  endregion
# region Gets

    def get_documents_to_process(self) -> list:
        """
        Returns the documents to be processed.

        Returns:
            list: A list of document paths that are set for processing.
        """
        return self.document_paths

# endregion
# region Internal methods

    def _pdf_to_text_paddle(self, pages) -> list:
        full_text = []
        for i, page in enumerate(pages):
            print(f"Processing page {i+1}/{len(pages)}")
            # Convert PIL image to numpy array and predict text using Paddle OCR
            image = np.array(page)
            result = self.ocr_paddle.ocr(image)
            print(f"OCR result for page {i+1}: {result}")
            if result[0] is None or len(result[0]) == 0:
                print(f"No text found on page {i+1}")
                continue
            page_text = []
            for line in result[0]:
                text = line[1][0]
                page_text.append(text)
            full_text.append("\n".join(page_text))
        return full_text

    def _pdf_to_text_llm(self, pages) -> list:
        full_text = []
        for i, page in enumerate(pages):
            print(f"Processing page {i+1}/{len(pages)}")
            # Convert PIL image to base64 string
            image_base64 = self._image_to_base64(page)
            # Create the prompt for the LLM and call it
            try:
                response = self.ocr_llm.invoke([
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this image."},
                            {
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        ]
                    }
                ])
                full_text.append(response.content)
            except Exception as e:
                print(f"Error processing page {i+1} with LLM OCR: {e}")
                continue

        return full_text

    def _pdf_to_images(self, pdf_path) -> list:
        # Convert PDF to a list of PIL images
        return convert_from_path(pdf_path, dpi=300)

    def _image_to_base64(self, img) -> str:
        img_np = np.array(img)

        # Ensure 3 channels (RGB)
        print(f"Original shape: {img_np.shape}")
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

        # Force consistent size (CRITICAL)
        img_np = cv2.resize(img_np, (768, 768))

        # Convert to BGR (OpenCV default)
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        # Encode as JPEG (smaller + more stable)
        _, buffer = cv2.imencode(
            ".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        return base64.b64encode(buffer).decode()

    def _improve_text_quality(self, paddle_text: str, llm_text: str) -> str:
        PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Voce é um assistente especializado em extrair texto de documentos médicos.\n"
             "Sua tarefa é analisar e comparar os resultados de extração de texto de dois métodos diferentes (Paddle OCR e LLM OCR) para o mesmo documento,"
             " identificar erros ou discrepâncias, e fornecer uma versão melhorada do texto extraído que combine os pontos fortes de ambos os métodos.\n"
             " Não deixe faltar informações, e não as duplique.\n"
             " Quando sentir que um dos documentos não está tão bem formatado quanto o outro para uma mesma versão, use a melhor formatação como saída.\n"
             " A saída deve ser em formato markdown.\n"
             " O objetivo é obter a versão mais precisa e completa possível do texto extraído do documento, corrigindo quaisquer erros e preenchendo as informações faltantes."),
            ("user", PromptTemplate.from_template(
                "Aqui estão os resultados de extração de texto para um documento médico:\n\n"
                "Texto extraído pelo Paddle OCR:\n{paddle_text}\n\n"
                "Texto extraído pelo LLM OCR:\n{llm_text}\n\n"
                "Por favor, analise ambos os textos, identifique quaisquer erros ou discrepâncias, e forneça uma versão melhorada do texto extraído que combine os pontos fortes de ambos os métodos.\n"
                "Certifique-se de não deixar faltar informações importantes e de não duplicar informações. \n"
                "Use a melhor formatação disponível entre os dois métodos para a saída final. A saída deve ser em formato markdown.\n"
                "NÃO RETORNE QUALQUER EXPLICAÇÃO OU PENSAMENTO, APENAS O TEXTO MELHORADO."
            ).format(paddle_text=paddle_text, llm_text=llm_text))
        ])
        try:
            print("Invoking LLM to improve text quality...")
            response = self.classify_improve_llm.invoke(PROMPT)
            print("LLM response received for text improvement.")
            return response.content
        except Exception as e:
            print(f"Error improving text quality with LLM: {e}")
            # Fallback: return the longer text if there's an error
            return paddle_text if len(paddle_text) > len(llm_text) else llm_text

    def _classify_document(self, text: str) -> str:
        # Placeholder for document classification logic (e.g., using an LLM or a trained classifier)
        PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente especializado em classificar documentos médicos com base em seu conteúdo textual. "
             "Sua tarefa é analisar o texto extraído de um documento médico e determinar a classificação mais apropriada para ele, como 'Relatório Médico', 'Prescrição', 'Laudo de Exame', etc. "
             "Considere as informações presentes no texto, como termos médicos, estrutura do documento e contexto geral para fazer a classificação."),
            ("user", PromptTemplate.from_template(
                "Aqui está o texto extraído de um documento médico:\n\n"
                "{text}\n\n"
                "Por favor, analise o conteúdo do texto e forneça a classificação mais apropriada para este documento (por exemplo, 'Relatório Médico', 'Prescrição', 'Laudo de Exame', etc.).\n"
                "Em sua resposta, forneça apenas a classificação do documento, sem explicações adicionais ou informações extras."
            ).format(text=text))
        ])
        try:
            print("Invoking LLM for document classification...")
            response = self.classify_improve_llm.invoke(PROMPT)
            print("LLM response received for document classification.")
            return response.content.strip()
        except Exception as e:
            print(f"Error classifying document with LLM: {e}")
            return "Classificação Desconhecida"

# endregion
# region External methods
    def classify_documents(self) -> dict:
        """
        Classifies the documents based on their content.

        Returns:
            dict: A dictionary containing the classification results for each document.
        """
        if not self.document_paths:
            print("No documents to process.")
            return {}

        # Process each document in the list of document paths
        documents_output = {}
        for i, document_path in enumerate(self.document_paths):
            # Convert the PDF to images
            print(
                f"Processing document: {document_path} | {i+1} out of {len(self.document_paths)}")
            pages_images = self._pdf_to_images(document_path)
            # Extract text using the Paddle OCR method
            print(
                f"Extracting text from {len(pages_images)} pages with paddle OCR...")
            extracted_pages_paddle = self._pdf_to_text_paddle(pages_images)
            # Extract text using the LLM-based OCR method
            print(
                f"Extracting text from {len(pages_images)} pages with LLM OCR...")
            extracted_pages_llm = self._pdf_to_text_llm(pages_images)
            # Pass the text for each extracted page to the improvement/merger model
            improved_final_extracted_document_pages = []
            for j, (paddle_text, llm_text) in enumerate(zip(extracted_pages_paddle, extracted_pages_llm)):
                print(f"Improving text quality for page {j+1}...")
                improved_text = self._improve_text_quality(
                    paddle_text, llm_text)
                print(
                    f"Final extracted text for page {j+1}:\n{improved_text}\n")
                improved_final_extracted_document_pages.append(improved_text)
            improved_extracted_text = "\n".join(
                improved_final_extracted_document_pages)
            print(
                f"Final extracted text for document {i+1}:\n{improved_extracted_text}\n")
            # Run the classification model on the extracted text to get the document classification
            classification = self._classify_document(improved_extracted_text)
            # Create the output dictionary for the current document
            document_name = document_path.split("/")[-1]
            documents_output[document_name] = {
                "classification": classification,
                "extracted_text": improved_final_extracted_document_pages,
                "original_path": document_path
            }

        return documents_output

# endregion


def main():
    # Example usage of the MedicalDocsOCR class
    ocr = MedicalDocsOCR()
    # Set the documents to process (replace with actual paths)
    ocr.set_documents_to_process(
        ["/home/vini/Desktop/5g_medical_docs/trials/20251127_102005_cardiologia.pdf"])
    # Classify the documents
    ocr.classify_documents()


if __name__ == "__main__":
    main()
