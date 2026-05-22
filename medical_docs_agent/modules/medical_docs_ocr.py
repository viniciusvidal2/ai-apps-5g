import os


# MUST come before importing paddle/paddleocr
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_enable_pir_in_executor"] = "0"
os.environ["FLAGS_use_pir_api"] = "0"
os.environ["FLAGS_use_cinn"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

# Optional but helps
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import paddle
paddle.enable_static()

from paddleocr import PaddleOCR
from pdf2image import convert_from_path
from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import numpy as np
import cv2
import base64
import yaml
import shutil
import logging
import threading
import time
try:
    from report_generator import generate_evaluation_report
except ImportError:
    from .report_generator import generate_evaluation_report

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
        if not "unclassified" in self.document_classes:
            self.document_classes.append("unclassified")
        ClassificationEnum = Enum(
            "ClassificationEnum",
            {c: c for c in self.document_classes}
        )
        # OCR model initialization
        self.ocr_paddle_basic = PaddleOCR(use_doc_orientation_classify=True,
                                          use_doc_unwarping=False,
                                          use_textline_orientation=True,
                                          lang="en",
                                          enable_mkldnn=False,
                                          device="cpu")
        # OCR using LLM model from ollama with langchain
        self.ocr_llm = ChatOllama(model="glm-ocr:latest",
                                  base_url="http://localhost:11434",
                                  debug=False)
        # Default OCR method
        self.ocr_method = "paddle"  # options: "paddle", "llm"
        # Document classification model from ollama with langchain
        self.classifier_llm = ChatOllama(model="gemma4:latest",
                                         base_url="http://localhost:11434",
                                         debug=False)
        # Status and results for threaded execution
        self.status = "idle"
        self.results = {}
        # Chain: classify a document into one of the configured document classes
        self.CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente especializado em classificar documentos médicos com base em seu conteúdo textual.\n"
             "Sua tarefa é analisar o texto extraído de um documento médico e determinar a classificação mais apropriada para ele.\n"
             " IMPORTANTE: SE ATENHA SOMENTE AS CLASSES DESCRITAS ABAIXO PONTUADAS, ENTRE O TRECHO TRACEJADO. CASO NAO CONSIDERE QUE SEJA NENHUMA DAS CLASSES, CLASSIFIQUE COMO 'unclassified'.\n"
             "{classes_list}"
             "\nConsidere as informações presentes no texto, como termos médicos, estrutura do documento e contexto geral para fazer a classificação."),
            ("user",
             "Aqui está o texto extraído de um documento médico:\n\n"
             "{text}\n\n"
             "Por favor, analise o conteúdo do texto e forneça as classificações mais apropriadas para este documento usando a ferramenta fornecida, respeitando as classes:\n"
             "{classes_list}"
             )
        ])
        
        self.ClassificationEnum = ClassificationEnum
        
        class ClassificationOutput(BaseModel):
            classifications: List[ClassificationEnum] = Field(
                description="List of classifications"
            )
        self.ClassificationOutput = ClassificationOutput
        
        structured_llm = self.classifier_llm.with_structured_output(self.ClassificationOutput)
        self.classify_chain = self.CLASSIFY_PROMPT | structured_llm
        
        # Chain: improve the document text
        self.IMPROVE_PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Você é um assistente especializado em limpar e aprimorar textos extraídos de documentos médicos via OCR.\n"
             "Sua tarefa é analisar o texto extraído, remover qualquer seção que pareça lixo, ruído de leitura de imagem, ou excesso de campos de exames vazios e repetitivos.\n"
             "Preserve apenas as informações textuais relevantes, cabeçalhos úteis, diagnósticos, observações clínicas, e termos médicos importantes que ajudem a identificar claramente a especialidade ou classe do documento.\n"
             "Retorne apenas o texto limpo e aprimorado, sem introduções ou explicações adicionais."),
            ("user", "Aqui está o texto bruto extraído do documento médico:\n\n{text}")
        ])
        self.improve_chain = self.IMPROVE_PROMPT | self.classifier_llm


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

    def set_ocr_method(self, method: str) -> None:
        """
        Sets the OCR method to be used.

        Args:
            method (str): The OCR method to use. Either "paddle" or "llm".
        """
        if method not in ["paddle", "llm"]:
            raise ValueError("Invalid OCR method. Use 'paddle' or 'llm'.")
        self.ocr_method = method

    def set_classification_model(self, model_name: str) -> None:
        """
        Sets the LLM model to be used for document classification.

        Args:
            model_name (str): The name of the LLM model to use for classification.
                This should correspond to a model available in the Ollama server.
        """
        self.classifier_llm = ChatOllama(model=model_name,
                                         base_url="http://localhost:11434",
                                         debug=False)
        structured_llm = self.classifier_llm.with_structured_output(self.ClassificationOutput)
        self.classify_chain = self.CLASSIFY_PROMPT | structured_llm
        self.improve_chain = self.IMPROVE_PROMPT | self.classifier_llm

    def get_status(self) -> str:
        """
        Returns the current status of the OCR and classification pipeline.

        Returns:
            str: The current status ("idle", "running", "completed", "failed").
        """
        return self.status

    def get_results(self) -> dict:
        """
        Returns the classification results.

        Returns:
            dict: The classification results.
        """
        return self.results

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
            return [doc_class["name"].lower() for doc_class in document_classes]

    def _pdf_to_text_paddle(self, images: list, type: str) -> list:
        """
        Extracts text from a list of page images using PaddleOCR.

        Args:
            images (list): A list of PIL Image objects representing document pages.
            type (str): The type of OCR to use. Either "paddle_vl" for the PaddleOCRVL model or "paddle_basic" for the basic PaddleOCR model.

        Returns:
            list: A list of strings, each containing the extracted text from one page.
        """
        pages = []
        for i, img in enumerate(images):
            print(
                f"Processing page {i+1}/{len(images)} with Paddle OCR ({type})...")
            if type == "paddle_vl":
                # ocr_result = self.ocr_paddle_vl.predict(input=img)
                # pages_res = list(ocr_result)
                # output = self.ocr_paddle_vl.restructure_pages(pages_res)
                # pages.extend([page.markdown["markdown_texts"] for page in output])
                pass
            elif type == "paddle_basic":
                ocr_result = self.ocr_paddle_basic.predict(img)
                texts = ocr_result[0]['rec_texts']  # recognized text strings
                pages.append("\n".join(texts) + "\n\n")
            else:
                raise ValueError(
                    "Invalid OCR type specified. Use 'paddle_vl' or 'paddle_basic'.")
        return pages

    def _pdf_to_text_llm(self, pages: list) -> list:
        """
        Extracts text from a list of page images using the LLM-based OCR model.

        Args:
            pages (list): A list of PIL Image objects representing document pages.

        Returns:
            list: A list of strings, each containing the extracted text from one page.
        """
        retrieved_pages = []
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
                retrieved_pages.append(response.content)
            except Exception as e:
                print(f"Error processing page {i+1} with LLM OCR: {e}")
                continue
        return retrieved_pages

    def _pdf_to_images(self, pdf_path: str) -> list:
        """
        Converts a PDF file into a list of numpy arrays, one per page.

        Args:
            pdf_path (str): Path to the PDF file to convert.

        Returns:
            list: A list of numpy arrays representing each page of the PDF.
        """
        # Convert PDF to a list of PIL images
        images_pil = convert_from_path(pdf_path, dpi=150)
        # Convert PIL images to numpy arrays
        images_np = [np.array(img) for img in images_pil]
        return images_np

    def _image_to_base64(self, img: np.ndarray) -> str:
        """
        Converts a NumPy array representing an image to a base64-encoded JPEG string suitable for LLM API calls.

        Args:
            img: A NumPy array representing the image to encode.

        Returns:
            str: A base64-encoded string of the image in JPEG format.
        """
        img_np = img.copy() if isinstance(img, np.ndarray) else np.array(img)
        # Ensure 3 channels (RGB)
        if len(img_np.shape) == 2:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)
        # Force consistent, reduced size
        img_np = cv2.resize(img_np, None, fx=0.5, fy=0.5,
                            interpolation=cv2.INTER_AREA)
        # Convert to BGR
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        # Encode as JPEG (smaller + more stable)
        _, buffer = cv2.imencode(
            ".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        return base64.b64encode(buffer).decode()

    def _classify_document(self, document_text: str) -> str:
        """
        Classifies a medical document based on its extracted text content.

        Uses an LLM to analyse the document text and match it to one of the
        configured document classes. Returns 'unclassified' if no class matches or
        if the LLM call fails.

        Args:
            document_text (str): The full extracted text of the document to classify.

        Returns:
            str: The matched document class name, or 'unclassified' if unclassified.
        """
        classes_list = "-" * 50 + "\n" + "".join(
            [f"- {doc_class}\n" for doc_class in self.document_classes]) + "-" * 50 + "\n"
        try:
            print("Invoking LLM for document classification...")
            response = self.classify_chain.invoke(
                {"text": document_text, "classes_list": classes_list})
            classification_value = response.classifications[0].value if response.classifications else "unclassified"
            print(f"LLM classification result: {classification_value}")
            return classification_value
        except Exception as e:
            print(f"Error classifying document with LLM: {e}")
            return "unclassified"

    def _write_md_version(self, text: str, output_path: str) -> None:
        """
        Writes the provided text content to a markdown file at the specified path.

        Args:
            text (str): The text content to write to the file.
            output_path (str): The full file path where the markdown file will be saved.
        """
        # Write the improved text to a markdown file
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(text)

# endregion
# region External methods
    def classify_documents(self) -> None:
        """
        Starts the classification process in a separate thread.
        Sets the status to 'running'.
        """
        if not self.document_paths:
            print("No documents to process.")
            self.status = "idle"
            return

        self.status = "running"
        self.results = {}
        
        # Start the worker thread
        worker_thread = threading.Thread(target=self._run_classification_worker)
        worker_thread.start()
        print("Classification worker started in a separate thread.")

    def _run_classification_worker(self) -> None:
        """
        The actual worker function that runs the OCR and classification pipeline.
        Updates self.status and self.results upon completion or failure.
        """
        try:
            total_start_time = time.time()
            # Process each document in the list of document paths
            documents_output = {}
            for i, document_path in enumerate(self.document_paths):
                print(
                    f"Processing document: {document_path} | {i+1} out of {len(self.document_paths)}")
                
                doc_start_time = time.time()
                
                # Convert the PDF to images
                pages_images = self._pdf_to_images(document_path)

                extracted_text = ""
                if self.ocr_method == "paddle":
                    print(
                        f"Extracting text from {len(pages_images)} pages with paddle OCR...")
                    extracted_pages = self._pdf_to_text_paddle(
                        pages_images, type="paddle_basic")
                    extracted_text = "\n".join(extracted_pages)
                elif self.ocr_method == "llm":
                    print(
                        f"Extracting text from {len(pages_images)} pages with LLM OCR...")
                    extracted_pages = self._pdf_to_text_llm(pages_images)
                    extracted_text = "\n".join(extracted_pages)

                # Run the classification model, improving text iteratively up to 3 times if unclassified
                current_text = extracted_text
                classification = "unclassified"
                
                for attempt in range(3):
                    print(f"Classification attempt {attempt + 1}/3...")
                    classification = self._classify_document(current_text)
                    
                    if classification != "unclassified":
                        # Found a valid class, stop iterating
                        break
                        
                    if attempt < 2:
                        print("Document was unclassified. Invoking LLM to improve text quality and remove noise...")
                        try:
                            response = self.improve_chain.invoke({"text": current_text})
                            improved_text = response.content if hasattr(response, "content") else str(response)
                            if improved_text.strip():
                                current_text = improved_text
                            else:
                                print("Improved text was empty. Retaining previous text version.")
                        except Exception as e:
                            print(f"Error improving text with LLM: {e}")

                doc_end_time = time.time()
                doc_elapsed_time = doc_end_time - doc_start_time

                # Extract ground truth from the document name
                # (last part of name, after '_' and before '.pdf')
                document_name = document_path.split("/")[-1]
                name_without_ext = os.path.splitext(document_name)[0]
                ground_truth = name_without_ext.split("_")[-1].lower()

                # Create the output dictionary for the current document
                documents_output[document_name] = {
                    "classification": classification,
                    "extracted_text": current_text,
                    "original_path": document_path,
                    "ground_truth": ground_truth,
                    "time_taken": doc_elapsed_time,
                    "pages": len(pages_images)
                }

            total_elapsed_time = time.time() - total_start_time

            # Generate the evaluation report at the end of the execution
            generate_evaluation_report(
                documents_output=documents_output,
                total_elapsed_time=total_elapsed_time,
                document_classes=self.document_classes,
                output_folder=self.output_folder
            )

            self.results = documents_output
            self.status = "completed"
            print("Classification worker finished successfully.")
        except Exception as e:
            print(f"Classification worker failed: {e}")
            self.status = "failed"

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
            if classification in self.document_classes and classification != "unknown":
                destination_folder = os.path.join(
                    self.output_folder, classification)
            else:
                destination_folder = unknown_class_folder
            destination_path = os.path.join(destination_folder, document_name)
            shutil.copy2(original_path, destination_path)
            # Also save the extracted text in markdown format in the same folder
            md_output_path = os.path.join(
                destination_folder, document_name.replace(".pdf", ".md"))
            self._write_md_version(
                output_path=md_output_path, text=info["extracted_text"])

# endregion
# region Main execution


def main() -> None:
    """Entry point demonstrating example usage of the MedicalDocsOCR pipeline."""
    # Example usage of the MedicalDocsOCR class
    ocr = MedicalDocsOCR(data_yaml_path=os.getenv(
        "HOME") + "/ai-apps-5g/medical_docs_agent/modules/data.yaml")

    # Set OCR method (optional, default is "paddle")
    ocr.set_ocr_method("llm")

    # Set the documents to process (replace with actual paths)
    ocr.set_documents_to_process([
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_103128_cardiologia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_100732_cardiologia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_101002_cardiologia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_101120_odontologico.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_101320_ergonomia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_101607_fisioterapia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_101814_pulmonar_eletroencefalograma_psicosocial.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102005_cardiologia.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102059_hemograma_psicosocial.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102150_psicosocial.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102216_eletroencefalograma.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102651_eletroencefalograma.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_102937_psicosocial.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_103103_pulmonar.pdf",
        "/home/vini/Desktop/5g_medical_docs/trials/20251127_103128_cardiologia.pdf",
    ])
    ocr.set_output_folder(
        "/home/vini/Desktop/5g_medical_docs/trials/classified_docs")

    # Classify the documents
    ocr.classify_documents()
    
    # Wait for the classification to finish
    import time
    while ocr.get_status() == "running":
        print(f"Waiting for classification... Status: {ocr.get_status()}")
        time.sleep(2)
    
    if ocr.get_status() == "completed":
        # Organize the documents in folders according to their classes
        ocr.organize_documents(ocr.get_results())
    else:
        print(f"Classification failed with status: {ocr.get_status()}")


if __name__ == "__main__":
    main()

# endregion
