import cv2
from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import numpy as np
import base64
import os
import yaml
import shutil
import logging

logging.getLogger("ppocr").setLevel(logging.WARNING)


class MedicalDocsOCR:
    def __init__(self, data_yaml_path: str) -> None:
        """
        Initializes the MedicalDocsOCR agent with OCR and classification capabilities.

        Args:
            data_yaml_path (str): Path to the YAML configuration file containing
                the document class definitions.
        """
        # Documents to be converted
        self.document_paths = []
        # Output folder for saving classified documents
        self.output_folder = ""
        # Classes to classify the objects
        self.document_classes = self._read_yaml_into_classes(data_yaml_path)
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
        """
        Sets the list of document paths to be processed by the OCR pipeline.

        Args:
            document_paths (list): A list of file paths to the PDF documents to process.
        """
        # Store the document paths for processing
        self.document_paths = document_paths

    def set_output_folder(self, output_folder: str) -> None:
        """
        Sets the output folder where classified documents will be saved.

        Args:
            output_folder (str): Path to the directory where classified documents
                and their extracted text files will be written.
        """
        # Store the output folder path for saving classified documents
        self.output_folder = output_folder

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

    def _read_yaml_into_classes(self, yaml_path: str) -> list:
        """
        Reads the YAML configuration file and extracts the document class names.

        Args:
            yaml_path (str): Path to the YAML file containing document class definitions.

        Returns:
            list: A list of document class name strings.
        """
        # Read the yaml file and extract the document classes
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)
            document_classes = data.get("document_classes", [])
            return [doc_class["name"] for doc_class in document_classes]

    def _pdf_to_text_paddle(self, pages: list) -> list:
        """
        Extracts text from a list of page images using PaddleOCR.

        Args:
            pages (list): A list of PIL Image objects representing document pages.

        Returns:
            list: A list of strings, each containing the extracted text from one page.
        """
        full_text = []
        for i, page in enumerate(pages):
            print(f"Processing page {i+1}/{len(pages)}")
            # Convert PIL image to numpy array and predict text using Paddle OCR
            image = np.array(page)
            result = self.ocr_paddle.ocr(image)
            if result[0] is None or len(result[0]) == 0:
                print(f"No text found on page {i+1}")
                continue
            page_text = []
            for line in result[0]:
                text = line[1][0]
                page_text.append(text)
            full_text.append("\n".join(page_text))
        return full_text

    def _pdf_to_text_llm(self, pages: list) -> list:
        """
        Extracts text from a list of page images using the LLM-based OCR model.

        Args:
            pages (list): A list of PIL Image objects representing document pages.

        Returns:
            list: A list of strings, each containing the extracted text from one page.
        """
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

    def _pdf_to_images(self, pdf_path: str) -> list:
        """
        Converts a PDF file into a list of PIL Image objects, one per page.

        Args:
            pdf_path (str): Path to the PDF file to convert.

        Returns:
            list: A list of PIL Image objects representing each page of the PDF.
        """
        # Convert PDF to a list of PIL images
        return convert_from_path(pdf_path, dpi=300)

    def _image_to_base64(self, img) -> str:
        """
        Converts a PIL Image to a base64-encoded JPEG string suitable for LLM API calls.

        Args:
            img: A PIL Image object to encode.

        Returns:
            str: A base64-encoded string of the image in JPEG format.
        """
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
        """
        Uses an LLM to merge and improve the text extracted by PaddleOCR and the LLM OCR.

        Compares both extraction results, identifies discrepancies, and produces a
        combined, higher-quality markdown version of the document text.

        Args:
            paddle_text (str): Text extracted by the PaddleOCR method.
            llm_text (str): Text extracted by the LLM-based OCR method.

        Returns:
            str: The improved, merged text in markdown format. Falls back to the
                longer of the two inputs if the LLM call fails.
        """
        PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Voce é um assistente especializado em extrair texto de documentos médicos.\n"
             "Sua tarefa é analisar e comparar os resultados de extração de texto de dois métodos diferentes (Paddle OCR e LLM OCR) para o mesmo documento,"
             " identificar erros ou discrepâncias, e fornecer uma versão melhorada do texto extraído que combine os pontos fortes de ambos os métodos.\n"
             " Não deixe faltar informações, e não as duplique.\n"
             " Quando sentir que um dos documentos não está tão bem formatado quanto o outro para uma mesma versão, use a melhor formatação como saída.\n"
             " A saída deve ser em formato markdown.\n"
             " O objetivo é obter a versão mais precisa e completa possível do texto extraído do documento, corrigindo quaisquer erros e preenchendo as informações faltantes."),
            ("user",
             "Aqui estão os resultados de extração de texto para um documento médico:\n\n"
             "Texto extraído pelo Paddle OCR:\n{paddle_text}\n\n"
             "Texto extraído pelo LLM OCR:\n{llm_text}\n\n"
             "Por favor, analise ambos os textos, identifique quaisquer erros ou discrepâncias, e forneça uma versão melhorada do texto extraído que combine os pontos fortes de ambos os métodos.\n"
             "Certifique-se de não deixar faltar informações importantes e de não duplicar informações. \n"
             "Use a melhor formatação disponível entre os dois métodos para a saída final. A saída deve ser em formato markdown.\n"
             "NÃO RETORNE QUALQUER EXPLICAÇÃO OU PENSAMENTO, APENAS O TEXTO MELHORADO."
             )
        ])
        chain = PROMPT | self.classify_improve_llm
        try:
            print("Invoking LLM to improve text quality...")
            response = chain.invoke({
                "paddle_text": paddle_text,
                "llm_text": llm_text
            })
            print("LLM response received for text improvement.")
            return response.content
        except Exception as e:
            print(f"Error improving text quality with LLM: {e}")
            # Fallback: return the longer text if there's an error
            return paddle_text if len(paddle_text) > len(llm_text) else llm_text

    def _classify_document(self, document_text: str) -> str:
        """
        Classifies a medical document based on its extracted text content.

        Uses an LLM to analyse the document text and match it to one of the
        configured document classes. Returns 'unknown' if no class matches or
        if the LLM call fails.

        Args:
            document_text (str): The full extracted text of the document to classify.

        Returns:
            str: The matched document class name, or 'unknown' if unclassified.
        """
        classes_prompt_section = "".join(
            [f"- {doc_class}\n" for doc_class in self.document_classes])
        # Placeholder for document classification logic (e.g., using an LLM or a trained classifier)
        PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente especializado em classificar documentos médicos com base em seu conteúdo textual.\n"
             "Sua tarefa é analisar o texto extraído de um documento médico e determinar a classificação mais apropriada para ele.\n"
             " IMPORTANTE: SE ATENHA SOMENTE AS CLASSES DESCRITAS ABAIXO PONTUADAS, ENTRE O TRECHO TRACEJADO. CASO NAO CONSIDERE QUE SEJA NENHUMA DAS CLASSES, RESPONDA COM 'unknown'.\n" +
             "-" * 50 + "\n" + classes_prompt_section + "-" * 50 + "\n"
             "\nConsidere as informações presentes no texto, como termos médicos, estrutura do documento e contexto geral para fazer a classificação."),
            ("user",
             "Aqui está o texto extraído de um documento médico:\n\n"
             "{text}\n\n"
             "Por favor, analise o conteúdo do texto e forneça a classificação mais apropriada para este documento, respeitando as classes:\n"
             "{classes}\n"
             "Em sua resposta, forneça apenas a classificação do documento, sem explicações adicionais ou informações extras."
             )
        ])
        chain = PROMPT | self.classify_improve_llm
        try:
            print("Invoking LLM for document classification...")
            response = chain.invoke(
                {"text": document_text, "classes": classes_prompt_section})
            print(
                f"LLM response received for document classification: {response.content}")
            for document_class in self.document_classes:
                if document_class.lower() in response.content.lower():
                    return document_class
            return "unknown"
        except Exception as e:
            print(f"Error classifying document with LLM: {e}")
            return "unknown"

    def _write_md_version(self, text: str, output_path: str) -> None:
        """
        Writes the provided text content to a markdown file at the specified path.

        Args:
            text (str): The text content to write to the file.
            output_path (str): The full file path where the markdown file will be saved.
        """
        # Write the improved text to a markdown file
        with open(output_path, "w") as file:
            file.write(text)

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
                improved_final_extracted_document_pages.append(improved_text)
            improved_extracted_text = "\n".join(
                improved_final_extracted_document_pages)
            # Run the classification model on the extracted text to get the document classification
            classification = self._classify_document(improved_extracted_text)
            # Create the output dictionary for the current document
            document_name = document_path.split("/")[-1]
            documents_output[document_name] = {
                "classification": classification,
                "extracted_text": improved_extracted_text,
                "paddle_text": "\n".join(extracted_pages_paddle),
                "llm_text": "\n".join(extracted_pages_llm),
                "original_path": document_path
            }

        return documents_output

    def organize_documents(self, classified_documents: dict) -> None:
        """
        Organizes classified documents into subfolders based on their classification.

        Creates a subfolder for each document class under the configured output folder,
        copies each original PDF to the appropriate subfolder, and writes the extracted
        text (paddle, LLM, and improved versions) as separate markdown files alongside it.
        Unclassified documents are placed in an 'unclassified' subfolder.

        Args:
            classified_documents (dict): A dictionary mapping document names to their
                classification results and extracted text, as returned by
                :meth:`classify_documents`.
        """
        # Create the subfolders for each class, if they are not there already
        print("Organizing documents into folders based on classification...")
        for document_class in self.document_classes:
            class_folder = os.path.join(
                self.output_folder, document_class)
            if not os.path.exists(class_folder):
                os.makedirs(class_folder)
        # Create a subfolder for unclassified documents, if it doesn't exist
        unknown_class_folder = os.path.join(
            self.output_folder, "unclassified")
        if not os.path.exists(unknown_class_folder):
            os.makedirs(unknown_class_folder)

        # Move the documents to the respective folders according to their classification
        print("Moving documents to respective folders...")
        for document_name, info in classified_documents.items():
            classification = info["classification"]
            original_path = info["original_path"]
            print(
                f"Document: {document_name} | Classification: {classification}")
            if classification in self.document_classes:
                destination_folder = os.path.join(
                    self.output_folder, classification)
            else:
                destination_folder = unknown_class_folder
            destination_path = os.path.join(destination_folder, document_name)
            shutil.copy2(original_path, destination_path)
            # Also save the extracted text in markdown format in the same folder
            md_paths_content = [
                (os.path.join(destination_folder, document_name.replace(
                    ".pdf", "_paddle.md")), info["paddle_text"]),
                (os.path.join(destination_folder, document_name.replace(
                    ".pdf", "_llm.md")), info["llm_text"]),
                (os.path.join(destination_folder, document_name.replace(
                    ".pdf", ".md")), info["extracted_text"]),
            ]
            for md_output_path, md_content in md_paths_content:
                self._write_md_version(
                    output_path=md_output_path, text=md_content)

# endregion
# region Main execution


def main() -> None:
    """Entry point demonstrating example usage of the MedicalDocsOCR pipeline."""
    # Example usage of the MedicalDocsOCR class
    ocr = MedicalDocsOCR(data_yaml_path=os.getenv(
        "HOME") + "/ai-apps-5g/medical_docs_agent/modules/data.yaml")
    # Set the documents to process (replace with actual paths)
    ocr.set_documents_to_process([
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_103128_cardiologia.pdf",
        # "/home/vini/Desktop/5g_medical_docs/trials/20251127_101607_fisioterapia.pdf",
        #"/home/vini/Desktop/5g_medical_docs/trials/20251127_102005_cardiologia.pdf",
        # "/home/vini/Desktop/5g_medical_docs/trials/20251127_102216_eletroencefalograma.pdf",
        #"/home/vini/Desktop/5g_medical_docs/trials/20251127_102651_eletroencefalograma.pdf",
        # "/home/vini/Desktop/5g_medical_docs/trials/20251127_102937_psicosocial.pdf",
    ])
    ocr.set_output_folder(
        "/home/vini/Desktop/5g_medical_docs/trials/classified_docs")
    # Classify the documents
    classified_documents = ocr.classify_documents()
    # Organize the documents in folders according to their classes
    ocr.organize_documents(classified_documents)


if __name__ == "__main__":
    main()

# endregion
