from PIL import Image
import os

# 1.png부터 7.png까지 파일명을 리스트로 생성
filenames = [f"{i}.png" for i in range(1, 8)]
frames = []
target_size = None

for filename in filenames:
    if os.path.exists(filename):
        im = Image.open(filename).convert("RGB")
        # 첫 이미지의 크기를 기준으로 모든 이미지를 맞춤
        if target_size is None:
            target_size = im.size
        else:
            if im.size != target_size:
                im = im.resize(target_size)
        frames.append(im)
    else:
        print(f"파일을 찾을 수 없습니다: {filename}")

if frames:
    # duration은 각 프레임의 표시 시간을 밀리초 단위로 설정 (3000ms = 3초)
    # loop=0 은 무한 반복, loop=1 은 한 번만 재생 후 멈춤
    frames[0].save('demo.gif', format='GIF', append_images=frames[1:], save_all=True, duration=3000, loop=0)
    print("demo.gif 파일이 생성되었습니다.")
else:
    print("이미지 파일이 없습니다.")
