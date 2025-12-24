from enum import Enum


class Satisfaction(str, Enum):
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"


class FeedbackReason(str, Enum):
    # 좋아요 사유
    ACCURATE = "ACCURATE"  # 정확한 분석
    EMPATHETIC = "EMPATHETIC"  # 공감적인 태도
    HELPFUL = "HELPFUL"  # 해결책이 도움이 됨

    # 싫어요 사유
    INACCURATE = "INACCURATE"  # 사실과 다름/상황파악 못함
    OFFENSIVE = "OFFENSIVE"  # 말투가 무례함
    TOO_LONG = "TOO_LONG"  # 답변이 너무 김
    NOT_EMPATHETIC = "NOT_EMPATHETIC"  # 공감이 부족함
    IRRELEVANT = "IRRELEVANT"  # 질문과 상관없는 답변
    OTHER = "OTHER" # 기타(사용자가 수동 입력하는 부분)