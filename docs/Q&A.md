## 文档说明

本文档旨在针对大家在使用 `X-AnyLabeling` 项目中碰到的一些常见问题进行梳理，以更好地帮助大家使用该工具，后续会不间断地更新此文档。</br>

`X-AnyLabeling` 是一款全新的交互式自动标注工具，其基于 [Labelme](https://github.com/wkentaro/labelme) 和 [Anylabeling](https://github.com/vietanhdev/anylabeling) 进行构建，在此基础上扩展并支持了许多丰富的模型和功能，并借助`Segment Anything`和`YOLO`等主流模型提供强大的 AI 支持。无须任何复杂配置，下载即用，支持自定义模型，极大提升用户标注效率!</br>

## 功能支持

Q: **`X-AnyLabeling` 目前支持哪些标注样式？**</br>
A: 当前支持**多边形**、**矩形**、**圆形**、**直线**和**点**。</br>

Q: **`X-AnyLabeling` 目前提供哪些基础模型？**</br>
A: 详情可移步至 [models_list](./models_list.md) 文档查看。

## 标签转换

Q: **如何将打标完的 `*.json` 标签文件转换为 `YOLO`/`VOC`/`COCO` 等主流格式？**</br>
A: 考虑到当前标注工具框架的兼容性，为了更好的扩展和维护，目前此功能并没有集成到工具内，而是视为一个独立的组件抽离出来供大家使用，同时也方便大家修改。</br>
针对工具本身自定义(`custom`)的格式，我们可以使用工程目录下的 `tools/label_converter.py` 脚本轻松转换，以下是参考的转换指令：

```bash
#======================================================================= Usage ========================================================================#
#
#-------------------------------------------------------------------- custom2voc  ---------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx_folder --dst_path xxx_folder --classes xxx.txt --mode custom2voc
#                                                                                                                            
#-------------------------------------------------------------------- voc2custom  ---------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx_folder --img_path xxx_folder --classes xxx.txt --mode voc2custom
#                                                                                                                           
#-------------------------------------------------------------------- custom2yolo  --------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx_folder --dst_path xxx_folder --classes xxx.txt --mode custom2yolo                   
#                                                                                                                            
#-------------------------------------------------------------------- yolo2custom  --------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx_folder --img_path xxx_folder --classes xxx.txt --mode yolo2custom
#                                                                                                                                                      
#-------------------------------------------------------------------- custom2coco  --------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx_folder --dst_path xxx_folder --classes xxx.txt --mode custom2coco                      
#                                                                                                                                                      
#-------------------------------------------------------------------- coco2custom  --------------------------------------------------------------------#
# python tools/label_converter.py --task xxx --src_path xxx.json --dst_pat xxx_folder --img_path xxx_folder --classes xxx.txt --mode coco2custom                     
#                                                                                                                                                      
#======================================================================= Usage ========================================================================#
```

注意：
1. 目前 `--task` 支持的任务有 ['rectangle', 'polygon'] 即矩形框和多边形框两种，其中多边形框任务只提供 `yolo` 和 `custom` 之间的互相转换，方便大家训练检测和分割任务。至于其它的任务，如关键点等，可以参考下脚本自行修改适配下。</br>
2. 此处 `--classes` 参数指定的  `*.txt` 文件是用户预定义的类别文件，每一行代表一个类别，类别编号按从上到下的顺序编排，可参考 `assets` 目录下的 `classes.txt`。</br>

Q: **语义分割任务如何将输出的标签文件转换为 \*.png 格式输出？**</br>
A: 针对工具本身自定义(`custom`)的格式，我们可以使用工程目录下的 `tools/polygon_mask_conversion.py` 脚本轻松转换，以下是参考的转换指令：

```bash
python tools/polygon_mask_conversion.py --img_path xxx_folder --mask_path xxx_folder --mode poly2mask

# [option] 如果标签和图像不在同一目录下，请使用以下命令：
python tools/polygon_mask_conversion.py --img_path xxx_folder --mask_path xxx_folder --json_path xxx_folder --mode poly2mask
```

同样地，也支持将掩码图一键转换为自定义格式导入 `X-AnyLabeling` 中进行修正，输出的 `*.json` 文件默认保存至 'img_path' 目录：

```bash
python tools/polygon_mask_conversion.py --img_path xxx_folder --mask_path xxx_folder --mode mask2poly
```

## 工具使用

Q: **如何修改自定义快捷键？**
</br>
A: 可通过修改当前设备的用户根目录下的 `.anylabelingrc` 文件：

```bash
#Linux
cd ~/.anylabelingrc

#Windows
cd C:\\Users\\xxx\\.anylabelingrc

```

Q: **如何使用 SAM 系列模型？**</br>
A: 可参考以下步骤实施：
1. 点击菜单栏左侧的`Brain`标志按钮以激活AI功能选项；
2. 从下拉菜单`Model`中选择`Segment Anything Models`系列模型；
> 说明：模型精度和速度因模型而异，其中</br>
> - `Segment Anything Model (ViT-B)` 是最快的但精度不高；</br>
> - `Segment Anything Model (ViT-H)` 是最慢和最准确的；</br>
> - `Quant` 表示量化过的模型；</br>
3. 使用自动分割标记工具标记对象：
- `+Point`：添加一个属于对象的点；
- `-Point`：移除一个你想从对象中排除的点；
- `+Rect`：绘制一个包含对象的矩形。Segment Anything 将自动分割对象。
4. 清除：清除所有自动分割标记；
5. 完成对象(f)：当完成当前标记后，我们可以及时按下快捷键f，输入标签名称并保存当前对象。

> 注意</br>
> 1. `X-AnyLabeling` 在第一次运行任何模型时，需要从服务器下载模型，需要一段时间，这具体取决于本地的网络速度；</br>
> 2. 第一次进行 AI 推理也需要时间，请耐心等待，因此后台任务会运行以缓存`SAM`模型的“编码器”，在接下来的图像中自动分割模型需要时间会缩短。</br>

Q: **如何支持自定义模型？**</br>
A: 请参考 [custom_model.md](./custom_model.md) 文档。

Q: **如何编译打包成可执行文件？**</br>
A：可参考以下打包指令：</br>

```bash
#Windows-CPU
bash scripts/build_executable.sh win-cpu

#Windows-GPU
bash scripts/build_executable.sh win-gpu

#Linux-CPU
bash scripts/build_executable.sh linux-cpu

#Linux-GPU
bash scripts/build_executable.sh linux-gpu
```

> 注意事项：</br>
> 1. 编译前请针对相应的 GPU/CPU 版本修改 `anylabeling/app_info.py` 文件中的 `__preferred_device__` 参数；</br>
> 2. 如果需要编译`GPU`版本，请通过`pip install -r requirements-gpu-dev.txt`安装对应的环境；特别的，对于 `Windows-GPU` 版本的编译，请自行修改 `anylabeling-win-gpu.spec` 的 `datas` 列表参数，将您本地的`onnxruntime-gpu`的相关动态库`*.dll`添加进列表中；此外，下载 `onnxruntime-gpu` 包是需要根据 `CUDA` 版本进行适配，具体匹配表可参考[官方文档](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)说明。</br>
> 3. 对于 `macos` 版本可自行参考 `anylabeling-win-*.spec` 脚本进行修改。

## 问题反馈

Q: **初始化加载时下载模型失败如何处理？**</br>
A: 由于当前模型权重暂存在 `github` 上，下载前请先开启科学上网，否则大概率会因为网络问题下载失败；如果不具备条件的可考虑手动下载方式，将下载好的 `*.onnx` 文件放置到当前系统用户目录下的 `anylabeling_data/models/xxx` 下。</br>
这里 `xxx` 为对应的模型的名称，具体地可参考 [`X-anylabeling/anylabeling/configs/auto_labeling/models.yaml`](../anylabeling/configs/auto_labeling/models.yaml) 文件中的对应 `model_name` 字段，示例如下：

```bash
(x-anylabeling) cvhub@CVHub:~/anylabeling_data$ tree
.
└── models
    ├── mobile_sam_vit_h-r20230810
    │   ├── mobile_sam.encoder.onnx
    │   └── sam_vit_h_4b8939.decoder.onnx
    ├── yolov5s-r20230520
    │   └── yolov5s.onnx
    ├── yolov6lite_s_face-r20230520
    └── yolox_l_dwpose_ucoco-r20230820
        ├── dw-ll_ucoco_384.onnx
        └── yolox_l.onnx
```

Q: **能正常加载模型，但推理没结果？**</br>
A: 请先下载源码，在终端运行，查看具体的报错信息再尝试解决，如解决不了可在 [issue](https://github.com/CVHub520/X-AnyLabeling/issues) 提交反馈。