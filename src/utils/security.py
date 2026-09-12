"""安全规则引擎

PRD 5.3 安全与隐私规则:
- 联系方式保护: 公开帖不显示手机号、QQ、微信
- 内容审核: 规则初筛（身份证号、手机号、违禁词、精确住址）+ AI 语义判断 + 风险分级
- 风险分级: 线下、金钱、长途、夜间等场景给出额外提示
- Coze 边界: 用户密码、原始身份证明、脱敏前联系方式不发送给 Coze
"""
import re
import logging
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def normalize_for_moderation(text: str) -> str:
    """Normalize user text without changing its readable meaning.

    NFKC folds full-width Latin characters, digits, and punctuation. Invisible
    spacing and repeated whitespace are removed so split-character variants can
    be evaluated consistently by moderation rules.
    """
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)
    normalized = normalized.replace("／", "/").replace("．", ".").replace("＠", "@")
    normalized = re.sub(r"[\t\r\f\v ]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


@dataclass
class ScreenResult:
    """内容审核结果"""
    has_violations: bool = False
    violations: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low / medium / high
    risk_factors: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    cleaned_text: str = ""


# ==================== 敏感信息检测 ====================

# 身份证号: 18位(最后一位可能是X)，用前后非数字边界替代 \b
ID_CARD_PATTERN = re.compile(r'(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)')

# 手机号: 11位, 1[3-9]开头，用前后非数字边界替代 \b
PHONE_PATTERN = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')

# 微信号检测 (包含各种变体)
WECHAT_PATTERNS = [
    re.compile(r'(?:微信|vx|VX|wechat|WeChat|加我|联系方式)[\s:：]*([a-zA-Z0-9_-]{6,20})', re.IGNORECASE),
    re.compile(r'(?:微信号|v信|V信)[\s:：]*([a-zA-Z0-9_-]{6,20})', re.IGNORECASE),
]

# QQ号检测
QQ_PATTERNS = [
    re.compile(r'(?:QQ|qq|Qq|q\s*q)[\s:：]*([1-9]\d{4,11})(?!\d)'),
]

# 邮箱检测 (用于检测在帖子内容中暴露邮箱)
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# 精确住址检测 (包含楼栋室等精确信息)
ADDRESS_PATTERN = re.compile(
    r'(?:住在|地址|住址|宿舍|公寓|楼|栋|单元|室)[\s]*[\d]+[栋楼栋幢]*[\s]*[\d]*[单元]*[\s]*[\d]*[室号]*',
    re.IGNORECASE
)


def detect_id_card(text: str) -> list[str]:
    """检测身份证号"""
    matches = ID_CARD_PATTERN.findall(text)
    return matches


def detect_phone(text: str) -> list[str]:
    """检测手机号"""
    matches = PHONE_PATTERN.findall(text)
    # 过滤掉明显不是手机号的数字(如日期、年份等)
    return [m for m in matches if not _is_likely_not_phone(m)]


def _is_likely_not_phone(number: str) -> bool:
    """排除明显不是手机号的11位数字"""
    # 以19或20开头的可能是年份
    if number.startswith(("19", "20")) and len(number) == 11:
        # 可能是年份+月份+日期的组合
        year = number[:4]
        if year in ("2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"):
            return True
    return False


def detect_wechat(text: str) -> list[str]:
    """检测微信号"""
    results = []
    for pattern in WECHAT_PATTERNS:
        matches = pattern.findall(text)
        results.extend(matches)
    return results


def detect_qq(text: str) -> list[str]:
    """检测QQ号"""
    results = []
    for pattern in QQ_PATTERNS:
        matches = pattern.findall(text)
        results.extend(matches)
    return results


def detect_address(text: str) -> list[str]:
    """检测精确住址"""
    matches = ADDRESS_PATTERN.findall(text)
    return matches


# ==================== 违禁词过滤 ====================

# 违禁词列表 (基础版, 可扩展)
BANNED_WORDS = [
    # 违法活动
    "赌博", "博彩", "彩票", "外围", "代孕",
    "毒品", "大麻", "冰毒", "摇头丸",
    "伪造", "假证", "假文凭", "假学历", "代考", "替考",
    "黑客", "刷单", "刷信誉", "水军",
    # 欺诈相关
    "传销", "拉人头", "庞氏",
    # 其他敏感
    "枪支", "弹药", "管制刀具",
]

# 风险关键词 (触发风险分级)
RISK_KEYWORDS = {
    "medium": [
        # 线下场景
        "线下见面", "当面", "面谈", "来我家", "去你家",
        # 金钱相关
        "转账", "付款", "押金", "收费", "费用", "缴费",
        "收钱", "付钱", "AA", "平摊",
        # 夜间场景
        "深夜", "凌晨", "夜间活动",
    ],
    "high": [
        # 高风险场景
        "跨省", "长途", "异地",
        "大额", "高额", "投资", "理财",
        "借贷", "贷款", "利息",
        "中介费", "手续费", "保证金",
        # 诱导性词汇
        "稳赚", "包过", "包赚", "免费拿",
    ],
}


def check_banned_words(text: str) -> list[str]:
    """检查违禁词"""
    found = []
    for word in BANNED_WORDS:
        if word in text:
            found.append(word)
    return found


def assess_risk(text: str) -> tuple[str, list[str]]:
    """评估风险等级, 返回 (risk_level, risk_factors)"""
    factors = []

    # 检查中等风险关键词
    for keyword in RISK_KEYWORDS["medium"]:
        if keyword in text:
            factors.append(f"中风险关键词: {keyword}")

    # 检查高风险关键词
    high_factors = []
    for keyword in RISK_KEYWORDS["high"]:
        if keyword in text:
            high_factors.append(f"高风险关键词: {keyword}")

    factors.extend(high_factors)

    # 确定风险等级
    if high_factors:
        return "high", factors
    elif factors:
        return "medium", factors
    else:
        return "low", []


# ==================== 综合审核 ====================

def screen_content(text: str) -> ScreenResult:
    """
    内容审核综合函数
    规则初筛: 身份证号、手机号、违禁词、精确住址
    返回审核结果
    """
    result = ScreenResult()
    result.cleaned_text = text

    violations = []

    # 1. 检测身份证号
    id_cards = detect_id_card(text)
    if id_cards:
        violations.append(f"检测到身份证号({len(id_cards)}处)，请删除后再发布")
        for card in id_cards:
            masked = card[:6] + "*" * 8 + card[-4:]
            result.cleaned_text = result.cleaned_text.replace(card, masked)

    # 2. 检测手机号
    phones = detect_phone(text)
    if phones:
        violations.append(f"检测到手机号({len(phones)}处)，公开帖不允许暴露联系方式")
        for phone in phones:
            masked = phone[:3] + "*" * 4 + phone[-4:]
            result.cleaned_text = result.cleaned_text.replace(phone, masked)

    # 3. 检测微信号
    wechats = detect_wechat(text)
    if wechats:
        violations.append(f"检测到微信号({len(wechats)}处)，请在双向确认成队后再交换联系方式")
        for wechat in wechats:
            result.cleaned_text = result.cleaned_text.replace(wechat, "[联系方式已隐藏]")

    # 4. 检测QQ号
    qqs = detect_qq(text)
    if qqs:
        violations.append(f"检测到QQ号({len(qqs)}处)，请在双向确认成队后再交换联系方式")
        for qq in qqs:
            result.cleaned_text = result.cleaned_text.replace(qq, "[联系方式已隐藏]")

    # 4.5 检测邮箱
    emails = EMAIL_PATTERN.findall(text)
    if emails:
        violations.append(f"检测到邮箱({len(emails)}处)，公开帖不允许暴露联系方式")
        for email in emails:
            result.cleaned_text = result.cleaned_text.replace(email, "[联系方式已隐藏]")

    # 5. 检测精确住址
    addresses = detect_address(text)
    if addresses:
        violations.append(f"检测到精确住址({len(addresses)}处)，请勿暴露详细地址")
        for addr in addresses:
            result.cleaned_text = result.cleaned_text.replace(addr, "[地址已隐藏]")

    # 6. 检测违禁词
    banned = check_banned_words(text)
    if banned:
        violations.append(f"检测到违禁词: {', '.join(banned)}")

    # 7. 风险分级
    risk_level, risk_factors = assess_risk(text)

    # 设置结果
    result.has_violations = len(violations) > 0
    result.violations = violations
    result.risk_level = risk_level
    result.risk_factors = risk_factors

    # 生成建议
    if violations:
        result.suggestions.append("请删除帖文中的敏感信息后重新发布")
    if risk_level == "medium":
        result.suggestions.append("此帖涉及线下/金钱/夜间等场景，建议添加安全提示")
    elif risk_level == "high":
        result.suggestions.append("此帖存在高风险因素，将进入人工复核队列")
    if not violations and risk_level == "low":
        result.suggestions.append("内容审核通过")

    return result


def screen_post_content(title: str, description: str) -> ScreenResult:
    """对帖子标题和描述进行审核"""
    full_text = f"{title}\n{description or ''}"
    return screen_content(full_text)
