import pdfplumber
import fitz  # PyMuPDF
import io
from PIL import Image
import ollama


class PdfLookup:
    def __init__(self):
        self.pdf_path = None
        self.pdf_text = None
        self.pdf_images_info = None
        self.pdf_data_prompt = None

    def set_pdf_path(self, path: str):
        self.pdf_path = path

    def load_pdf(self):
        self.pdf_text = ""
        if not self.pdf_path:
            raise ValueError("PDF path is not set.")

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n{text}"
                else:
                    self.pdf_text += f"\n\n--- Page {page_num} ---\n[No text found]"

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

                self.pdf_images_info.append({
                    "page": page_num,
                    "image": image
                })

    def build_pdf_data_prompt(self):
        self.pdf_data_prompt = "### Extracted PDF Content\n\n"
        self.pdf_data_prompt += self.pdf_text
        if self.pdf_images_info:
            self.pdf_data_prompt += "\n\n### Images in Document:\n"
            for img in self.pdf_images_info:
                self.pdf_data_prompt += f"- Image on page {img['page']}\n"
        else:
            self.pdf_data_prompt += "\n\n(No images found in the PDF)\n"

    def get_pdf_data_prompt(self):
        if self.pdf_data_prompt is None:
            self.build_pdf_data_prompt()
        return self.pdf_data_prompt


class PdfInference:
    def __init__(self):
        self.pdf_lookup = PdfLookup()

    def set_pdf_path(self, path: str):
        self.pdf_lookup.set_pdf_path(path)

    def set_inference_prompt(self, prompt: str):
        self.inference_prompt = prompt

    def run_inference(self):
        if not self.pdf_lookup.pdf_path:
            raise ValueError("PDF path is not set.")

        self.pdf_lookup.load_pdf()
        self.pdf_lookup.build_pdf_data_prompt()

        pdf_data_prompt = self.pdf_lookup.get_pdf_data_prompt()

        response = ollama.chat(
            model="qwen3:8b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that can answer questions about the content of a PDF document. I will provide you with the content of a PDF document in the following message, and you will answer questions based on that content."},
                {"role": "user", "content": pdf_data_prompt},
                {"role": "user", "content": self.inference_prompt},
            ]
        )
        return response['message']['content']


if __name__ == "__main__":
    # Example usage
    pdf_inference = PdfInference()
    pdf_inference.set_pdf_path("/home/grin/Downloads/521895066-MB2-HardwareManual-2.pdf")
    pdf_inference.set_inference_prompt(
        "What is the main topic of this document?")
    result = pdf_inference.run_inference()
    print("\n=== LLM Response ===\n")
    print(result)
