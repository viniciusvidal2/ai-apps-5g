from PIL import Image
import torch
import requests

# Original LLaVA imports
# from transformers import AutoProcessor, LlavaForConditionalGeneration

# Original BLIP imports
from transformers import BlipProcessor, BlipForConditionalGeneration

class ImageProcessor:
    def __init__(self) -> None:
        """Initialize the image processor with LLaVA model"""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # LLaVA model initialization
        """
        self.model_id = "llava-hf/llava-1.5-7b-hf"
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.model = LlavaForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        ).to(self.device)
        """

        # BLIP model initialization
        self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
        self.model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-large"
        ).to(self.device)

    def get_image_description(self, image) -> str:
        """Process an image and return its detailed description

        Args:
            image: The image to be processed (PIL Image)

        Returns:
            str: Detailed description of the image
        """
        # LLaVA processing
        """
        prompt = "Describe this image in detail, including all visible elements, colors, objects, people, and context."

        inputs = self.processor(
            text=prompt,
            images=image,
            return_tensors="pt"
        ).to(self.device)

        # Generate with LLaVA
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=False
            )

        # Decode the output
        description = self.processor.decode(output[0], skip_special_tokens=True)

        # Remove the prompt from the output
        if prompt in description:
            description = description.replace(prompt, "").strip()

        return description
        """
        # BLIP processing

        # Prepare the image for the model
        inputs = self.processor(image, return_tensors="pt").to(self.device)

        # Configure for longer and more detailed descriptions
        output = self.model.generate(
            **inputs,
            max_length=150,  # Increased for longer descriptions
            num_beams=5,     # Beam search for better quality
            min_length=30,   # Force more complete descriptions
            top_p=0.9,       # Nucleus sampling for diversity
            repetition_penalty=1.5  # Avoid repetitions
        )

        description = self.processor.decode(output[0], skip_special_tokens=True)

        # Return only the technical description without additional prefixes
        # to be used internally by the chatbot
        return description
