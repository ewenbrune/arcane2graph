import os
import json
import xmltodict

input_dir = "./xml"
output_dir = "./json"

os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.endswith(".xml"):
        xml_path = os.path.join(input_dir, filename)
        json_path = os.path.join(output_dir, filename.replace(".xml", ".json"))

        with open(xml_path, 'r', encoding='utf-8') as xml_file:
            try:
                data_dict = xmltodict.parse(xml_file.read())
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(data_dict, json_file, indent=2, ensure_ascii=False)
                print(f"Converted: {filename} → {os.path.basename(json_path)}")
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")
