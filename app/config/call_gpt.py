"""OpenAI GPT API 호출 모듈."""

import os
from typing import Optional, AsyncIterator, List, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# 환경 변수 검증
MAX_TOKENS_ENV = os.getenv("MAX_TOKENS")
if not MAX_TOKENS_ENV:
    raise ValueError("MAX_TOKENS environment variable is required")

try:
    MAX_TOKENS = int(MAX_TOKENS_ENV)
except ValueError as e:
    raise ValueError(f"MAX_TOKENS must be a valid integer: {e}") from e

# OpenAI 클라이언트 초기화
_async_client: Optional[AsyncOpenAI] = None


def get_async_client() -> AsyncOpenAI:
    """비동기 클라이언트 싱글톤 인스턴스 반환"""
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _async_client


async def _create_chat_completion_stream(prompt: str, file_urls: list[str] = None) -> AsyncIterator[str]:
    """비동기 방식으로 GPT API를 호출합니다 (스트리밍).
    
    Args:
        prompt: 사용자 프롬프트
        
    Returns:
        GPT 응답 텍스트
        
    Raises:
        ValueError: 프롬프트가 비어있는 경우
        Exception: OpenAI API 호출 실패 시
    """

    if isinstance(prompt, str):
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        actual_prompt = prompt
    else:
        actual_prompt = str(prompt)

    client = get_async_client()
    file_urls = file_urls or []

    # 1. 텍스트와 이미지를 포함한 메시지 구성
    if not file_urls:
        content = actual_prompt
    else:
        content = [{"type": "text", "text": actual_prompt}]
        for url in file_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
    
    # 타입 안전성을 위해 딕셔너리를 명시적으로 구성
    messages: List[Any] = [
        {"role": "user", "content": content}
    ]
    try:
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0,
            stream=True
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        raise Exception(f"Failed to call GPT API: {str(e)}") from e


async def _create_chat_completion_non_stream(prompt: str, file_urls: list[str] = None) -> str:
    """비스트리밍 방식으로 GPT API를 호출합니다.
    
    Args:
        prompt: 사용자 프롬프트
        file_urls: 이미지 URL 목록 (선택)
        
    Returns:
        완성된 응답 텍스트
        
    Raises:
        ValueError: 프롬프트가 비어있는 경우
        Exception: OpenAI API 호출 실패 시
    """
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    client = get_async_client()
    file_urls = file_urls or []
    
    # 메시지 구성 (스트리밍과 동일)
    if not file_urls:
        content = prompt
    else:
        content = [{"type": "text", "text": prompt}]
        for url in file_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
    
    messages: List[Any] = [
        {"role": "user", "content": content}
    ]
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0,
            stream=False  # 비스트리밍
        )
        
        return response.choices[0].message.content or ""
        
    except Exception as e:
        raise Exception(f"Failed to call GPT API: {str(e)}") from e


class CallGPT:
    """OpenAI GPT API를 비동기로 호출하는 클래스."""

    @staticmethod
    async def call_gpt(prompt: str, file_urls: list[str] = None) -> AsyncIterator[str]:
        """비동기 방식으로 GPT API를 호출합니다 (스트리밍).
        
        Args:
            prompt: 사용자 프롬프트
            file_urls: 이미지 URL 목록 (선택)
            
        Returns:
            GPT 응답 텍스트 (스트리밍)
            
        Raises:
            ValueError: 프롬프트가 비어있는 경우
            Exception: OpenAI API 호출 실패 시
        """
        try:
            async for chunk in _create_chat_completion_stream(prompt, file_urls):
                yield chunk
        except Exception as e:
            raise Exception(f"CallGPT 중계 에러: {str(e)}")

    @staticmethod
    async def call_gpt_non_stream(prompt: str, file_urls: list[str] = None) -> str:
        """비스트리밍 방식으로 GPT API를 호출합니다.
        
        Args:
            prompt: 사용자 프롬프트
            file_urls: 이미지 URL 목록 (선택)
            
        Returns:
            완성된 GPT 응답 텍스트
            
        Raises:
            ValueError: 프롬프트가 비어있는 경우
            Exception: OpenAI API 호출 실패 시
        """
        try:
            return await _create_chat_completion_non_stream(prompt, file_urls)
        except Exception as e:
            raise Exception(f"CallGPT 중계 에러: {str(e)}")