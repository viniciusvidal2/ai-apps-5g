import pdfplumber
import fitz  # PyMuPDF
import io
from PIL import Image
import ollama


class PdfLookup:
    def __init__(self) -> None:
        """Initializes a PdfLookup object to handle PDF extraction and processing.
        """
        self.pdf_path = None
        self.pdf_text = None
        self.pdf_images_info = None
        self.pdf_data_prompt = None

    def set_pdf_path(self, path: str) -> None:
        """Sets the path to the PDF file to be processed.

        Args:
            path (str): The file path to the PDF document.
        """
        self.pdf_path = path

    def load_pdf(self) -> None:
        """Loads the PDF file, extracts text and images, and prepares the data for inference.
        """
        if not self.pdf_path:
            raise ValueError("PDF path is not set.")
        # Load the PDF text using the plumber library
        self.pdf_text = ""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n{text}"
                else:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n[No text found]"
        # Load the PDF images using the fitz library (PyMuPDF)
        doc = fitz.open(self.pdf_path)
        self.pdf_images_info = []
        for page_num, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
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
        self.pdf_lookup.set_pdf_path(path)

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
        if not self.pdf_lookup.pdf_path:
            raise ValueError("PDF path is not set.")
        # Load the PDF and build the data prompt
        print("Loading PDF and building data prompt...")
        self.pdf_lookup.load_pdf()
        self.pdf_lookup.build_pdf_data_prompt()
        # Get the PDF data prompt
        pdf_data_prompts = self.pdf_lookup.get_pdf_data_prompts()
        # Use the Ollama API to run inference with the PDF data and the inference prompt
        print("Running inference with Ollama API...")
        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": "Colocarei no proximo prompt o conteudo de um PDF, somente a parte textual"},
                {"role": "user", "content": pdf_data_prompts["text"]},
                {"role": "system", "content": "Colocarei no proximo prompt o conteudo do mesmo PDF, somente a parte de imagens"},
                {"role": "user", "content": pdf_data_prompts["images"]},
                {"role": "system", "content": "Agora, por favor, responda a pergunta abaixo com base no conteudo do PDF"},
                {"role": "user", "content": self.inference_prompt},
            ]
        )
        return response['message']['content']


if __name__ == "__main__":
    # Example usage
    pdf_inference = PdfInference()
    pdf_inference.set_pdf_path("/home/grin/Downloads/boleto.pdf")
    query_prompt = "Qual o valor final deste boleto? Qual a data de vencimento?"
    pdf_inference.set_inference_prompt(query_prompt)
    result = pdf_inference.run_inference()
    # Print the result from the LLM
    print(f"\nQuery Prompt: {query_prompt}")
    print("\n=== LLM Response ===\n")
    print(result)
