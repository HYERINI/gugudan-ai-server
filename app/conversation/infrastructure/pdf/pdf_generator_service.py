from io import BytesIO
from datetime import datetime
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from app.config.pdf_config_loader import pdf_config_loader


class PDFGeneratorService:
    """PDF 생성 서비스 - Love-Note 브랜딩 (간소화 디자인)"""

    def __init__(self):
        self.config = pdf_config_loader
        self._register_korean_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _register_korean_fonts(self):
        """한글 폰트 등록 (설정 파일 사용)"""
        font_paths = self.config.get_font_paths()

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('KoreanFont', font_path))
                    pdfmetrics.registerFont(TTFont('KoreanFont-Bold', font_path))
                    self.korean_font = 'KoreanFont'
                    return
                except Exception as e:
                    continue

        self.korean_font = self.config.get_default_font()

    def _resolve_color(self, color_value: str) -> str:
        """색상 값을 해석 (컬러 이름 또는 HEX 값)"""
        if color_value.startswith('#'):
            return color_value
        return self.config.get_color(color_value)

    def _create_paragraph_style(self, name: str, style_config: dict) -> ParagraphStyle:
        """YAML 설정으로부터 ParagraphStyle 생성"""
        # 기본 스타일 상속
        parent = self.styles['Normal']
        if 'title' in name.lower() or 'heading' in name.lower():
            parent = self.styles['Heading1']

        # 폰트 결정
        font_name = self.korean_font
        if style_config.get('bold', False):
            font_name = f'{self.korean_font}-Bold'
        if style_config.get('font_name'):
            font_name = style_config['font_name']

        # 정렬 방식
        alignment = TA_LEFT
        if style_config.get('alignment') == 'center':
            alignment = TA_CENTER
        elif style_config.get('alignment') == 'right':
            alignment = TA_RIGHT
        elif style_config.get('alignment') == 'justify':
            alignment = TA_JUSTIFY

        # 색상
        text_color = colors.black
        if style_config.get('color'):
            text_color = colors.HexColor(self._resolve_color(style_config['color']))

        # 배경색
        back_color = None
        if style_config.get('background'):
            back_color = colors.HexColor(self._resolve_color(style_config['background']))

        # 테두리 (간소화 - 왼쪽 테두리만 지원)
        border_width = 0
        border_color = None
        border_padding = 0

        if style_config.get('border_width', 0) > 0:
            border_width = style_config['border_width']
            if style_config.get('border_color'):
                border_color = colors.HexColor(self._resolve_color(style_config['border_color']))
            border_padding = style_config.get('border_padding', 0)

        # ParagraphStyle 생성
        return ParagraphStyle(
            name=name,
            parent=parent,
            fontName=font_name,
            fontSize=style_config.get('font_size', 10),
            leading=style_config.get('line_height', style_config.get('font_size', 10) * 1.2),
            textColor=text_color,
            backColor=back_color,
            alignment=alignment,
            spaceBefore=style_config.get('space_before', 0),
            spaceAfter=style_config.get('space_after', 0),
            leftIndent=style_config.get('left_indent', 0),
            rightIndent=style_config.get('right_indent', 0),
            borderWidth=border_width,
            borderColor=border_color,
            borderPadding=border_padding
        )

    def _setup_styles(self):
        """스타일 설정 (YAML 기반)"""
        # YAML에서 모든 paragraph_styles 가져오기
        paragraph_styles = self.config.get_all_paragraph_styles()

        for style_name, style_config in paragraph_styles.items():
            # 스타일 이름을 PascalCase로 변환 (예: title -> CustomTitle)
            custom_name = f'Custom{style_name.capitalize()}'
            style = self._create_paragraph_style(custom_name, style_config)
            self.styles.add(style)

    def _add_page_decorations(self, canvas_obj, doc):
        """페이지 데코레이션 추가 (헤더, 푸터, 워터마크) - 간소화"""
        canvas_obj.saveState()

        # 워터마크 추가 (매우 연하게)
        watermark_config = self.config.get_watermark_config()
        if watermark_config['enabled']:
            canvas_obj.setFont('Helvetica', watermark_config['font_size'])
            canvas_obj.setFillColor(
                colors.HexColor(self._resolve_color(watermark_config['color'])),
                alpha=watermark_config['opacity']
            )
            canvas_obj.translate(A4[0]/2, A4[1]/2)
            canvas_obj.rotate(watermark_config['angle'])
            canvas_obj.drawCentredString(0, 0, watermark_config['text'])

        canvas_obj.restoreState()

        # 푸터 추가 (간소화)
        footer_config = self.config.get_footer_config()
        if footer_config['enabled']:
            canvas_obj.setFont('Helvetica', 8)
            canvas_obj.setFillColor(colors.HexColor(self.config.get_color('text_light')))

            # 페이지 번호 (오른쪽)
            if footer_config['show_page_number']:
                page_num = f"{doc.page}"
                canvas_obj.drawRightString(A4[0] - 2.5*cm, 1.5*cm, page_num)

            # 서비스 이름 (왼쪽)
            if footer_config['show_service_info']:
                service_text = f"{self.config.get_service_name_en()}"
                canvas_obj.drawString(2.5*cm, 1.5*cm, service_text)

    def _parse_markdown_table(self, lines: list, start_index: int) -> tuple:
        """마크다운 테이블 파싱

        Returns:
            (table_data, next_index)
        """
        table_rows = []
        i = start_index

        # 첫 번째 줄은 헤더
        if i < len(lines) and '|' in lines[i]:
            header_line = lines[i].strip()
            # 앞뒤 | 제거하고 분리
            header_cells = [cell.strip() for cell in header_line.strip('|').split('|')]
            table_rows.append(header_cells)
            i += 1

            # 두 번째 줄은 구분선 (---, :--:, --: 등) - 스킵
            if i < len(lines) and '|' in lines[i] and '-' in lines[i]:
                i += 1

            # 나머지 줄들은 데이터
            while i < len(lines) and '|' in lines[i]:
                data_line = lines[i].strip()
                data_cells = [cell.strip() for cell in data_line.strip('|').split('|')]
                table_rows.append(data_cells)
                i += 1

        return table_rows, i

    def _create_table_flowable(self, table_data: list):
        """테이블 데이터를 ReportLab Table로 변환"""
        if not table_data or len(table_data) < 2:  # 헤더 + 최소 1개 데이터 행
            return None

        # 테이블 설정 가져오기
        table_config = self.config.get_table_style_config()

        # Paragraph로 셀 내용 래핑 (한글 지원)
        processed_data = []
        for row_idx, row in enumerate(table_data):
            processed_row = []
            for cell in row:
                # 인라인 마크다운 처리
                cell_text = self._process_inline_markdown(cell)

                # 헤더는 볼드 처리
                if row_idx == 0:
                    cell_para = Paragraph(f'<b>{cell_text}</b>', self.styles['CustomBody'])
                else:
                    cell_para = Paragraph(cell_text, self.styles['CustomBody'])
                processed_row.append(cell_para)
            processed_data.append(processed_row)

        # 테이블 생성
        table = Table(processed_data)

        # 테이블 스타일 적용
        border_color = self._resolve_color(table_config['border']['color'])
        border_width = table_config['border']['width']

        style_commands = [
            # 전체 테두리
            ('GRID', (0, 0), (-1, -1), border_width, colors.HexColor(border_color)),

            # 헤더 스타일
            ('FONTSIZE', (0, 0), (-1, 0), table_config['header']['font_size']),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # 셀 패딩
            ('TOPPADDING', (0, 0), (-1, -1), table_config['cell']['padding']),
            ('BOTTOMPADDING', (0, 0), (-1, -1), table_config['cell']['padding']),
            ('LEFTPADDING', (0, 0), (-1, -1), table_config['cell']['padding']),
            ('RIGHTPADDING', (0, 0), (-1, -1), table_config['cell']['padding']),
        ]

        # 헤더 배경색 (있는 경우에만)
        if table_config['header']['background']:
            header_bg = self._resolve_color(table_config['header']['background'])
            style_commands.append(
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_bg))
            )

        # 헤더 텍스트 색상
        header_text_color = self._resolve_color(table_config['header']['text_color'])
        style_commands.append(
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(header_text_color))
        )

        # 줄무늬 효과 (alternating rows)
        if table_config['stripe']['enabled']:
            even_color = self._resolve_color(table_config['stripe']['even_row_color'])
            for row_idx in range(1, len(processed_data)):
                if row_idx % 2 == 0:
                    style_commands.append(
                        ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(even_color))
                    )

        table.setStyle(TableStyle(style_commands))

        return table

    def _convert_markdown_to_flowables(self, markdown_text: str):
        """마크다운 텍스트를 ReportLab flowable 요소로 변환"""
        flowables = []
        lines = markdown_text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 빈 줄
            if not line.strip():
                flowables.append(Spacer(1, 0.15*cm))
                i += 1
                continue

            # 테이블 감지 (| 로 시작하는 줄)
            if line.strip().startswith('|') and '|' in line:
                table_data, next_i = self._parse_markdown_table(lines, i)
                if table_data:
                    table = self._create_table_flowable(table_data)
                    if table:
                        flowables.append(Spacer(1, 0.3*cm))
                        flowables.append(table)
                        flowables.append(Spacer(1, 0.3*cm))
                i = next_i
                continue

            # 코드 블록 (```)
            if line.strip().startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                code_text = '\n'.join(code_lines)
                flowables.append(Preformatted(code_text, self.styles['CustomCode']))
                i += 1
                continue

            # H1 헤더 (#)
            if line.startswith('# '):
                text = self._process_inline_markdown(line[2:])
                flowables.append(Paragraph(text, self.styles['CustomH1']))
                i += 1
                continue

            # H2 헤더 (##)
            if line.startswith('## '):
                text = self._process_inline_markdown(line[3:])
                flowables.append(Paragraph(text, self.styles['CustomH2']))
                i += 1
                continue

            # H3 헤더 (###)
            if line.startswith('### '):
                text = self._process_inline_markdown(line[4:])
                flowables.append(Paragraph(text, self.styles['CustomH3']))
                i += 1
                continue

            # 인용구 (>)
            if line.startswith('> '):
                quote_lines = []
                while i < len(lines) and lines[i].startswith('> '):
                    quote_lines.append(lines[i][2:])
                    i += 1
                quote_text = ' '.join(quote_lines)
                quote_text = self._process_inline_markdown(quote_text)
                flowables.append(Paragraph(f'<i>{quote_text}</i>', self.styles['CustomQuote']))
                continue

            # 순서 없는 리스트 (-)
            if line.startswith('- ') or line.startswith('* '):
                while i < len(lines) and (lines[i].startswith('- ') or lines[i].startswith('* ')):
                    item_text = self._process_inline_markdown(lines[i][2:])
                    flowables.append(Paragraph(f'  • {item_text}', self.styles['CustomBody']))
                    i += 1
                flowables.append(Spacer(1, 0.15*cm))
                continue

            # 순서 있는 리스트 (1. 2. 3.)
            if re.match(r'^\d+\.\s', line):
                counter = 1
                while i < len(lines) and re.match(r'^\d+\.\s', lines[i]):
                    item_text = self._process_inline_markdown(re.sub(r'^\d+\.\s', '', lines[i]))
                    flowables.append(Paragraph(f'  {counter}. {item_text}', self.styles['CustomBody']))
                    counter += 1
                    i += 1
                flowables.append(Spacer(1, 0.15*cm))
                continue

            # 수평선 (---)
            if line.strip() == '---' or line.strip() == '***':
                divider_config = self.config.get_divider_config()
                flowables.append(Spacer(1, divider_config['space_before']))
                divider_color = self._resolve_color(divider_config['color'])
                flowables.append(Paragraph(f'<hr color="{divider_color}"/>', self.styles['CustomBody']))
                flowables.append(Spacer(1, divider_config['space_after']))
                i += 1
                continue

            # 일반 텍스트
            text = self._process_inline_markdown(line)
            flowables.append(Paragraph(text, self.styles['CustomBody']))
            i += 1

        return flowables

    def _process_inline_markdown(self, text: str) -> str:
        """인라인 마크다운 처리 (볼드, 이탤릭, 코드)"""
        # 볼드 (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)

        # 이탤릭 (*text* or _text_)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)

        # 인라인 코드 (`code`)
        code_color = self.config.get_color('code_text')
        text = re.sub(r'`(.+?)`', f'<font name="Courier" color="{code_color}">\\1</font>', text)

        # 링크 [text](url) - URL 표시
        primary_color = self.config.get_color('primary')
        text = re.sub(r'\[(.+?)\]\((.+?)\)', f'<font color="{primary_color}"><u>\\1</u></font>', text)

        return text

    def generate_summary_pdf(
        self,
        room_title: str,
        summary_text: str,
        created_at: datetime,
        message_count: int
    ) -> BytesIO:
        """채팅 요약 PDF 생성 (Love-Note 브랜딩 - 간소화)

        Args:
            room_title: 대화방 제목
            summary_text: 요약 텍스트 (마크다운 형식)
            created_at: 대화방 생성 시각
            message_count: 메시지 개수

        Returns:
            PDF 파일을 담은 BytesIO 객체
        """
        buffer = BytesIO()

        # 페이지 설정
        page_config = self.config.get_page_config()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=page_config['margin_right']*cm,
            leftMargin=page_config['margin_left']*cm,
            topMargin=page_config['margin_top']*cm,
            bottomMargin=page_config['margin_bottom']*cm
        )

        story = []

        # === 헤더 영역 (간소화) ===
        service_name = self.config.get_service_name()
        service_name_en = self.config.get_service_name_en()
        primary_color = self.config.get_color('primary')
        secondary_color = self.config.get_color('secondary')

        # 타이틀 (퍼플~핑크)
        title_html = f'<font color="{primary_color}">{service_name}</font> <font color="{secondary_color}">{service_name_en}</font>'
        story.append(Paragraph(title_html, self.styles['CustomTitle']))

        # 태그라인
        tagline = self.config.get_tagline()
        story.append(Paragraph(tagline, self.styles['CustomSubtitle']))

        # === 메타 정보 (간소화 - 테두리 제거) ===
        meta_lines = [
            f"<b>대화방:</b> {room_title}",
            f"<b>일시:</b> {created_at.strftime('%Y.%m.%d %H:%M')}",
            f"<b>메시지:</b> {message_count}개",
        ]

        for meta_line in meta_lines:
            story.append(Paragraph(meta_line, self.styles['CustomMeta']))

        story.append(Spacer(1, 0.5*cm))

        # === 구분선 ===
        divider_config = self.config.get_divider_config()
        divider_color = self._resolve_color(divider_config['color'])
        story.append(Paragraph(f'<hr color="{divider_color}" width="100%"/>', self.styles['CustomBody']))
        story.append(Spacer(1, 0.3*cm))

        # === 요약 내용 ===
        story.append(Paragraph("대화 요약", self.styles['CustomSection_title']))

        # === 마크다운 변환 및 추가 ===
        markdown_flowables = self._convert_markdown_to_flowables(summary_text)
        story.extend(markdown_flowables)

        # PDF 생성 (페이지 데코레이션 포함)
        doc.build(story, onFirstPage=self._add_page_decorations,
                  onLaterPages=self._add_page_decorations)
        buffer.seek(0)
        return buffer
