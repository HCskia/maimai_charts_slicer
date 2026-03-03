# maimai_charts_slicer

个人用舞萌谱面切片器，主要功能为按照输入时间来切片舞萌谱面和音频文件，majdata.txt和track.mp3

#### 使用方法

将谱面文件夹放入assest文件夹内

后使用方法 chartsManager.export_maimai_slice 来进行切片操作


| 参数名 | 用处                |
| :--------| :------------------------- |
| `folder_path`| 谱面文件夹路径 |
| `start_time`| 切片开始时间(秒) |
| `end_time`| 切片终止时间(秒) |
| `difficulty_idx`| 难度序数(5为Master 以此类推) |
| `rate`| 切片后的播放速率(float) |
| `repeat_count`| 切片后的重复次数(int) |

运行后会在谱面目录产生一个新的文件夹名为 segment_rate 里面包含新的majdata.txt和track.mp3，不包含bg.png或bg.jpg
