import os
import cv2
import torch
import numpy as np
import json
from insightface.app import FaceAnalysis
from tqdm import tqdm

# --- 설정 ---
# 프레임이 저장된 폴더 (프로젝트 루트/extracted_frames)
FRAME_DIR = "extracted_frames"
# 메타데이터 저장할 폴더 (프로젝트 루트/metadata)
SAVE_METADATA_DIR = "metadata"
os.makedirs(SAVE_METADATA_DIR, exist_ok=True)

# 프레임 추출 시 1초당 1개로 저장했으므로, 파일명에서 추출한 숫자가 초(timestamp)가 됩니다.
# (따라서 fps 변수는 별도로 사용하지 않습니다.)

# --- ArcFace 얼굴 인식 모델 초기화 ---
app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
app.prepare(ctx_id=0 if torch.cuda.is_available() else -1)

# --- Hierarchical ArcFace 모델 정의 및 가중치 로드 ---
MODEL_PATH = "2best_hierarchical_arcface(c).pth"
device = "cuda" if torch.cuda.is_available() else "cpu"

class HierarchicalArcFaceModel(torch.nn.Module):
    def __init__(self, embedding_size=512, num_groups=6, num_members=[2, 2, 4, 4, 2, 1]):
        super(HierarchicalArcFaceModel, self).__init__()
        self.global_fc = torch.nn.Sequential(
            torch.nn.Linear(embedding_size, 512),
            torch.nn.BatchNorm1d(512),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
        )
        self.group_head = torch.nn.Linear(512, num_groups)  # 그룹 분류
        self.member_heads = torch.nn.ModuleList(
            [torch.nn.Linear(512, num_members[i]) for i in range(num_groups)]
        )

    def forward(self, x):
        features = self.global_fc(x)
        group_logits = self.group_head(features)  # 그룹 예측
        predicted_group = torch.argmax(group_logits, dim=1)  # 예측된 그룹

        batch_size = features.shape[0]
        member_logits_padded = torch.zeros(batch_size, max([h.out_features for h in self.member_heads])).to(features.device)
        for i in range(batch_size):
            group_idx = predicted_group[i].item()
            member_logits = self.member_heads[group_idx](features[i].unsqueeze(0))
            member_logits_padded[i, :member_logits.shape[1]] = member_logits
        return group_logits, member_logits_padded

model = HierarchicalArcFaceModel().to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval()

# 그룹 및 멤버 정보 (오직 "NJZ" 그룹만 사용)
GROUPS = ["EXO", "IVE", "NJZ", "RED", "SK", "UNKNOWN"]
MEMBERS = {
    "EXO": ["D.O", "Kai"],
    "IVE": ["An Yujin", "Jang Wonyoung"],
    "NJZ": ["Danielle", "Gang Harin", "Kim Minji", "Pham Hanni"],
    "RED": ["Irene", "Joy", "Seulgi", "Wendy"],
    "SK": ["Hyunjin", "Felix"],
    "UNKNOWN": ["Unknown"]
}

# --- 메타데이터 생성 ---
metadata = []
frames = sorted(os.listdir(FRAME_DIR))

for frame_name in tqdm(frames, desc="Processing Frames"):
    # 확장자가 .png, .jpg, .jpeg 인 경우에만 처리
    if not frame_name.lower().endswith((".png", ".jpg", ".jpeg")):
        continue
    frame_path = os.path.join(FRAME_DIR, frame_name)
    frame = cv2.imread(frame_path)
    if frame is None:
        continue

    # 파일명 형식 예: "frame_0000.png"
    try:
        base_name = os.path.splitext(frame_name)[0]  # "frame_0000"
        sec_str = base_name.split("_")[-1]  # "0000"
        timestamp = int(sec_str)  # 0초, 1초, 2초 등
    except Exception as e:
        print(f"Error parsing timestamp for {frame_name}: {e}")
        continue

    # 얼굴 인식 수행
    faces = app.get(frame)
    if not faces:
        continue  # 얼굴이 인식되지 않으면 건너뜁니다.

    for face in faces:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox

        # 얼굴 임베딩 추출 및 모델 예측
        embedding_tensor = torch.tensor(face.embedding, dtype=torch.float32).unsqueeze(0).to(device)
        with torch.no_grad():
            group_logits, member_logits = model(embedding_tensor)
        group_probs = torch.softmax(group_logits, dim=1)
        predicted_group_id = torch.argmax(group_probs, dim=1).item()
        predicted_group_name = GROUPS[predicted_group_id]

        # 오직 "NJZ" 그룹만 저장
        if predicted_group_name != "NJZ":
            continue

        member_probs = torch.softmax(member_logits, dim=1)
        predicted_member_id = torch.argmax(member_probs, dim=1).item()
        member_confidence = member_probs[0, predicted_member_id].item()
        predicted_member_name = MEMBERS[predicted_group_name][predicted_member_id]

        # 메타데이터 저장 (timestamp는 이미 정수 초 단위)
        metadata.append({
            "timestamp": timestamp,
            "video_id": "FuJ1RiLoq-M",
            "group": predicted_group_name,
            "member": predicted_member_name,
            "confidence": float(torch.max(group_probs).item()),
            "bbox": [int(x1), int(y1), int(x2), int(y2)]
        })

        print(f"Processed {frame_name}: {predicted_group_name} - {predicted_member_name}")

# 결과를 JSON 파일로 저장
output_path = os.path.join(SAVE_METADATA_DIR, "metadata.json")
with open(output_path, "w", encoding="utf-8") as outfile:
    json.dump(metadata, outfile, indent=4, ensure_ascii=False)

print(f"메타데이터 저장 완료: {output_path}")
