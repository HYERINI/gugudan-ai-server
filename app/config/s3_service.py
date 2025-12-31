import boto3
import asyncio
import uuid
import datetime
from io import BytesIO
from PIL import Image
from pathlib import Path
from fastapi import UploadFile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from botocore.signers import CloudFrontSigner
from app.config.settings import settings


class S3Service:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.AWS_S3_BUCKET

        self.cf_domain = settings.CLOUDFRONT_DOMAIN
        self.cf_key_id = settings.CLOUDFRONT_KEY_ID

        raw_key = settings.CLOUDFRONT_PRIVATE_KEY
        raw_key = raw_key.strip().strip('"').strip("'")

        raw_key = raw_key.replace("\\n", "\n")

        self.private_key_content = raw_key

    def _rsa_signer(self, message):
        """환경 변수로부터 프라이빗 키를 로드하여 메시지에 서명합니다."""
        private_key = serialization.load_pem_private_key(
            self.private_key_content.encode('utf-8'),
            password=None
        )
        return private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA1()
        )

    def get_signed_url(self, file_path: str, expire_minutes: int = 60) -> str:
        if not file_path:
            return ""

        try:
            if file_path.startswith("http"):
                # CloudFront 도메인이 이미 포함되어 있다면 경로만 떼어냄
                if self.cf_domain in file_path:
                    path = file_path.split(f"{self.cf_domain}/")[-1]
                else:
                    return file_path  # 다른 도메인이면 그대로 반환
            else:
                path = file_path

            path = path.lstrip("/")
            url = f"https://{self.cf_domain}/{path}"

            expire_date = datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)
            signer = CloudFrontSigner(self.cf_key_id, self._rsa_signer)

            signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)

            print(f"--- Generated Signed URL: {signed_url}")

            return signed_url

        except Exception as e:
            print(f"--- Signed URL Error: {str(e)}")
            return file_path

    async def upload_file(self, file: UploadFile, account_id: int) -> str:
        file_ext = Path(file.filename).suffix.lower()
        # 확장자가 없는 경우 처리
        if not file_ext:
            file_ext = ".jpg"

        from datetime import timezone, timedelta
        kst = timezone(timedelta(hours=9))
        now = datetime.datetime.now(kst)

        partition_path = now.strftime("%Y/%m/%d")
        file_name = f"{uuid.uuid4()}{file_ext}"
        full_path = f"chat/{partition_path}/{account_id}/{file_name}"

        # 이미지 압축 로직
        content = await file.read()
        if file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
            content = self._compress_image(content)

        try:
            # 1. S3에 Private하게 업로드 (기본값이 Private입니다)
            self.s3.put_object(
                Bucket=self.bucket,
                Key=full_path,
                Body=content,
                ContentType=file.content_type or "image/jpeg",
                StorageClass='INTELLIGENT_TIERING'
            )

            return full_path

        except Exception as e:
            print(f"S3 Upload Error Detail: {str(e)}")
            raise Exception(f"S3 업로드 및 서명 생성 실패: {str(e)}")

    def _compress_image(self, image_bytes: bytes) -> bytes:
        """이미지 용량을 줄여서 S3 비용 및 GPT 토큰 사용량을 아낍니다."""
        try:
            img = Image.open(BytesIO(image_bytes))

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # GPT Vision 모델 권장 해상도에 맞춰 리사이징
            try:
                # 최신 버전 (Pillow 10+)
                resampling_method = Image.Resampling.LANCZOS
            except AttributeError:
                # 이전 버전
                resampling_method = Image.LANCZOS

            img.thumbnail((2048, 2048), resampling_method)

            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=95, optimize=True)
            return buffer.getvalue()
        except Exception:
            # 압축 실패 시 원본 반환 (이미지가 아닌 파일 대비)
            return image_bytes

    async def read_file_content(self, file_path: str) -> str:
        """확장자 불문, 텍스트 기반 파일의 내용을 최대한 읽어옵니다."""
        if not file_path: return ""
        try:
            path = file_path.split(f"{self.cf_domain}/")[-1] if self.cf_domain in file_path else file_path
            path = path.lstrip("/")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.s3.get_object(Bucket=self.bucket, Key=path))
            raw_content = response['Body'].read()

            # 인코딩 자동 감지 시도 (utf-8 -> cp949 -> euc-kr)
            for enc in ['utf-8', 'cp949', 'euc-kr']:
                try:
                    return raw_content.decode(enc)
                except UnicodeDecodeError:
                    continue

            # 텍스트로 읽기 실패 시 (바이너리 등)
            return f"[알림: {file_path} 파일은 텍스트로 읽을 수 없는 형식이거나 손상되었습니다.]"
        except Exception as e:
            return f"[파일 로드 실패: {str(e)}]"