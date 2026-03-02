import re
from pydub import AudioSegment
import os

assestPath = r"assest/"

class chartsManager:
    def __init__(self):
        pass

    @staticmethod
    def parse_maimai_chart(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 排除 inote 开头的键
        metadata_pattern = r'&([a-z_]+(?<!inote_\d))=(.*?)(?=\n&|\n\n|$)'
        metadata = dict(re.findall(metadata_pattern, content, re.DOTALL))
        # 难度等级 谱师
        levels = {}
        for i in range(1, 7):
            lv_key = f'lv_{i}'
            des_key = f'des_{i}'
            if f'&{lv_key}=' in content:
                lv_val = re.search(rf'&{lv_key}=(.*?)\n', content)
                des_val = re.search(rf'&{des_key}=(.*?)\n', content)
                levels[i] = {
                    'level': lv_val.group(1).strip() if lv_val else "",
                    'designer': des_val.group(1).strip() if des_val else ""
                }

        # 各个难度的谱面数据
        charts = {}
        inote_pattern = r'&inote_(\d)=(.*?)\nE'
        inote_matches = re.findall(inote_pattern, content, re.DOTALL)

        for difficulty_idx, chart_data in inote_matches:
            clean_chart = "".join([line.strip() for line in chart_data.splitlines()])
            charts[int(difficulty_idx)] = clean_chart

        return {
            "metadata": metadata,
            "difficulty_info": levels,
            "charts": charts
        }

    @staticmethod
    def get_chart_segment_pro(full_chart_text, start_time_sec, end_time_sec, initial_bpm=205):
        # 移除换行并将谱面流拆分为最小节拍单位
        chart_flow = "".join(full_chart_text.splitlines())
        beats = chart_flow.split(',')

        current_time = 0.0
        current_bpm = initial_bpm
        current_divisor = 4

        state_at_start = {"bpm": initial_bpm, "divisor": 4}
        segment_beats = []

        for beat in beats:
            bpm_match = re.search(r'\((\d+\.?\d*)\)', beat)
            if bpm_match:
                current_bpm = float(bpm_match.group(1))

            divisor_match = re.search(r'\{(\d+)\}', beat)
            if divisor_match:
                current_divisor = int(divisor_match.group(1))

            # 计算当前拍的时长
            beat_duration = (60.0 / current_bpm) * (4.0 / current_divisor)

            if current_time < start_time_sec:
                state_at_start["bpm"] = current_bpm
                state_at_start["divisor"] = current_divisor

            if current_time >= start_time_sec and current_time <= end_time_sec:
                segment_beats.append(beat)

            current_time += beat_duration
            if current_time > end_time_sec:
                break

        if not segment_beats:
            return "E"  # 结束符

        header = ""
        first_beat = segment_beats[0]
        if f"({state_at_start['bpm']})" not in first_beat:
            header += f"({state_at_start['bpm']})"
        if f"{{{state_at_start['divisor']}}}" not in first_beat:
            header += f"{{{state_at_start['divisor']}}}"

        return header + ",".join(segment_beats) + ",E"

    @staticmethod
    def slice_audio_track(input_path,folder_path, start_time_sec, end_time_sec, output_filename="track_segment.mp3", rate=1.0):
        if not os.path.exists(input_path):
            print(f"错误: 找不到音频文件 {input_path}")
            return

        print(f"正在加载音频: {input_path}...")
        audio = AudioSegment.from_file(input_path)

        start_ms = start_time_sec * 1000
        end_ms = end_time_sec * 1000

        print(f"正在切分音频: {start_time_sec}s -> {end_time_sec}s")
        segment = audio[start_ms:end_ms]
        final_audio = chartsManager.apply_speed_to_audio(segment, rate)

        output_path = os.path.join(f"{folder_path}/segment_rate", output_filename)
        final_audio.export(output_path, format="mp3", bitrate="192k")

        print(f"音频切分完成！已保存至: {output_path}")
        return output_path

    @staticmethod
    def export_maimai_slice(folder_path, start_time, end_time, difficulty_idx=5, rate=1.0):
        export_path = f"{folder_path}/segment_rate"
        os.makedirs(export_path, exist_ok=True)
        # 解析原谱面
        data = chartsManager.parse_maimai_chart(os.path.join(folder_path, 'maidata.txt'))
        full_chart = data['charts'].get(difficulty_idx, "")
        start_bpm = float(data['metadata'].get('wholebpm', 205))

        if not full_chart:
            print("未找到指定难度的谱面数据")
            return

        # 切分谱面字符串
        sliced_chart = chartsManager.get_chart_segment_pro(full_chart, start_time, end_time, initial_bpm=int(start_bpm))
        final_chart = chartsManager.modify_chart_speed(sliced_chart, rate)

        # 切分音频
        chartsManager.slice_audio_track(os.path.join(folder_path, 'track.mp3'),folder_path, start_time, end_time, "track.mp3", rate=rate)

        # 生成新的 maidata.txt
        new_maidata_content = (
            f"&title={data['metadata'].get('title', 'Unknown')}_segment_{rate}Speed\n"
            f"&artist={data['metadata'].get('artist', 'Unknown')}\n"
            f"&wholebpm={int(start_bpm*rate)}\n"
            f"&inote_{difficulty_idx}=\n{final_chart}\n"
        )

        with open(os.path.join(export_path, 'maidata.txt'), 'w', encoding='utf-8') as f:
            f.write(new_maidata_content)

        print("\n[成功] 谱面片段与音频片段已生成！")

    @staticmethod
    def modify_chart_speed(chart_text, rate):
        def bpm_replacer(match):
            old_bpm = float(match.group(1))
            new_bpm = old_bpm * rate
            return f"({new_bpm:.2f})"
        return re.sub(r'\((\d+\.?\d*)\)', bpm_replacer, chart_text)

    @staticmethod
    def apply_speed_to_audio(audio_segment, rate):
        new_sample_rate = int(audio_segment.frame_rate * rate)
        new_audio = audio_segment._spawn(audio_segment.raw_data, overrides={
            "frame_rate": new_sample_rate
        })
        return new_audio.set_frame_rate(audio_segment.frame_rate)

if __name__ == '__main__':
    chartsManager.export_maimai_slice(fr"{assestPath}/11394_WORLDSENDLONELINESS_DX", 80, 130,rate=0.8)