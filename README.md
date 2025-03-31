# Multimodal Video Search & Edit

본 프로젝트는 **영상**을 프레임 단위로 분석해, **Arcface** 모델을 기반하여 인물구별 학습을 진행한 가중치를 통한 인물 식별 메타데이터와 **BLIP2/EILEV** 모델을 통한 영상 캡션 메타데이터를 생성합니다. 이 두 메타데이터를 합쳐 **kpf-sbert** 기반 임베딩 DB에 저장하고, 이를 바탕으로 **검색 및 수정** 기능을 제공합니다. 또한, **Slack**과 연동하여 검색 결과를 공유하고, 특정 구간을 편집할 수 있도록 지원합니다.

> **Note:**  
> - **EILEV 모델**은 Git Submodule을 통해 [https://github.com/yukw777/EILEV.git](https://github.com/yukw777/EILEV.git) 에서 관리됩니다.  
> - **kpf-sbert-128d-v1** 모델은 [HuggingFace Model Hub](https://huggingface.co/bongsoo/kpf-sbert-128d-v1)에서 다운로드할 수 있습니다.

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [설치 및 실행](#설치-및-실행)
3. [워크플로우](#워크플로우)
4. [모델 성능 및 한계](#모델-성능-및-한계)
5. [TODO / Future Plans](#todo--future-plans)

---

## 프로젝트 개요

- **핵심 기능**  
  - **Arcface** 기반 인물 인식 (Buffalo 모델 사용) 및 인물구별 학습  
  - **BLIP2/EILEV** 모델로 영상 캡션 생성  
  - **kpf-sbert-128d-v1** 모델을 통한 한글/영어 임베딩 및 검색  
  - **Gemini LLM**(Google Generative AI)을 이용해 검색 결과를 한국어로 번역·요약  
  - **Slack 연동**을 통한 검색 결과 공유 및 편집 기능  
  - **수정 기능**: 특정 구간(세그먼트) 자막, 멤버 정보 업데이트 및 세그먼트의 생성, 병합, 분할 처리

---

## 설치 및 실행

### 필수 환경
- **Python:** 3.10.11  
- **PostgreSQL:** 15 (pgvector 확장 사용 – 실행 후 `CREATE EXTENSION IF NOT EXISTS vector;` 명령어 실행)
- **ngrok:** [ngrok 다운로드](https://ngrok.com/)

