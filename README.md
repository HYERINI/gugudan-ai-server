# Gugudan AI Server 

감성 AI 기반 관계 솔루션 서비스 백엔드 서버

## 📋 프로젝트 개요

인간관계(연애·커플·이혼) 속의 '소통 문제'와 '심리적 거리'를 해결하는 AI 솔루션 서버입니다. 사용자의 대화 로그와 감정 데이터를 분석하여 관계 상태를 객관적으로 진단하고, 맞춤형 조언을 제공합니다.

### 핵심 가치

- **감정 데이터 기반 객관적 진단**: 주관적 감정을 데이터로 가시화
- **관계 유형별 맞춤 조언**: 연애/커플/이혼/썸 상황별 AI 피드백 제공
- **의사결정 지원**: 관계 유지·회복·정리 결정을 돕는 데이터 기반 인사이트

## 🏗️ 아키텍처

### 기술 스택

- **Framework**: FastAPI 0.109+
- **Language**: Python 3.13
- **Database**: MySQL 8.0, Redis 5.0+
- **ORM**: SQLAlchemy 2.0+, Alembic
- **AI/ML**: OpenAI API
- **Authentication**: JWT, OAuth 2.0 (Google, Kakao, Naver)
- **Security**: PyJWT, Cryptography, AES Encryption

### 아키텍처 패턴

**Hexagonal Architecture (Clean Architecture)** 기반으로 설계되어 있습니다.

```
app/
├── account/          # 계정 관리 도메인
├── auth/             # 인증/인가 도메인
├── conversation/     # 대화/채팅 도메인
├── ml/               # 머신러닝 분석 도메인
├── common/           # 공통 유틸리티
└── config/           # 설정 및 인프라 구성
```

각 도메인은 다음 레이어로 구성됩니다:
- **Domain**: 비즈니스 로직 및 엔티티
- **Application**: UseCase 및 포트 인터페이스
- **Infrastructure**: 외부 시스템 연동 (DB, Redis, 외부 API)
- **Adapter**: 입력/출력 어댑터 (Web API, Stream 등)

## 🚀 주요 기능

### 1. 인증 및 계정 관리 (`/api/v1`)

- **OAuth 소셜 로그인**: Google, Kakao, Naver 지원
- **JWT 기반 인증**: HttpOnly Cookie를 통한 안전한 토큰 관리
- **세션 관리**: Redis 기반 세션 및 토큰 블랙리스트 관리
- **CSRF 보호**: 쿠키 기반 CSRF 토큰 검증

### 2. AI 상담 대화 (`/conversation`)

- **스트리밍 채팅**: OpenAI API를 활용한 실시간 AI 상담
- **대화방 관리**: 사용자별 대화방 생성 및 관리
- **메시지 암호화**: AES 암호화를 통한 민감 정보 보호
- **사용량 관리**: 사용자별 API 호출 제한 및 모니터링
- **피드백 시스템**: 사용자 만족도 피드백 수집

**주요 엔드포인트:**
- `POST /conversation/chat/stream-auto`: AI 스트리밍 채팅 시작
- `GET /conversation/rooms`: 사용자 대화방 목록 조회
- `GET /conversation/rooms/{room_id}/messages`: 대화 메시지 조회
- `DELETE /conversation/rooms/{room_id}`: 대화방 삭제
- `POST /conversation/feedback`: 채팅 피드백 등록

### 3. 머신러닝 분석 (`/ml`)

- **대화 데이터 분석**: 채팅 메시지 기반 감정 분석
- **Fine-tuning 데이터 생성**: JSONL 형식의 학습 데이터 생성

**주요 엔드포인트:**
- `GET /ml/fine-tuning-data`: 지정 기간 내 대화 데이터를 JSONL로 변환

### 4. 계정 관리 (`/api/v1`)

- 사용자 프로필 관리
- 계정 정보 조회 및 수정

## 📦 설치 및 실행

### 사전 요구사항

- Python 3.13+
- Docker & Docker Compose
- MySQL 8.0
- Redis 5.0+

### 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# Application
APP_HOST=0.0.0.0
APP_PORT=33333
ENVIRONMENT=local

# Database
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=gugudan_ai
MYSQL_ROOT_PASSWORD=root_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# CORS
CORS_ALLOWED_FRONTEND_URL=http://localhost:3000
FRONTEND_URL=http://localhost:3000

# Security
CSRF_SECRET_KEY=your_csrf_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ENCRYPTION_KEY=your_encryption_key_32chars
JWT_EXPIRY_HOURS=12
COOKIE_SECURE=False
COOKIE_SAMESITE=lax

# OAuth - Google
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:33333/api/v1/auth/google/callback

# OAuth - Kakao
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_CLIENT_SECRET=your_kakao_client_secret
KAKAO_REDIRECT_URI=http://localhost:33333/api/v1/auth/kakao/callback

# OAuth - Naver
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
NAVER_REDIRECT_URI=http://localhost:33333/api/v1/auth/naver/callback

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### Docker Compose로 실행

**개발 환경:**
```bash
docker-compose -f docker-compose.dev.yml up --build
```

**프로덕션 환경:**
```bash
docker-compose up --build
```

서버는 `gugudan.net`에서 실행됩니다.

### 로컬 개발 환경

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 마이그레이션
alembic upgrade head

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 33333 --reload
```

## 📊 데이터베이스 마이그레이션

Alembic을 사용한 데이터베이스 스키마 관리:

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "migration_message"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

## 🔍 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: `http://localhost:33333/docs`
- **ReDoc**: `http://localhost:33333/redoc`

## 🧪 Health Check

```bash
curl http://localhost:33333/health
```

## 🔐 보안 기능

- **메시지 암호화**: AES-256 암호화를 통한 민감 정보 보호
- **JWT 토큰**: HttpOnly Cookie 기반 안전한 인증
- **CSRF 보호**: 쿠키 기반 CSRF 토큰 검증
- **OAuth 2.0**: 소셜 로그인을 통한 안전한 인증
- **토큰 블랙리스트**: Redis 기반 로그아웃 토큰 관리

## 📈 향후 계획

### 1단계 (현재)
- ✅ 회원가입/로그인
- ✅ AI 챗 상담
- ✅ 결과 전달

### 2단계 (MVP)
- 대화 로그 업로드 및 분석
- 감정 비율 및 패턴 분석
- 관계 진단 리포트 생성
- 개선 방향 제시

### 3단계 (확장)
- 영상 기반 감정 분석 (표정, 톤)
- 관계 유형별 맞춤 조언
- 감정 추이 시각화
- 관계 회복 챌린지 시스템

## 📝 라이선스

이 프로젝트는 공개 프로젝트입니다.

## 👥 구성원

@arti1117
@glassdekko
@HYERINI
@imhwan112
@keaunsolNa
@jspark2504 
