import pdfplumber
import fitz  # PyMuPDF
import io
from PIL import Image
import ollama
import os
import time


class PdfLookup:
    def __init__(self) -> None:
        """Initializes a PdfLookup object to handle PDF extraction and processing.
        """
        self.pdf_text = None
        self.pdf_images_info = None
        self.pdf_data_prompt = None
        self.pdf_bytes = None

    def set_pdf_bytes(self, pdf_bytes: bytes) -> None:
        """Sets the PDF file content as bytes to be processed.

        Args:
            pdf_bytes (bytes): The byte content of the PDF document.
        """
        self.pdf_bytes = pdf_bytes

    def load_pdf(self) -> None:
        """Loads the PDF file, extracts text and images, and prepares the data for inference.
        """
        if not self.pdf_bytes:
            raise ValueError(
                "PDF bytes are not set. Please set the PDF bytes before loading.")
        self.pdf_stream = io.BytesIO(self.pdf_bytes)
        self.pdf_stream.seek(0)
        # Load the PDF text using the plumber library
        self.pdf_text = ""
        with pdfplumber.open(self.pdf_stream) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n{text}"
                else:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n[No text found]"
        # Load the PDF images using the fitz library (PyMuPDF)
        self.pdf_stream.seek(0)  # Reset the stream position
        doc = fitz.open(stream=self.pdf_stream, filetype="pdf")
        self.pdf_images_info = []
        for page_num, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            for _, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                # Add the image information to the list
                self.pdf_images_info.append({
                    "page": page_num,
                    "image": image
                })

    def build_pdf_data_prompt(self) -> None:
        """Builds a prompt containing the extracted text and image information from the PDF.
        """
        self.pdf_data_prompt = {"text": "", "images": ""}
        self.pdf_data_prompt["text"] += "### Conteudo TEXTUAL do PDF:\n\n"
        self.pdf_data_prompt["text"] += self.pdf_text
        if self.pdf_images_info:
            self.pdf_data_prompt["images"] += "\n\n### Conteudo de IMAGEM do PDF:\n"
            for img_info in self.pdf_images_info:
                self.pdf_data_prompt["images"] += f"- Pagina {img_info['page']}\n"
        else:
            self.pdf_data_prompt += "\n\n(Nao ha IMAGEM no PDF)\n"

    def get_pdf_data_prompts(self) -> dict:
        """Returns the PDF data prompt containing the extracted text and image information.

        Returns:
            dict: The prompt containing the PDF ('text' and 'images', both as strings).
        """
        if self.pdf_data_prompt is None:
            # Call the method to build the prompt if it hasn't been built yet
            self.build_pdf_data_prompt()
        return self.pdf_data_prompt


class PdfInference:
    """Handles PDF inference tasks using the Ollama API.
    This class will test the PDF inference capabilities by extracting text and images from a PDF document,
    and then using the Ollama API to run inference based on the extracted data.
    """

    def __init__(self) -> None:
        """Initializes a PdfInference object to handle PDF inference tasks.
        """
        self.pdf_lookup = PdfLookup()

    def set_pdf_path(self, path: str) -> None:
        """Sets the path to the PDF file for inference.

        Args:
            path (str): The file path to the PDF document.
        """
        # Read the pdf into bytes
        try:
            with open(path, "rb") as pdf_file:
                self.pdf_lookup.set_pdf_bytes(pdf_file.read())
        except FileNotFoundError:
            raise ValueError(f"PDF file not found at path: {path}")
        except Exception as e:
            raise ValueError(
                f"An error occurred while reading the PDF file: {e}")

    def set_inference_prompt(self, prompt: str) -> None:
        """Sets the inference prompt to be used with the PDF data.

        Args:
            prompt (str): The prompt to be used for inference.
        """
        self.inference_prompt = prompt

    def run_inference(self) -> str:
        """Runs the inference using the PDF data and the provided prompt.

        Returns:
            str: The response from the LLM after processing the PDF data and inference prompt.
        """
        # Load the PDF and build the data prompt
        print("Loading PDF and building data prompt...")
        self.pdf_lookup.load_pdf()
        self.pdf_lookup.build_pdf_data_prompt()
        # Get the PDF data prompt
        pdf_data_prompts = self.pdf_lookup.get_pdf_data_prompts()
        # Use the Ollama API to run inference with the PDF data and the inference prompt
        print("Running inference with Ollama API...")
        formated_prompt = f"""
        Instrucao: A seguir, voce recebera o conteudo de um PDF dividido em duas partes: texto e imagens.
        A primeira parte contem o texto do PDF, e a segunda parte contem as imagens do PDF.
        Sua tarefa e analisar o conteudo do PDF e responder a pergunta que sera feita a seguir
        com base no conteudo do PDF.
        Texto do PDF:
        {pdf_data_prompts["text"]}
        Imagens do PDF:
        {pdf_data_prompts["images"]}
        Pergunta: {self.inference_prompt}
        Resposta:
        """
        response = ollama.chat(
            model="deepseek-r1:70b",
            messages=[
                {"role": "system", "content": "Voce e um assintente de IA especializado em analise de documentos PDF."},
                {"role": "user", "content": formated_prompt},
            ]
        )
        # Remove everything from the think process
        answer = response['message']['content']
        think_end_section = "</think>"
        if think_end_section in response['message']['content']:
            answer = response['message']['content'].split(
                think_end_section)[-1].strip()
        return answer


if __name__ == "__main__":
    os.environ["OLLAMA_ACCELERATE"] = "gpu"
    # Example usage
    pdf_inference = PdfInference()
    pdf_inference.set_pdf_path("/home/vini/Downloads/manual_corolla.pdf")
    # query_prompts = [
    #     "Quais passos sao de responsabilidade de daiana santos?",
    #     "Quais passos sao de responsabilidade de INFRA-SPO?",
    #     "Me fale quantos passos ha no plano de atualizacao?",
    #     "Qual a data de emissao do plano de atualizacao?",
    #     "Qual o prazo de execucao do plano de atualizacao, somando as duracoes de cada passo?",
    #     "Faca um resumo tecnico das descricoes das atividades"
    # ]
    query_prompts = [
        "Me diga as regras para condutores profissionais.",
        "Faça um resumo do anexo do código brasileiro de trânsito, com os pontos mais críticos.",
        "Quais as principais funcionalidades dos pneus?",
        "Quais são as obrigações do condutor profissional?",
    ]
    for query_prompt in query_prompts:
        print("\n\n---------------------------------------------------------\n\n")
        start_t = time.time()
        pdf_inference.set_inference_prompt(query_prompt)
        result = pdf_inference.run_inference()
        # Print the result from the LLM
        print(f"\nQuery Prompt: {query_prompt}")
        print("\n=== LLM Response ===\n")
        print(result)
        end_t = time.time()
        print(f"\nTime taken for inference: {end_t - start_t:.2f} seconds")
