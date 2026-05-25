#!/usr/bin/env python3
import os
import sys
import time
import argparse
import yaml
import traceback

# ── Path Resolution & Imports ──────────────────────────────────────────────────
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure that local modules can be loaded correctly
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, os.path.join(CURRENT_DIR, "modules"))

try:
    from modules.medical_docs_ocr import MedicalDocsOCR
except ImportError:
    from medical_docs_ocr import MedicalDocsOCR


class MedicalDocsFolderManager:
    def __init__(self, input_folder: str, output_folder: str, interval_minutes: float, state_yaml_path: str = None) -> None:
        """
        Initializes the Medical Docs Folder Manager.

        Args:
            input_folder (str): The folder containing the input PDF documents.
            output_folder (str): The folder where the classified documents and markdown text will be organized.
            interval_minutes (float): The interval in minutes to check the input folder for new documents.
            state_yaml_path (str, optional): The path to the YAML state file. Defaults to modules/configs/folder_state.yaml.
        """
        self.input_folder = os.path.abspath(input_folder)
        self.output_folder = os.path.abspath(output_folder)
        self.interval_minutes = interval_minutes

        if state_yaml_path is None:
            self.state_yaml_path = os.path.join(CURRENT_DIR, "modules", "configs", "folder_state.yaml")
        else:
            self.state_yaml_path = os.path.abspath(state_yaml_path)

        # Default dictionary structure for the current folder's state
        self.state = {
            "input_folder": self.input_folder,
            "output_folder": self.output_folder,
            "last_checked_files": [],
            "processed_files": []
        }

        # Placeholder for the MedicalDocsOCR instance
        self.ocr = None

        # Load existing state from yaml
        self.load_state()

    def get_time_str(self) -> str:
        """Helper to get formatted local time string."""
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def load_state(self) -> None:
        """
        Loads state from the YAML file if it exists. 
        It expects a root list of dictionaries and retrieves the state matching our input folder.
        """
        if os.path.exists(self.state_yaml_path):
            print(f"[{self.get_time_str()}] Loading existing folder states from '{self.state_yaml_path}'...")
            try:
                with open(self.state_yaml_path, "r", encoding="utf-8") as f:
                    loaded_list = yaml.safe_load(f)
                
                # Normalize loaded data to a list of dicts
                if not isinstance(loaded_list, list):
                    print(f"[{self.get_time_str()}] Warning: YAML root was not a list. Initializing fresh list.")
                    loaded_list = []

                # Search for our input folder in the loaded list
                found_entry = None
                for entry in loaded_list:
                    if isinstance(entry, dict) and entry.get("input_folder") == self.input_folder:
                        found_entry = entry
                        break

                if found_entry:
                    self.state["output_folder"] = found_entry.get("output_folder", self.output_folder)
                    self.state["last_checked_files"] = found_entry.get("last_checked_files", [])
                    self.state["processed_files"] = found_entry.get("processed_files", [])
                    print(f"[{self.get_time_str()}] State matched for folder '{self.input_folder}': "
                          f"{len(self.state['processed_files'])} processed, "
                          f"{len(self.state['last_checked_files'])} last checked.")
                else:
                    print(f"[{self.get_time_str()}] Input folder '{self.input_folder}' not tracked yet. Appending new entry.")
                    self.save_state()
            except Exception as e:
                print(f"[{self.get_time_str()}] Error loading state from YAML: {e}. Starting fresh for this folder.")
        else:
            print(f"[{self.get_time_str()}] No existing folder state found at '{self.state_yaml_path}'. A new one will be created.")
            self.save_state()

    def save_state(self) -> None:
        """
        Saves/updates the state of the current folder inside the root list of the YAML file.
        """
        print(f"[{self.get_time_str()}] Saving state for '{self.input_folder}' to '{self.state_yaml_path}'...")
        try:
            # Ensure configs directory exists
            os.makedirs(os.path.dirname(self.state_yaml_path), exist_ok=True)
            
            # Read current list from file to preserve other folder configurations
            loaded_list = []
            if os.path.exists(self.state_yaml_path):
                try:
                    with open(self.state_yaml_path, "r", encoding="utf-8") as f:
                        loaded_list = yaml.safe_load(f)
                    if not isinstance(loaded_list, list):
                        loaded_list = []
                except Exception:
                    loaded_list = []

            # Replace or append the entry for the current input folder
            found_idx = -1
            for idx, entry in enumerate(loaded_list):
                if isinstance(entry, dict) and entry.get("input_folder") == self.input_folder:
                    found_idx = idx
                    break

            if found_idx != -1:
                loaded_list[found_idx] = self.state
            else:
                loaded_list.append(self.state)

            # Dump the root list of dictionaries back to the state YAML
            with open(self.state_yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(loaded_list, f, default_flow_style=False, allow_unicode=True)
            print(f"[{self.get_time_str()}] State saved successfully.")
        except Exception as e:
            print(f"[{self.get_time_str()}] Error saving state to YAML: {e}")

    def inspect_folder(self) -> list[str]:
        """Inspects the input folder for PDF files and returns their absolute paths."""
        print(f"[{self.get_time_str()}] Inspecting input folder: '{self.input_folder}'...")
        if not os.path.exists(self.input_folder):
            print(f"[{self.get_time_str()}] Warning: Input folder '{self.input_folder}' does not exist. Creating it now...")
            os.makedirs(self.input_folder, exist_ok=True)
            return []

        pdf_files = []
        for entry in os.scandir(self.input_folder):
            if entry.is_file() and entry.name.lower().endswith(".pdf"):
                pdf_files.append(os.path.abspath(entry.path))

        pdf_files.sort()
        print(f"[{self.get_time_str()}] Found {len(pdf_files)} PDF file(s) in input folder.")
        return pdf_files

    def process_files(self, file_paths: list[str]) -> None:
        """Processes the list of files using MedicalDocsOCR."""
        print(f"[{self.get_time_str()}] Initializing MedicalDocsOCR...")
        # Auto-detect location of configs/document_classes.yaml configuration
        data_yaml_path = os.path.join(CURRENT_DIR, "modules", "configs", "document_classes.yaml")
        if not os.path.exists(data_yaml_path):
            data_yaml_path = os.path.expanduser("~") + "/ai-apps-5g/medical_docs_agent/modules/configs/document_classes.yaml"

        print(f"[{self.get_time_str()}] Using document classes config from: '{data_yaml_path}'")
        
        # Instantiate and store the OCR agent in self.ocr
        self.ocr = MedicalDocsOCR(data_yaml_path=data_yaml_path)
        self.ocr.set_ocr_method("llm")
        self.ocr.set_documents_to_process(file_paths)
        self.ocr.set_output_folder(self.output_folder)

        print(f"[{self.get_time_str()}] Starting classification of {len(file_paths)} file(s)...")
        self.ocr.classify_documents()

        # Monitor the threaded processing progress
        while self.ocr.get_status() == "running":
            print(f"[{self.get_time_str()}] Waiting for classification thread... Status: {self.ocr.get_status()}")
            time.sleep(2)

        status = self.ocr.get_status()
        if status == "completed":
            print(f"[{self.get_time_str()}] Classification completed successfully. Organizing files...")
            results = self.ocr.get_results()
            self.ocr.organize_documents(results)

            # Update the list of processed files in the state variable and persist to YAML
            for f in file_paths:
                if f not in self.state["processed_files"]:
                    self.state["processed_files"].append(f)
            self.save_state()
            print(f"[{self.get_time_str()}] Successfully processed, organized, and tracked {len(file_paths)} document(s).")
        else:
            print(f"[{self.get_time_str()}] Classification completed with non-success status: {status}")

    def stop_ocr(self) -> None:
        """Calls the stop function of the MedicalDocsOCR class to clean up running models."""
        if self.ocr is not None:
            print(f"[{self.get_time_str()}] Calling stop() on MedicalDocsOCR to kill running models...")
            self.ocr.stop()
        else:
            print(f"[{self.get_time_str()}] MedicalDocsOCR was not active. Killing any running Ollama models directly...")
            import subprocess
            try:
                subprocess.run(["ollama", "stop", "glm-ocr:latest"], check=False)
                subprocess.run(["ollama", "stop", "gemma4:latest"], check=False)
            except Exception as e:
                print(f"[{self.get_time_str()}] Error executing direct stop commands: {e}")

    def run_cycle(self) -> None:
        """Runs a single folder inspection and processing cycle."""
        print(f"\n[{self.get_time_str()}] ─── Starting Folder Inspection Cycle ───")
        current_files = self.inspect_folder()

        # Update variable and YAML file with the last checked files snapshot
        self.state["last_checked_files"] = current_files
        self.save_state()

        # Filter out files that have already been processed
        unprocessed_files = [f for f in current_files if f not in self.state["processed_files"]]

        if not unprocessed_files:
            print(f"[{self.get_time_str()}] All discovered files have already been processed. Nothing to do.")
            return

        print(f"[{self.get_time_str()}] Discovered {len(unprocessed_files)} unprocessed file(s):")
        for f in unprocessed_files:
            print(f"  * {os.path.basename(f)}")

        # Process only the unprocessed files
        self.process_files(unprocessed_files)

    def start_loop(self) -> None:
        """Starts the main periodic loop to inspect the folder."""
        print(f"[{self.get_time_str()}] Starting periodic folder inspection loop.")
        print(f"[{self.get_time_str()}] Input Folder: '{self.input_folder}'")
        print(f"[{self.get_time_str()}] Output Folder: '{self.output_folder}'")
        print(f"[{self.get_time_str()}] Inspection Interval: {self.interval_minutes} minute(s)")

        interval_seconds = self.interval_minutes * 60.0

        while True:
            self.run_cycle()
            print(f"[{self.get_time_str()}] Sleeping for {self.interval_minutes} minute(s) before next check...")
            
            # Sleep in short increments to remain highly responsive to Ctrl+C
            slept = 0.0
            while slept < interval_seconds:
                time.sleep(1)
                slept += 1.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Medical Docs Agent - Folder Management & Auto-Classification Script"
    )
    parser.add_argument(
        "--input-folder", 
        required=True, 
        help="Path to the directory where input PDFs should be located"
    )
    parser.add_argument(
        "--output-folder", 
        required=True, 
        help="Path to the directory where classified PDFs and texts will be organized"
    )
    parser.add_argument(
        "--interval", 
        type=float, 
        required=True, 
        help="Inspection interval in minutes"
    )
    parser.add_argument(
        "--state-yaml", 
        default=None, 
        help="Optional path to save/load state YAML file (defaults to modules/configs/folder_state.yaml)"
    )

    args = parser.parse_args()

    manager = MedicalDocsFolderManager(
        input_folder=args.input_folder,
        output_folder=args.output_folder,
        interval_minutes=args.interval,
        state_yaml_path=args.state_yaml
    )

    try:
        manager.start_loop()
    except KeyboardInterrupt:
        print(f"\n[{manager.get_time_str()}] KeyboardInterrupt (Ctrl+C) detected! Stopping Medical Docs Agent...")
        manager.stop_ocr()
        print(f"[{manager.get_time_str()}] Shutdown complete. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[{manager.get_time_str()}] Unexpected exception occurred: {e}")
        traceback.print_exc()
        print(f"[{manager.get_time_str()}] Stopping Medical Docs Agent to release resources...")
        manager.stop_ocr()
        print(f"[{manager.get_time_str()}] Shutdown complete. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
