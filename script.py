import tkinter as tk
from tkinter import filedialog
import xml.etree.ElementTree as ET
import tkinterdnd2 as tkdnd
import sys
import os

def resource_path(relative_path):
    """ Retorna o caminho absoluto, compatível com Nuitka e execução normal """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class DoorExtractorApp:
    def __init__(self, root: tk.Tk):
        self.include_comments = tk.BooleanVar(value=True)
        self._setup_window(root)
        self._create_widgets()
        self.all_door_data = []

    def _setup_window(self, root: tk.Tk):
        self.root = root
        self.root.title("Door Data Extractor")
        self.root.geometry("400x300")
    def _create_widgets(self):
        self._create_drop_zone()
        self._create_output_text()
        self._create_select_button()
        self._create_comment_toggle()

    def _create_drop_zone(self):
        self.drop_label = tk.Label(
            self.root,
            text="Drag & Drop YMAP files here\nor click to select",
            bg='lightgray',
            height=8
        )
        self.drop_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._setup_drag_and_drop()

    def _create_output_text(self):
        self.output_text = tk.Text(self.root, height=4, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _setup_drag_and_drop(self):
        self.drop_label.drop_target_register(tkdnd.DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.process_drop)

    def _create_select_button(self):
        self.select_btn = tk.Button(
            self.root,
            text="Select Files",
            command=self.select_file
        )
        self.select_btn.pack(pady=10)

    def _create_comment_toggle(self):
        self.comment_check = tk.Checkbutton(
            self.root,
            text="Include Comments",
            variable=self.include_comments
        )
        self.comment_check.pack(pady=(0, 10))

    def _get_output_path(self):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".lua",
            filetypes=[("Lua files", "*.lua")],
            initialfile="combined_doors.lua"
        )
        if not output_path:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, "Operation cancelled!")
        return output_path

    def _collect_ymap_files(self, filepaths):
        all_files = []
        for filepath in filepaths:
            if os.path.isdir(filepath):
                for root, dirs, files in os.walk(filepath):
                    all_files.extend(
                        os.path.join(root, file)
                        for file in files
                        if file.endswith('.ymap')
                    )
            elif filepath.endswith('.ymap'):
                all_files.append(filepath)
        return sorted(all_files)

    def _is_valid_ymap(self, filepath):
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read(200)
            return not content.strip().startswith("RSC")

    def process_files(self, filepaths, output_path=None):
        try:
            if output_path is None:
                output_path = self._get_output_path()
                if not output_path:
                    return

            has_doors = False
            door_data_dict = {}
            ymap_files = self._collect_ymap_files(filepaths)
            
            for filepath in ymap_files:
                if not self._is_valid_ymap(filepath):
                    continue
                
                tree = ET.parse(filepath)
                root = tree.getroot()
                
                file_doors = []
                for entity in root.findall(".//Item[@type='CEntityDef']"):
                    modelname = entity.find('archetypeName').text
                    if "door" in modelname.lower():
                        position = entity.find('position')
                        coords = [position.get(axis) for axis in ['x', 'y', 'z']]
                        
                        for extension in entity.findall(".//Item"):
                            if extension.get('type') in ['SSxlGTA_0xDB12012B', 'CExtensionDefDoor'] and extension.find('Id') is not None and extension.find('Id').text is not None:                            
                                has_doors = True

                                door_id = getJenkinHash(bytearray(extension.find('Id').text, 'utf-8'))
                                model_hash = getJenkinHash(bytearray(modelname, "utf-8"))
                                door_entry = {
                                    'door_id': door_id,
                                    'model_hash': model_hash,
                                    'modelname': modelname,
                                    'coords': coords,
                                    'original_id': extension.find("Id").text
                                }
                                door_data_dict[door_id] = door_entry

            if has_doors:
                with open(output_path, 'w') as f:
                    f.write("local doorhashes = {\n")
                    sorted_doors = sorted(door_data_dict.items())
                    current_model = None
                    for door_id, entry in sorted_doors:
                        if current_model != entry['modelname']:
                            current_model = entry['modelname']
                            f.write(f"\n    -- Model: {current_model}\n")
                        f.write(f'    [{entry["door_id"]}] = {{{entry["door_id"]},{entry["model_hash"]},"{entry["modelname"]}",{entry["coords"][0]},{entry["coords"][1]},{entry["coords"][2]}}}, -- {entry["original_id"]}\n')
                    f.write("}")
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, f"Files processed successfully!\nOutput saved as: {output_path}")
            else:
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(tk.END, "No doors found in the provided files!")
            
        except Exception as e:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, f"Error processing files!\n{str(e)}")

    def process_drop(self, event):
        filepaths = [filepath.strip('{}') for filepath in event.data.split()]
        self.process_files(filepaths)

    def select_file(self):
        filepath = filedialog.askdirectory()
        if filepath:
            self.process_files([filepath])

def getJenkinHash(ba: bytearray) -> int:
    hash = 0
    for byte in ba:
        hash = (hash + byte) & 0xFFFFFFFF
        hash = (hash + (hash << 10)) & 0xFFFFFFFF
        hash = (hash ^ (hash >> 6)) & 0xFFFFFFFF
    hash = (hash + (hash << 3)) & 0xFFFFFFFF
    hash = (hash ^ (hash >> 11)) & 0xFFFFFFFF
    hash = (hash + (hash << 15)) & 0xFFFFFFFF
    return hash

if __name__ == "__main__":
    root = tkdnd.Tk()
    app = DoorExtractorApp(root)
    root.mainloop()