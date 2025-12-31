import boto3
import uuid
from io import BytesIO
from PIL import Image
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
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

    async def upload_file(self, file: UploadFile, account_id: int) -> str:
        file_ext = Path(file.filename).suffix.lower()
        # 확장자가 없는 경우 처리
        if not file_ext:
            file_ext = ".jpg"

        now = datetime.now()
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

            # 2. ✅ 핵심: 10분 동안만 유효한 임시 보안 URL 생성
            # 이 URL은 버킷이 '모든 퍼블릭 액세스 차단' 상태여도 작동합니다.
            presigned_url = self.s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': full_path
                },
                ExpiresIn=600  # 600초(10분) 후 자동 만료
            )

            # DB와 GPT에게는 이 임시 보안 URL이 전달됩니다.
            return presigned_url

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