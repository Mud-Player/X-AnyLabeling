import argparse
import json
import os
import shutil
import time

import yaml
from PIL import Image
from tqdm import tqdm
from datetime import date

from pathlib import Path
import numpy as np
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import glob

import sys

sys.path.append('.')
from anylabeling.app_info import __version__
from sklearn.model_selection import train_test_split

VERSION = __version__


class BaseLabelConverter:
    def __init__(self, classes_file):

        if classes_file:
            with open(classes_file, 'r', encoding='utf-8') as f:
                self.classes = f.read().splitlines()
        else:
            self.classes = []
        print(f"import classes is: {self.classes}")

    def reset(self):
        self.custom_data = dict(
            version=VERSION,
            flags={},
            shapes=[],
            imagePath="",
            imageData=None,
            imageHeight=-1,
            imageWidth=-1
        )

    def get_image_size(self, image_file):
        with Image.open(image_file) as img:
            width, height = img.size
            return width, height


class RectLabelConverter(BaseLabelConverter):

    def custom_to_voc2017(self, input_file, output_dir):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        image_path = data['imagePath']
        image_width = data['imageWidth']
        image_height = data['imageHeight']

        root = ET.Element('annotation')
        ET.SubElement(root, 'folder').text = os.path.dirname(output_dir)
        ET.SubElement(root, 'filename').text = os.path.basename(image_path)
        size = ET.SubElement(root, 'size')
        ET.SubElement(size, 'width').text = str(image_width)
        ET.SubElement(size, 'height').text = str(image_height)
        ET.SubElement(size, 'depth').text = '3'

        for shape in data['shapes']:
            label = shape['label']
            points = shape['points']

            xmin = str(points[0][0])
            ymin = str(points[0][1])
            xmax = str(points[1][0])
            ymax = str(points[1][1])

            object_elem = ET.SubElement(root, 'object')
            ET.SubElement(object_elem, 'name').text = label
            ET.SubElement(object_elem, 'pose').text = 'Unspecified'
            ET.SubElement(object_elem, 'truncated').text = '0'
            ET.SubElement(object_elem, 'difficult').text = '0'
            bndbox = ET.SubElement(object_elem, 'bndbox')
            ET.SubElement(bndbox, 'xmin').text = xmin
            ET.SubElement(bndbox, 'ymin').text = ymin
            ET.SubElement(bndbox, 'xmax').text = xmax
            ET.SubElement(bndbox, 'ymax').text = ymax

        xml_string = ET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(xml_string)
        formatted_xml = dom.toprettyxml(indent='  ')

        with open(output_dir, 'w') as f:
            f.write(formatted_xml)

    def voc2017_to_custom(self, input_file, output_file):
        self.reset()

        tree = ET.parse(input_file)
        root = tree.getroot()

        image_path = root.find('filename').text
        image_width = int(root.find('size/width').text)
        image_height = int(root.find('size/height').text)

        self.custom_data['imagePath'] = image_path
        self.custom_data['imageHeight'] = image_height
        self.custom_data['imageWidth'] = image_width

        for obj in root.findall('object'):
            label = obj.find('name').text
            xmin = float(obj.find('bndbox/xmin').text)
            ymin = float(obj.find('bndbox/ymin').text)
            xmax = float(obj.find('bndbox/xmax').text)
            ymax = float(obj.find('bndbox/ymax').text)

            shape = {
                "label": label,
                "text": "",
                "points": [[xmin, ymin], [xmax, ymax]],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }

            self.custom_data['shapes'].append(shape)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_data, f, indent=2, ensure_ascii=False)

    def custom_to_yolov5(self, input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        image_width = data['imageWidth']
        image_height = data['imageHeight']

        with open(output_file, 'w', encoding='utf-8') as f:
            for shape in data['shapes']:
                label = shape['label']
                points = shape['points']

                class_index = self.classes.index(label)

                x_center = (points[0][0] + points[1][0]) / (2 * image_width)
                y_center = (points[0][1] + points[1][1]) / (2 * image_height)
                width = abs(points[1][0] - points[0][0]) / image_width
                height = abs(points[1][1] - points[0][1]) / image_height

                f.write(f"{class_index} {x_center} {y_center} {width} {height}\n")

    def yolov5_to_custom(self, input_file, output_file, image_file):
        self.reset()

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        image_width, image_height = self.get_image_size(image_file)

        for line in lines:
            line = line.strip().split(' ')
            class_index = int(line[0])
            x_center = float(line[1])
            y_center = float(line[2])
            width = float(line[3])
            height = float(line[4])

            x_min = int((x_center - width / 2) * image_width)
            y_min = int((y_center - height / 2) * image_height)
            x_max = int((x_center + width / 2) * image_width)
            y_max = int((y_center + height / 2) * image_height)

            label = self.classes[class_index]

            shape = {
                "label": label,
                "text": None,
                "points": [[x_min, y_min], [x_max, y_max]],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }

            self.custom_data['shapes'].append(shape)

        self.custom_data['imagePath'] = os.path.basename(image_file)
        self.custom_data['imageHeight'] = image_height
        self.custom_data['imageWidth'] = image_width

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_data, f, indent=2, ensure_ascii=False)

    def custom_to_coco(self, input_path, output_path):
        coco_data = {
            "info": {
                "year": 2023,
                "version": VERSION,
                "description": "COCO Label Conversion",
                "contributor": "CVHub",
                "url": "https://github.com/CVHub520/X-AnyLabeling",
                "date_created": str(date.today())
            },
            "licenses": [
                {
                    "id": 1,
                    "url": "https://www.gnu.org/licenses/gpl-3.0.html",
                    "name": "GNU GENERAL PUBLIC LICENSE Version 3"
                }
            ],
            "categories": [],
            "images": [],
            "annotations": []
        }

        for i, class_name in enumerate(self.classes):
            coco_data['categories'].append({
                "id": i + 1,
                "name": class_name,
                "supercategory": ""
            })

        image_id = 0
        annotation_id = 0

        file_list = os.listdir(input_path)
        for file_name in tqdm(file_list, desc='Converting files', unit='file', colour='green'):
            if not file_name.endswith('.json'): continue
            image_id += 1

            input_file = os.path.join(input_path, file_name)
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            image_path = data['imagePath']
            image_name = os.path.splitext(os.path.basename(image_path))[0]

            coco_data['images'].append({
                "id": image_id,
                "file_name": image_name,
                "width": data['imageWidth'],
                "height": data['imageHeight'],
                "license": 0,
                "flickr_url": "",
                "coco_url": "",
                "date_captured": ""
            })

            for shape in data['shapes']:
                annotation_id += 1
                label = shape['label']
                points = shape['points']
                class_id = self.classes.index(label)
                x_min = min(points[0][0], points[1][0])
                y_min = min(points[0][1], points[1][1])
                x_max = max(points[0][0], points[1][0])
                y_max = max(points[0][1], points[1][1])
                width = x_max - x_min
                height = y_max - y_min

                annotation = {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": class_id + 1,
                    "bbox": [x_min, y_min, width, height],
                    "area": width * height,
                    "iscrowd": 0
                }

                coco_data['annotations'].append(annotation)

        output_file = os.path.join(output_path, "x_anylabeling_coco.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(coco_data, f, indent=4, ensure_ascii=False)

    def coco_to_custom(self, input_file, output_path, image_path):

        img_dic = {}
        for file in os.listdir(image_path):
            img_dic[file] = file

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not self.classes:
            for cat in data["categories"]:
                self.classes.append(cat["name"])

        total_info, label_info = {}, {}

        # map category_id to name
        for dic_info in data["categories"]:
            label_info[dic_info["id"]] = dic_info["name"]

        # map image_id to info
        for dic_info in data["images"]:
            total_info[dic_info["id"]] = {
                "imageWidth": dic_info["width"],
                "imageHeight": dic_info["height"],
                "imagePath": img_dic[dic_info["file_name"]],
                "shapes": []
            }

        for dic_info in data["annotations"]:
            bbox = dic_info["bbox"]
            x_min = bbox[0]
            y_min = bbox[1]
            width = bbox[2]
            height = bbox[3]
            x_max = x_min + width
            y_max = y_min + height

            shape_info = {
                "label": self.classes[dic_info["category_id"] - 1],
                "text": None,
                "points": [[x_min, y_min], [x_max, y_max]],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }

            total_info[dic_info["image_id"]]["shapes"].append(shape_info)

        for dic_info in tqdm(total_info.values(), desc='Converting files', unit='file', colour='green'):
            self.reset()
            self.custom_data["shapes"] = dic_info["shapes"]
            self.custom_data["imagePath"] = dic_info["imagePath"]
            self.custom_data["imageHeight"] = dic_info["imageHeight"]
            self.custom_data["imageWidth"] = dic_info["imageWidth"]

            output_file = os.path.join(output_path, os.path.splitext(dic_info["imagePath"])[0] + ".json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_data, f, indent=2, ensure_ascii=False)


class PolyLabelConvert(BaseLabelConverter):

    def custom_to_yolov5(self, input_file, output_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        image_width = data['imageWidth']
        image_height = data['imageHeight']
        image_size = np.array([[image_width, image_height]])

        with open(output_file, 'w', encoding='utf-8') as f:
            for shape in data['shapes']:
                label = shape['label']
                points = np.array(shape['points'])
                class_index = self.classes.index(label)
                norm_points = points / image_size
                f.write(f"{class_index} " + " ".join(
                    [" ".join([str(cell[0]), str(cell[1])]) for cell in norm_points.tolist()]) + "\n")

    def yolov5_to_custom(self, input_file, output_file, image_file):
        self.reset()

        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        image_width, image_height = self.get_image_size(image_file)
        image_size = np.array([image_width, image_height], np.float64)

        for line in lines:
            line = line.strip().split(' ')
            class_index = int(line[0])
            label = self.classes[class_index]
            masks = line[1:]
            shape = {
                "label": label,
                "text": None,
                "points": [],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {}
            }
            for x, y in zip(masks[0::2], masks[1::2]):
                point = [np.float64(x), np.float64(y)]
                point = np.array(point, np.float64) * image_size
                shape['points'].append(point.tolist())
            self.custom_data['shapes'].append(shape)

        self.custom_data['imagePath'] = os.path.basename(image_file)
        self.custom_data['imageHeight'] = image_height
        self.custom_data['imageWidth'] = image_width

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Label Converter')
    parser.add_argument('--task', default='rectangle', choices=['rectangle', 'polygon'],
                        help='Choose the type of task to perform')
    parser.add_argument('--src_path', help='Path to input directory')
    parser.add_argument('--dst_path', help='Path to output directory')
    parser.add_argument('--img_path', help='Path to image directory')
    parser.add_argument('--classes', default=None,
                        help='Path to classes.txt file, where each line represent a specific class')
    parser.add_argument('--mode', help='Choose the conversion mode what you need',
                        choices=['custom2voc', 'voc2custom', 'custom2yolo', 'yolo2custom', 'custom2coco',
                                 'coco2custom'])
    parser.add_argument('--train_size', default='0.9', help='Train size for training')
    parser.add_argument('--val_size', default='0.1', help='Validate size for training')

    args = parser.parse_args()

    print(f"Starting conversion to {args.mode} format of {args.task}...")
    start_time = time.time()

    if args.task == 'rectangle':
        converter = RectLabelConverter(args.classes)
    elif args.task == 'polygon':
        converter = PolyLabelConvert(args.classes)
        valid_modes = ['custom2yolo', 'yolo2custom']
        assert args.mode in valid_modes, f"Polygon tasks are only supported in {valid_modes} now!"

    if args.mode == "custom2voc":
        file_list = os.listdir(args.src_path)
        os.makedirs(args.dst_path, exist_ok=True)
        for file_name in tqdm(file_list, desc='Converting files', unit='file', colour='green'):
            if not file_name.endswith('.json'): continue
            src_file = os.path.join(args.src_path, file_name)
            dst_file = os.path.join(args.dst_path, os.path.splitext(file_name)[0] + '.xml')
            converter.custom_to_voc2017(src_file, dst_file)
    elif args.mode == "voc2custom":
        file_list = os.listdir(args.src_path)
        for file_name in tqdm(file_list, desc='Converting files', unit='file', colour='green'):
            src_file = os.path.join(args.src_path, file_name)
            dst_file = os.path.join(args.img_path, os.path.splitext(file_name)[0] + '.json')
            converter.voc2017_to_custom(src_file, dst_file)
    elif args.mode == "custom2yolo":
        # Preprocessing
        json_names = glob.glob(args.src_path + "/*.json")
        conflitcs_jsons = []
        for json_file in json_names:
            with open(json_file) as f:
                json_data = json.load(f)
                labels = [shapes["label"] for shapes in json_data["shapes"]]
                if not validate_annotations(labels):
                    conflitcs_jsons.append(json_file)

        if conflitcs_jsons:
            for tmp in conflitcs_jsons:
                print(f"Validate file failed: {tmp}")
            os.abort()

        # Processing
        file_list = os.listdir(args.src_path)
        os.makedirs(args.dst_path, exist_ok=True)
        for file_name in tqdm(file_list, desc='Converting files', unit='file', colour='green'):
            if not file_name.endswith('.json'): continue
            src_file = os.path.join(args.src_path, file_name)
            dst_file = os.path.join(args.dst_path, os.path.splitext(file_name)[0] + '.txt')
            converter.custom_to_yolov5(src_file, dst_file)

        # Post Processing: split dataset to train, test
        json_names = [Path(item).stem for item in json_names]
        train_idxs, val_idxs = train_test_split(range(len(json_names)), test_size=float(args.val_size),
                                                train_size=float(args.train_size))
        train_json_names = [json_names[train_idx] for train_idx in train_idxs]
        val_json_names = [json_names[val_idx] for val_idx in val_idxs]
        dataset_path = Path(args.dst_path) / "YoloDatasets"
        os.makedirs(dataset_path / "images" / "train", exist_ok=True)
        os.makedirs(dataset_path / "images" / "val", exist_ok=True)
        os.makedirs(dataset_path / "images" / "test", exist_ok=True)
        os.makedirs(dataset_path / "labels" / "train", exist_ok=True)
        os.makedirs(dataset_path / "labels" / "val", exist_ok=True)
        os.makedirs(dataset_path / "labels" / "test", exist_ok=True)
        for file_name in train_json_names:
            image_file = file_name + ".JPG"
            shutil.copy(Path(args.src_path) / image_file, dataset_path / "images" / "train" / image_file)
            label_file = file_name + ".txt"
            shutil.copy(Path(args.dst_path) / label_file, dataset_path / "labels" / "train" / label_file)
        for file_name in val_json_names:
            image_file = file_name + ".JPG"
            shutil.copy(Path(args.src_path) / image_file, dataset_path / "images" / "test" / image_file)
            shutil.copy(Path(args.src_path) / image_file, dataset_path / "images" / "val" / image_file)
            label_file = file_name + ".txt"
            shutil.copy(Path(args.dst_path) / label_file, dataset_path / "labels" / "test" / label_file)
            shutil.copy(Path(args.dst_path) / label_file, dataset_path / "labels" / "val" / label_file)
        with open(Path(dataset_path) / "dataset.yaml", "w+") as f:
            yaml_data = {
                "train": str(dataset_path / "images" / "train"),
                "val": str(dataset_path / "images" / "val"),
                "test": str(dataset_path / "images" / "val"),
                "nc": len(converter.classes),
                "names": converter.classes
            }
            dataset_yaml = yaml.dump(yaml_data, f)


    elif args.mode == "yolo2custom":
        img_dic = {}
        for file in os.listdir(args.img_path):
            prefix = file.split('.')[0]
            img_dic[prefix] = file
        file_list = os.listdir(args.src_path)
        for file_name in tqdm(file_list, desc='Converting files', unit='file', colour='green'):
            src_file = os.path.join(args.src_path, file_name)
            dst_file = os.path.join(args.img_path, os.path.splitext(file_name)[0] + '.json')
            img_file = os.path.join(args.img_path, img_dic[os.path.splitext(file_name)[0]])
            converter.yolov5_to_custom(src_file, dst_file, img_file)
    elif args.mode == "custom2coco":
        os.makedirs(args.dst_path, exist_ok=True)
        converter.custom_to_coco(args.src_path, args.dst_path)
    elif args.mode == "coco2custom":
        os.makedirs(args.dst_path, exist_ok=True)
        converter.coco_to_custom(args.src_path, args.dst_path, args.img_path)

    end_time = time.time()
    print(f"Conversion completed successfully: {args.dst_path}")
    print(f"Conversion time: {end_time - start_time:.2f} seconds")


def validate_annotations(lst: list) -> bool:
    # validate duplicate
    if len(lst) != len(set(lst)):
        return False

    # validate different faces conflicts
    def has_more_than_two_intersection(my_list, my_sets):
        my_set = set(my_list)
        count = 0
        for s in my_sets:
            if my_set.intersection(s):
                count += 1
            if count >= 2:
                return True
        return False

    compare_sets = [
        {"Antenna", "Antenna-Cover", "1001-02A", "1001-02A-Cover", "1005-02C-1A", "1005-02C-1A-Cover",
         "1005-03C-1A", "1005-03C-1A-QRPanel", "2006-01C-1A", "2006-01C-1A-QRPanel", "2006-01C-2A",
         "2006-01C-2A-Cover"},
        {"placeholder-front", "placeholder-front-Cover", "1001-03A", "1001-03A-Cover", "1001-04A", "1001-04A-QRPanel",
         "1006-02C-1A", "1006-02C-1A-Cover", "2007-01A", "2007-01A-Cover", "placeholder-tail", "placeholder-tail-Cover",
         "3002-06C", "3002-06C-Cover"}
    ]
    if has_more_than_two_intersection(lst, compare_sets):
        # special case
        if not has_more_than_two_intersection(
                lst, [{"Antenna", "Antenna-Cover"}, {"placeholder-front", "placeholder-front-Cover"}]):
            return False

    return True

if __name__ == '__main__':
    main()
