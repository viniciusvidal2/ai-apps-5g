import os
import shutil
from pathlib import Path
from ultralytics import YOLO

def main():
    src_dir = r"c:\Users\viki\Downloads\EPI\EPI-2-(Sem-No)-2"
    dst_dir = r"c:\Users\viki\Downloads\EPI\Person"
    model_path = os.path.join(dst_dir, "person.pt")
    
    # Target class index for "Person" in the dataset (based on data.yaml names list)
    target_person_idx = "9"
    # The class index output by the new model for "person" (which is 0)
    model_person_idx = 0
    
    # 1. Copiar as pastas test, train e valid (e data.yaml se possível)
    for folder in ["train", "valid", "test"]:
        src_folder = os.path.join(src_dir, folder)
        dst_folder = os.path.join(dst_dir, folder)
        if os.path.exists(src_folder):
            print(f"Copiando {folder}...")
            shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)
            
    src_yaml = os.path.join(src_dir, "data.yaml")
    if os.path.exists(src_yaml):
        shutil.copy2(src_yaml, os.path.join(dst_dir, "data.yaml"))

    # Load YOLO model
    print("Carregando o modelo...")
    model = YOLO(model_path)

    # 2. Iterate over the newly copied directories
    for folder in ["train", "valid", "test"]:
        images_dir = os.path.join(dst_dir, folder, "images")
        labels_dir = os.path.join(dst_dir, folder, "labels")
        
        if not os.path.exists(images_dir):
            continue
            
        # Guarantee labels directory exists
        os.makedirs(labels_dir, exist_ok=True)
        
        for image_name in os.listdir(images_dir):
            if not image_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            image_path = os.path.join(images_dir, image_name)
            label_name = os.path.splitext(image_name)[0] + ".txt"
            label_path = os.path.join(labels_dir, label_name)
            
            has_person = False
            needs_newline = False
            
            # Check if person is already identified
            if os.path.exists(label_path):
                with open(label_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines and not lines[-1].endswith('\n'):
                        needs_newline = True
                    for line in lines:
                        if line.startswith(f"{target_person_idx} "):
                            has_person = True
                            break
            
            # If not identified, run model and append predictions
            if not has_person:
                results = model.predict(source=image_path, verbose=False)
                # results is a list of Results objects
                new_lines = []
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        # Ensure we get the class correctly
                        cls_idx = int(box.cls[0].item())
                        if cls_idx == model_person_idx:
                            xywhn = box.xywhn[0]
                            # YOLO format: class x_center y_center width height (normalized)
                            new_lines.append(f"{target_person_idx} {xywhn[0]:.6f} {xywhn[1]:.6f} {xywhn[2]:.6f} {xywhn[3]:.6f}\n")
                
                if new_lines:
                    print(f"Adicionando {len(new_lines)} anotação(ões) de pessoa em {label_name}")
                    with open(label_path, "a", encoding="utf-8") as f:
                        if needs_newline:
                            f.write("\n")
                        f.writelines(new_lines)

if __name__ == "__main__":
    main()
