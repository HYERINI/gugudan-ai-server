import yaml
from pathlib import Path
from typing import List, Dict, Any


class PDFConfigLoader:
    """PDF 설정을 로드하는 싱글톤 클래스"""
    
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            # 프로젝트 루트에서 pdf_config.yaml 찾기
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "pdf_config.yaml"

            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)

    # 브랜딩 정보
    def get_service_name(self) -> str:
        return self._config['branding']['service_name']
    
    def get_service_name_en(self) -> str:
        return self._config['branding']['service_name_en']
    
    def get_tagline(self) -> str:
        return self._config['branding']['tagline']
    
    def get_footer_text(self) -> str:
        return self._config['branding']['footer_text']

    # 색상 정보
    def get_color(self, color_name: str) -> str:
        """색상 가져오기"""
        return self._config['colors'].get(color_name, '#000000')
    
    def get_colors(self) -> Dict[str, str]:
        """모든 색상 가져오기"""
        return self._config['colors']

    # 폰트 정보
    def get_font_paths(self) -> List[str]:
        """폰트 경로 목록 가져오기"""
        return self._config['fonts']['paths']
    
    def get_default_font(self) -> str:
        """기본 폰트 가져오기"""
        return self._config['fonts']['default']

    # 페이지 설정
    def get_page_config(self) -> Dict[str, Any]:
        """페이지 설정 가져오기"""
        return self._config['page']

    # 스타일 설정 (구버전 호환)
    def get_style(self, style_name: str) -> Dict[str, Any]:
        """특정 스타일 설정 가져오기 (구버전 호환)"""
        return self._config.get('styles', {}).get(style_name, {})

    def get_all_styles(self) -> Dict[str, Any]:
        """모든 스타일 가져오기 (구버전 호환)"""
        return self._config.get('styles', {})

    # Paragraph 스타일 설정
    def get_paragraph_style(self, style_name: str) -> Dict[str, Any]:
        """특정 Paragraph 스타일 설정 가져오기"""
        return self._config['paragraph_styles'].get(style_name, {})

    def get_all_paragraph_styles(self) -> Dict[str, Any]:
        """모든 Paragraph 스타일 가져오기"""
        return self._config['paragraph_styles']

    # 로고 설정
    def get_logo_config(self) -> Dict[str, Any]:
        """로고 설정 가져오기"""
        return self._config.get('logo', {})

    # 워터마크 설정
    def get_watermark_config(self) -> Dict[str, Any]:
        """워터마크 설정 가져오기"""
        return self._config['watermark']

    # 헤더 설정
    def get_header_config(self) -> Dict[str, Any]:
        """헤더 설정 가져오기"""
        return self._config['header']

    # 푸터 설정
    def get_footer_config(self) -> Dict[str, Any]:
        """푸터 설정 가져오기"""
        return self._config['footer']

    # 구분선 설정
    def get_divider_config(self) -> Dict[str, Any]:
        """구분선 설정 가져오기"""
        return self._config['divider']

    # 테이블 설정
    def get_table_style_config(self) -> Dict[str, Any]:
        """테이블 스타일 설정 가져오기"""
        return self._config['table_style']


# 싱글톤 인스턴스
pdf_config_loader = PDFConfigLoader()