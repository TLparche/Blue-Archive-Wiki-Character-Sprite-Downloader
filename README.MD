# Blue Archive Wiki Character Sprite Downloader

## 개요
Blue Archive Wiki 캐릭터 스프라이트 이미지 자동 다운로드 도구. 
필요시 캐릭터 부분 crop 도구 포함.
---

## 파일 설명

### `main.py`
* Blue Archive Wiki 크롤링하여 캐릭터 스프라이트 이미지를 다운로드
* `character_names` 배열 내부에 수집할 캐릭터 이름을 직접 지정

---

### `face_cropper.py`
* 다운로드한 이미지에서 수동으로 크롭 수행
* crop 이미지 크기 및 출력 이미지 크기 설정 가능
* 캐릭터 의상별로 따로 진행
* 드래그를 통해 범위 지정 가능

---

## 실행 방법

### 1. 의존성

```bash
uv pip install .
```

or

```bash
pip install .
```

---

### 2. 스프라이트 다운로드

```bash
python main.py
```

---

### 3. 얼굴 crop

```bash
python face_cropper.py
```

## 참고 사항

* Wiki 서버 부하를 고려하여 과도한 요청은 지양.
* 크롤링 대상 페이지 구조가 변경될 경우 동작하지 않을 수 있음.

---

## Overview

An automated tool for downloading **character sprite images** from the Blue Archive Wiki.
Includes an optional utility for **manually cropping character regions** from downloaded images.

---

## File Description

### `main.py`

* Crawls the Blue Archive Wiki and downloads character sprite images
* Specify the target characters by listing their names in the `character_names` array

---

### `face_cropper.py`

* Performs **manual cropping** on downloaded images
* Allows configuration of crop size and output image size
* Intended to be used **separately for each character outfit / variant**
* Supports **drag-based region selection** via GUI

---

## How to Run

### 1. Install Dependencies

```bash
uv pip install .
```

or

```bash
pip install .
```

---

### 2. Download Character Sprites

```bash
python main.py
```

---

### 3. Crop Character Regions

```bash
python face_cropper.py
```

---

## Notes

* Please avoid excessive requests to prevent unnecessary load on the Wiki server.
* The tool may stop working if the target Wiki page structure changes.

---
