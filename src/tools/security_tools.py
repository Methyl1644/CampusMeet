"""安全审核工具：内容审核初筛、风险评估"""
import json
import logging
from langchain.tools import tool
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context
from utils.security import screen_content, screen_post_content

logger = logging.getLogger(__name__)


@tool
def screen_text_content(text: str) -> str:
    """审核文本内容安全性。检测身份证号、手机号、微信号、QQ号、精确住址、违禁词，并评估风险等级。text 为待审核的文本内容。"""
    ctx = request_context.get() or new_context(method="screen_text_content")
    try:
        result = screen_content(text)
        return json.dumps({
            "has_violations": result.has_violations,
            "violations": result.violations,
            "risk_level": result.risk_level,
            "risk_factors": result.risk_factors,
            "suggestions": result.suggestions,
            "cleaned_text": result.cleaned_text if result.has_violations else None,
        }, ensure_ascii=False)
    except Exception as e:
        logger.error(f"screen_text_content error: {e}")
        return json.dumps({"error": f"审核失败: {str(e)}"}, ensure_ascii=False)
