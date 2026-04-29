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
        # OCR using LLM model from ollama with langgraph
        self.ocr_llm = ChatOllama(model="glm-ocr:latest",
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

    def _pdf_to_text_paddle(self, pages) -> str:
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
        return "\n\n".join(full_text)

    def _pdf_to_text_llm(self, pages) -> str:
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

        return "\n\n".join(full_text)

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
        _, buffer = cv2.imencode(".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

        return base64.b64encode(buffer).decode()

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
        for i, document_path in enumerate(self.document_paths):
            # Convert the PDF to images
            print(
                f"Processing document: {document_path} | {i+1} out of {len(self.document_paths)}")
            pages = self._pdf_to_images(document_path)
            # Extract text using the Paddle OCR method
            print(
                f"Extracting text from {len(pages)} pages with paddle OCR...")
            # extracted_text_paddle = self._pdf_to_text_paddle(pages)
            # print(
            #     f"Extracted text using Paddle OCR:\n{extracted_text_paddle}\n")
            # Extract text using the LLM-based OCR method
            print(f"Extracting text from {len(pages)} pages with LLM OCR...")
            extracted_text_llm = self._pdf_to_text_llm(pages)
            print(f"Extracted text using LLM OCR:\n{extracted_text_llm}\n")
            # response = requests.post(
            #     "http://localhost:11434/api/generate",
            #     json={
            #         "model": "glm-ocr:latest",
            #         "prompt": "Extract all text from this image.",
            #         "images": [self._image_to_base64(pages[0])],
            #         "stream": False
            #     }
            # )
            # print(response.json()["response"])

        return {}

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
