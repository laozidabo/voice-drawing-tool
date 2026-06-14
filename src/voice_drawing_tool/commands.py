import re
import difflib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple


ZH_COLOR_MAP = {
    '红': 'red', '红色': 'red', '赤': 'red', '朱': 'red',
    '蓝': 'blue', '蓝色': 'blue', '靛': 'blue',
    '绿': 'green', '绿色': 'green', '翠': 'green',
    '黑': 'black', '黑色': 'black', '墨': 'black',
    '白': 'white', '白色': 'white',
    '黄': 'yellow', '黄色': 'yellow',
    '橙': 'orange', '橙色': 'orange', '橘': 'orange',
    '紫': 'purple', '紫色': 'purple',
    '粉': 'pink', '粉色': 'pink', '桃': 'pink',
    '棕': 'brown', '棕色': 'brown', '褐': 'brown',
    '灰': 'gray', '灰色': 'gray',
    '青': 'cyan', '青色': 'cyan',
    '洋红': 'magenta', '品红': 'magenta',
    '海军': 'navy', '海军蓝': 'navy',
    '茶': 'teal', '茶色': 'teal',
    '靛蓝': 'indigo', '靛青': 'indigo',
    '紫罗蓝': 'violet',
    '石灰': 'lime', '柠檬': 'lime', '浅绿': 'lime',
    '金': 'gold', '金色': 'gold',
    '银': 'silver', '银色': 'silver',
}

_ZH_EN_MAP = {
    '画一个': 'draw a', '画一条': 'draw a', '画一座': 'draw a', '画个': 'draw a', '画': 'draw ',
    '画朵': 'draw a', '画棵': 'draw a', '画辆': 'draw a', '画座': 'draw a', '画条': 'draw a',
    '画在': 'at ', '画到': 'at ', '画于': 'at ',
    '换一个': 'draw a', '换一张': 'draw a', '换个': 'draw a',
    '来一个': 'draw a', '来一张': 'draw a', '来个': 'draw a', '来': 'draw ',
    '整一个': 'draw a', '搞一个': 'draw a', '弄一个': 'draw a',
    '整': 'draw', '搞': 'draw', '弄': 'draw',
    '来颗': 'draw a', '整条': 'draw a', '来点': 'draw a',
    '颗': '', '个': '',
    '这个': '',
    '帮我': '', '给我': '',
    '我想要画': 'draw', '我想画': 'draw', '我要画': 'draw',
    '我要': 'draw', '我想': 'draw', '我想要': 'draw',
    '能不能': 'draw', '可以画': 'draw',
    '请': '',
    '一下': ' ',
    '写': 'write',
    '绘制': 'draw', '创建': 'draw', '制作': 'draw',
    '的': ' ',
    '设置': 'set', '设为': 'set', '调整为': 'set',
    '清空': 'clear', '擦除': 'clear', '清屏': 'clear',
    '导出': 'save',
    '撤销': 'undo', '回退': 'undo',
    '重做': 'redo', '恢复': 'redo',
    '圆': 'circle', '圆形': 'circle',
    '椭圆': 'ellipse', '椭圆形': 'ellipse',
    '线': 'line', '直线': 'line',
    '矩形': 'rectangle', '长方形': 'rectangle',
    '正方形': 'square', '正方': 'square', '方形': 'square', '方': 'square',
    '三角形': 'triangle',
    '星': 'star', '星形': 'star', '五角星': 'star',
    '多边形': 'polygon', '多角形': 'polygon',
    '六边形': 'hexagon', '六角形': 'hexagon',
    '菱形': 'diamond', '判断框': 'diamond',
    '箭头': 'arrow', '箭头线': 'arrow', '带箭头': 'arrow',
    '圆角矩形': 'rounded rectangle', '圆角框': 'rounded rectangle', '圆角': 'rounded',
    '笑脸': 'smiley',
    '小人': 'person', '人': 'person', '画个小人': 'person', '画个人': 'person',
    '流程': 'flowchart', '流程图': 'flowchart', '开始': 'flowchart', '结束': 'flowchart',
    '环': 'ring', '圆环': 'ring', '环形': 'ring', '空心圆': 'ring',
    '填充的': 'filled', '实心的': 'filled', '填充': 'filled', '实心': 'filled',
    '空心': 'hollow', '不填充': 'hollow',
    '从 ': 'from ', '从坐标': 'from ',
    '到 ': 'to ', ' 到 ': ' to ',
    '在 ': 'at ', '坐标 ': '',
    '半径': 'radius',
    '颜色': 'color', '颜色为': 'color to',
    '宽度': 'width', '粗细': 'width',
    '粗一点': 'thick', '粗点': 'thick', '粗线条': 'thick', '加粗': 'thick',
    '细一点': 'thin', '细点': 'thin', '加细': 'thin',
    '文字': 'text', '文本': 'text',
    '画布': 'canvas', '整张画布': 'canvas', '画面': 'canvas',
    '房子': 'house', '房屋': 'house',
    '正': '',
    '圈': 'circle',
    '最基本的': '', '最简单的': '', '基本的': '',
    '树': 'tree', '树木': 'tree',
    '车': 'car', '汽车': 'car',
    '太阳': 'sun', '太阳公公': 'sun',
    '山': 'mountain', '山脉': 'mountain',
    '花': 'flower', '花朵': 'flower', '一朵花': 'flower', '花儿': 'flower',
    '笑脸': 'smiley',
    '保存': 'save', '另存为': 'save',
    '宽度为': 'width', '宽度设置成': 'width',
    '清除': 'clear', '全部清除': 'clear', '重新来': 'clear',
    '顶点': 'points',
    '水平半径': 'rx',
    '垂直半径': 'ry',
    '一': 'a',
    '棵': '', '辆': '', '座': '',
    '一个': 'a', '一条': 'a', '一座': 'a', '一朵': 'a', '个': 'a', '只': '',
    '一百': '100', '两百': '200', '三百': '300', '四百': '400', '五百': '500',
    '为 ': 'to ', '为': 'to ',
    '把': '', '将': '', '刚': '', '给': '', '在': '',
    '水平': 'horizontal', '垂直': 'vertical',
    '斜': 'diagonal', '斜着': 'diagonal', '斜的': 'diagonal',
    '上一步': 'undo', '上一个': 'prev',
    '挪': 'move', '移到': 'move',
    '上面': 'up', '下面': 'down',
    '左边': 'centerleft', '右边': 'centerright', '左侧': 'centerleft', '右侧': 'centerright',
    '左上': 'topleft', '右上': 'topright', '左下': 'bottomleft', '右下': 'bottomright',
    '最左': 'centerleft', '最右': 'centerright', '最上': 'topcenter', '最下': 'bottomcenter',
    '中间': 'center', '正中间': 'center', '中央': 'center', '居中': 'center',
    '左上角': 'topleft', '左下角': 'bottomleft',
    '右上角': 'topright', '右下角': 'bottomright',
    '上中': 'topcenter', '中上': 'topcenter',
    '下中': 'bottomcenter', '中下': 'bottomcenter',
    '左中': 'centerleft', '中左': 'centerleft',
    '右中': 'centerright', '中右': 'centerright',
    '偏左': 'offset left', '偏右': 'offset right',
    '偏上': 'offset up', '偏下': 'offset down',
    '靠左': 'align left', '靠右': 'align right',
    '靠上': 'align top', '靠下': 'align bottom',
    '最左边': 'align left', '最右边': 'align right',
    '最上面': 'align top', '最下面': 'align bottom',
    '背景': 'background', '底色': 'background',
    '新建': 'new', '新的': 'new',
    '删除': 'delete', '移除': 'delete', '去掉': 'delete',
    '复制': 'copy', '拷贝': 'copy',
    '上': '', '下': '', '左': '', '右': '',
    '随便': '', '就行': '', '简单': '',
    '大': 'big', '小': 'small', '中': 'medium',
    '一个图形': 'shape', '图形': 'shape',
    '那个图形': 'prev',
    '往右': 'offset right', '往左': 'offset left', '往上': 'offset up', '往下': 'offset down',
    '向右': 'offset right', '向左': 'offset left', '向上': 'offset up', '向下': 'offset down',
    '右移': 'move right', '左移': 'move left', '上移': 'move up', '下移': 'move down',
    '移': 'move', '移动': 'move',
    '一点': 'a little',
    '一倍': '2 times', '两倍': '2 times', '二倍': '2 times', '三倍': '3 times',
    '一半': 'half',
    '大一点': 'bigger', '大点': 'bigger', '放大': 'bigger',
    '小一点': 'smaller', '小点': 'smaller', '缩小': 'smaller',
    '就这样': 'confirm', '完成了': 'confirm', '完工': 'confirm', '好': 'confirm',
    '确认': 'confirm', '可以': 'confirm', '不错': 'confirm',
    '光标': 'cursor', '鼠标': 'cursor', '指针': 'cursor',
    '光': 'cursor',
    '光标移到': 'cursor move', '光标移动到': 'cursor move',
    '把光标': 'cursor', '将光标': 'cursor',
    '当前': 'here', '位置': 'here', '白色位置': 'cursor',
    '这里': 'here', '这儿': 'here', '在那': 'cursor',
    # Multi-command connectors
    '和': ' and ', '还有': ' and ', '与': ' and ',
    '然后': ' then ', '接着': ' then ', '再然后': ' then ',
    '，': ' and ', '；': ' and ',
    # Shortcut aliases for common commands
    '圆圈': 'circle', '圈圈': 'circle', '小圆': 'small circle', '大圆': 'big circle', '中圆': 'medium circle',
    '方块': 'square', '小方': 'small square', '大方': 'big square', '中方': 'medium square',
    '三角': 'triangle', '小三角': 'small triangle', '大三角': 'big triangle',
    '星星': 'star', '小星': 'small star', '大星': 'big star',
    '线条': 'line', '小线': 'short line', '短线': 'short line', '长线': 'long line',
    '小房子': 'small house', '大房子': 'big house',
    '小树': 'small tree', '大树': 'big tree',
    '小车': 'small car', '大车': 'big car',
    '小花': 'small flower', '大花': 'big flower',
    '小太阳': 'small sun', '大太阳': 'big sun',
    '小山': 'small mountain', '高山': 'big mountain',
    '再来一个': 'repeat variation', '再画一个': 'repeat variation',
    '再来一遍': 'repeat variation', '重复': 'repeat variation',
    '同样的': 'repeat variation', '再来': 'repeat variation',
    # Animation commands
    '下雨': 'rain', '下点雨': 'rain', '开始下雨': 'rain',
    '停雨': 'stop rain', '雨停': 'stop rain', '雨停了': 'stop rain',
    '开花': 'grow flower', '开朵花': 'grow flower', '开花了': 'grow flower',
    '长成大树': 'grow tree', '长树': 'grow tree', '长出一棵树': 'grow tree',
    '萤火虫': 'fireflies', '放萤火虫': 'fireflies',
    '烟花': 'fireworks', '放烟花': 'fireworks', '放个烟花': 'fireworks',
    '闪烁': 'sparkle', '闪一下': 'sparkle', '闪闪': 'sparkle', '闪': 'sparkle',
    '魔法阵': 'magic circle', '魔法': 'magic circle', '画魔法阵': 'magic circle',
    '流星': 'starfall', '流星雨': 'starfall', '放流星': 'starfall',
    '下雪': 'snow', '下雪了': 'snow', '雪': 'snow', '飘雪': 'snow',
    '停雪': 'stop snow', '雪停': 'stop snow', '停止下雪': 'stop snow',
    '泡泡': 'bubbles', '吹泡泡': 'bubbles', '放泡泡': 'bubbles',
    '停泡泡': 'stop bubbles', '泡泡停': 'stop bubbles', '停止泡泡': 'stop bubbles',
    '极光': 'aurora', '放极光': 'aurora', '画极光': 'aurora',
    '停极光': 'stop aurora', '极光停': 'stop aurora', '停止极光': 'stop aurora',
    '停止动画': 'stop animation', '停动画': 'stop animation', '停止所有动画': 'stop animation',
}

_SPEECH_FIX_MAP = {
    # === 形状名称纠错 ===
    '话': '画',
    '园': '圆', '元': '圆', '缘': '圆', '员': '圆', '原': '圆',
    '圈圈': '圆', '全': '圆',
    '据形': '矩形', '据型': '矩形', '举形': '矩形', '巨形': '矩形',
    '天充': '填充', '填中': '填充', '田充': '填充',
    '三圆形': '三角形', '三园形': '三角形', '三脚形': '三角形',
    '三发型': '三角形', '三甲型': '三角形', '三角色': '三角形',
    '三园': '三角', '三圆': '三角', '山圆': '三角', '山角': '三角',
    '山形': '三角', '伞形': '三角', '三型': '三角', '散角': '三角',
    '五角形': '五角星', '五角新': '五角星', '五角行': '五角星',
    '五角心': '五角星', '五角兴': '五角星', '五星': '五角星',
    '正方型': '正方形', '正方式': '正方形', '正方向': '正方形',
    '正方行': '正方形', '征方形': '正方形',
    '长方式': '长方形', '长发型': '长方形',
    '长方型': '长方形', '长方向': '长方形', '长方行': '长方形',
    '脱圆': '椭圆', '头圆': '椭圆', '扭圆': '椭圆', '拖圆': '椭圆',
    '驼圆': '椭圆', '妥圆': '椭圆', '椭元': '椭圆', '椭缘': '椭圆',
    '零形': '菱形', '铃形': '菱形', '零行': '菱形',
    '灵形': '菱形', '领形': '菱形', '令形': '菱形',
    '左边形': '左边',
    '空心圆': '圆',
    '六边形': '六边形', '六边行': '六边形', '溜边形': '六边形',
    '多边形': '多边形', '多边行': '多边形', '躲边形': '多边形',
    '圆角矩形': '圆角矩形', '圆角据形': '圆角矩形',

    # === 颜色纠错 ===
    '男色': '蓝色', '兰色': '蓝色', '蓝蓝': '蓝色', '兰': '蓝',
    '鸿': '红', '宏': '红', '轰': '红', '洪': '红',
    '皇': '黄', '慌': '黄', '煌': '黄', '凰': '黄',
    '嘿': '黑', '赫': '黑', '核': '黑',
    # Protect "长成" before individual "成" → "橙" mapping
    '长成': '长成',
    '呈': '橙', '成': '橙', '城': '橙', '诚': '橙',
    '宗色': '棕色', '综色': '棕色', '总色': '棕色',
    '辉色': '灰色', '灰色': '灰色', '回色': '灰色', '会色': '灰色',
    '录色': '绿色', '虑色': '绿色', '律色': '绿色',
    '子色': '紫色', '自色': '紫色', '资色': '紫色',
    '粉色': '粉色', '奋色': '粉色', '坟色': '粉色',
    '茶色': '茶色', '查色': '茶色',

    # === 操作纠错 ===
    '吃消': '撤销', '撤消': '撤销', '彻消': '撤销', '车消': '撤销',
    '宝存': '保存', '保村': '保存', '报存': '保存', '保寸': '保存',
    '清处': '清除', '清出': '清除', '清除': '清除', '轻除': '清除',
    '十心': '实心', '食心': '实心', '石心': '实心', '时心': '实心',
    '空芯': '空心', '空新': '空心', '空欣': '空心', '空信': '空心',
    '重做': '重做', '从做': '重做', '虫做': '重做',

    # === 位置/方向纠错 ===
    '左上': '左上', '做上': '左上', '昨上': '左上',
    '右下': '右下', '有下': '右下', '又下': '右下',
    '正中间': '正中间', '正中见': '正中间', '中间': '正中间',

    # === 样式纠错 ===
    '填充': '填充', '天充': '填充', '田充': '填充',
    '粗一点': '粗一点', '粗一店': '粗一点', '粗一电': '粗一点',
    '细一点': '细一点', '细一店': '细一点', '细一电': '细一点',

    # === 场景纠错 ===
    '房子': '房子', '放子': '房子', '方子': '房子',
    '太阳': '太阳', '大阳': '太阳', '太羊': '太阳',
    '汽车': '汽车', '骑车': '汽车', '七车': '汽车',

    # === 常见语音识别噪音 ===
    '的的': '的', '了了': '了', '是是': '是',
    '然后然后': '然后', '就是就是': '就是',
    # === Whisper 常见误识别 ===
    '话一个': '画一个', '化一个': '画一个', '画一格': '画一个',
    '花圆': '画圆', '花方': '画方', '花三角': '画三角',
    '红远': '红圆', '红元': '红圆', '红缘': '红圆',
    '蓝房': '蓝方', '兰方': '蓝方', '兰房': '蓝方',
    '绿山角': '绿三角', '绿山角形': '绿三角形',
    '黄星': '黄星', '黄心': '黄星',
    '画房子': '画房子', '画房子': '画房子', '画芳子': '画房子',
    '画树': '画树', '画术': '画树', '画数': '画树',
    '画车': '画车', '画扯': '画车', '画彻': '画车',
    '画太阳': '画太阳', '画大阳': '画太阳', '画太羊': '画太阳',
    '画花': '画花', '画华': '画花',
    '画山': '画山', '画三': '画山',
    '撤销': '撤销', '吃消': '撤销', '撤消': '撤销',
    '重做': '重做', '从做': '重做', '虫做': '重做',
    '清空': '清空', '清控': '清空', '清空': '清空',
    '保存': '保存', '宝存': '保存', '保村': '保存',
    '帮助': '帮助', '帮主': '帮助', '帮住': '帮助',
}
_SPEECH_FIX_PATTERNS = sorted(_SPEECH_FIX_MAP.keys(), key=len, reverse=True)
_SPEECH_FIX_RE = re.compile('|'.join(re.escape(zh) for zh in _SPEECH_FIX_PATTERNS))


def fix_speech_text(text: str) -> str:
    result = _SPEECH_FIX_RE.sub(lambda m: _SPEECH_FIX_MAP[m.group(0)], text)
    result = re.sub(r'[嗯啊呃哦呀哈]+', '', result)
    result = re.sub(r'(.)\1{2,}', r'\1', result)
    # Remove filler "帮我" "给我" "请" at start of command
    result = re.sub(r'^\s*(帮我|给我|请)\s*', '', result)
    # Remove "的" between color and shape: "红色的圆" -> "红圆"
    _colors = '红蓝绿黄紫橙粉棕灰黑白赤朱靛翠墨'
    result = re.sub(rf'([{_colors}])色?的([一-鿿])', r'\1\2', result)
    # Remove "一个" before shapes: "画一个圆" -> "画圆"
    result = re.sub(r'(画|整|搞)一个([一-鿿])', r'\1\2', result)
    if re.match(r'^个个[红蓝绿黄紫橙粉棕灰黑白]', result):
        result = '画' + result
    if re.match(r'^[一两][个条座]', result):
        result = '画' + result
    # Bare color+shape without verb: "红圆" -> "画红圆"
    if re.match(rf'^[{_colors}]色?[一-鿿]', result) and not re.match(r'^(画|整|搞|换|来|写|绘制|创建|制作|设置|清空|导出|撤销|重做|保存|清除|删除|复制|移动|帮我|给我|请|我)', result):
        result = '画' + result
    return result


_ZH_EN_ALL = {}
_ZH_EN_ALL.update(ZH_COLOR_MAP)
_ZH_EN_ALL.update(_ZH_EN_MAP)
_ZH_PATTERNS = sorted(_ZH_EN_ALL.keys(), key=len, reverse=True)
_ZH_RE = re.compile('|'.join(re.escape(zh) for zh in _ZH_PATTERNS))


def zh_to_en(text: str) -> str:
    def replacer(m):
        zh = m.group(0)
        return ' ' + _ZH_EN_ALL.get(zh, zh) + ' '
    result = _ZH_RE.sub(replacer, text)
    result = _replace_zh_numbers(result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result


_ZH_NUM_PAT = re.compile(r'[一二三四五六七八九十百千万亿零]+')


def _replace_zh_numbers(text: str) -> str:
    # Collapse any whitespace between Chinese numeral characters first,
    # so that "十 五" becomes "十五" before conversion.
    collapsed = re.sub(
        r'(?<=[一二三四五六七八九十百千万亿零])\s+(?=[一二三四五六七八九十百千万亿零])',
        '',
        text,
    )

    def repl(m):
        raw = m.group(0)
        return str(zh_number_to_int(raw))
    return _ZH_NUM_PAT.sub(repl, collapsed)


COLOR_MAP = {
    'red': (0, 0, 255),
    'blue': (255, 0, 0),
    'green': (0, 255, 0),
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'yellow': (0, 255, 255),
    'orange': (0, 165, 255),
    'purple': (128, 0, 128),
    'pink': (147, 20, 255),
    'brown': (42, 42, 165),
    'gray': (128, 128, 128),
    'cyan': (255, 255, 0),
    'magenta': (255, 0, 255),
    'navy': (128, 0, 0),
    'teal': (128, 128, 0),
    'indigo': (130, 0, 75),
    'violet': (211, 130, 238),
    'lime': (0, 255, 128),
    'gold': (41, 215, 255),
    'silver': (192, 192, 192),
    'skin': (180, 210, 240),
    'darkbrown': (30, 65, 130),
}

COLOR_NAMES = '|'.join(COLOR_MAP.keys())

COLOR_NAME_LIST = sorted(COLOR_MAP.keys(), key=len, reverse=True)


def resolve_color(name: str) -> tuple:
    name = name.lower().strip()
    if name in COLOR_MAP:
        return COLOR_MAP[name]
    matches = difflib.get_close_matches(name, COLOR_MAP.keys(), n=1, cutoff=0.6)
    if matches:
        return COLOR_MAP[matches[0]]
    return COLOR_MAP['red']


def extract_numbers(text: str) -> List[int]:
    return [int(n) for n in re.findall(r'\d+', text)]


_ZH_DIGITS = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
              '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_ZH_UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10000}


def zh_number_to_int(text: str) -> int:
    text = text.replace(' ', '')
    total = 0
    cur = 0
    for ch in text:
        if ch in _ZH_DIGITS:
            cur = _ZH_DIGITS[ch]
        elif ch in _ZH_UNITS:
            unit = _ZH_UNITS[ch]
            if cur == 0:
                cur = 1
            total += cur * unit
            cur = 0
        else:
            if cur:
                total += cur
                cur = 0
    if cur:
        total += cur
    return total if total != 0 else 1


def parse_number_word(text: str) -> int:
    text = text.strip().lower()
    m = re.match(r'(\d+)', text)
    if m:
        return int(m.group(1))
    return zh_number_to_int(text)


class Command(ABC):
    @abstractmethod
    def execute(self, canvas) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass


class CompositeCommand(Command):
    def __init__(self, commands: List[Command], description: str):
        self.commands = commands
        self._description = description

    def execute(self, canvas) -> str:
        results = []
        for cmd in self.commands:
            try:
                results.append(cmd.execute(canvas))
            except Exception as e:
                results.append(f"Error: {e}")
        return f"{self._description}: {'; '.join(results)}"

    def get_description(self) -> str:
        return self._description


class DrawCircleCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 200))
        self.y = int(params.get('y', 200))
        self.radius = int(params.get('radius', 50))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'red')

    def execute(self, canvas) -> str:
        canvas.draw_circle(self.x, self.y, self.radius, color=self.color, width=self.width)
        return f"circle at ({self.x},{self.y}) r={self.radius}"

    def get_description(self) -> str:
        return f"draw {self.color_name} circle at ({self.x}, {self.y})"


class DrawEllipseCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 200))
        self.y = int(params.get('y', 200))
        self.rx = int(params.get('rx', 80))
        self.ry = int(params.get('ry', 50))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'red')

    def execute(self, canvas) -> str:
        canvas.draw_ellipse(self.x, self.y, self.rx, self.ry, color=self.color, width=self.width)
        return f"ellipse at ({self.x},{self.y}) rx={self.rx} ry={self.ry}"

    def get_description(self) -> str:
        return f"draw {self.color_name} ellipse at ({self.x}, {self.y})"


class DrawLineCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x1 = int(params.get('x1', 0))
        self.y1 = int(params.get('y1', 0))
        self.x2 = int(params.get('x2', 100))
        self.y2 = int(params.get('y2', 100))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'blue')

    def execute(self, canvas) -> str:
        canvas.draw_line(self.x1, self.y1, self.x2, self.y2, color=self.color, width=self.width)
        return f"line from ({self.x1},{self.y1}) to ({self.x2},{self.y2})"

    def get_description(self) -> str:
        return f"draw {self.color_name} line"


class DrawRectangleCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x1 = int(params.get('x1', 50))
        self.y1 = int(params.get('y1', 50))
        self.x2 = int(params.get('x2', 200))
        self.y2 = int(params.get('y2', 200))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'green')

    def execute(self, canvas) -> str:
        canvas.draw_rectangle(self.x1, self.y1, self.x2, self.y2,
                               color=self.color, width=self.width, filled=self.filled)
        return f"rectangle from ({self.x1},{self.y1}) to ({self.x2},{self.y2})"

    def get_description(self) -> str:
        return f"draw {self.color_name} rectangle"


class DrawTriangleCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        pts = extract_numbers(params.get('points', ''))
        self.pts = pts if len(pts) == 6 else [100, 50, 50, 150, 150, 150]
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'purple')

    def execute(self, canvas) -> str:
        canvas.draw_polygon(self.pts, color=self.color, width=self.width, filled=self.filled)
        return f"triangle at {self.pts[:2]}"

    def get_description(self) -> str:
        return f"draw {self.color_name} triangle"


class DrawPolygonCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        pts = extract_numbers(params.get('points', ''))
        self.pts = pts if len(pts) >= 4 else [100, 50, 150, 100, 100, 150, 50, 100]
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'purple')

    def execute(self, canvas) -> str:
        canvas.draw_polygon(self.pts, color=self.color, width=self.width, filled=self.filled)
        return f"polygon"

    def get_description(self) -> str:
        return f"draw {self.color_name} polygon"


class DrawStarCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 200))
        self.y = int(params.get('y', 200))
        self.r = int(params.get('radius', 80))
        self.points = int(params.get('points', 5))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'gold')

    def execute(self, canvas) -> str:
        canvas.draw_star(self.x, self.y, self.r, self.points, color=self.color, width=self.width)
        return f"star at ({self.x},{self.y}) r={self.r}"

    def get_description(self) -> str:
        return f"draw {self.color_name} star"


class DrawTextCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 50))
        self.y = int(params.get('y', 50))
        self.text = params.get('text', 'Hello')
        self.size = int(params.get('size', 1))
        self.color = resolve_color(params.get('color', ''))
        self.color_name = params.get('color', 'black')

    def execute(self, canvas) -> str:
        canvas.draw_text(self.x, self.y, self.text, size=self.size, color=self.color)
        return f"text '{self.text}' at ({self.x},{self.y})"

    def get_description(self) -> str:
        return f"write '{self.text}'"


class DrawFilledCircleCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 200))
        self.y = int(params.get('y', 200))
        self.radius = int(params.get('radius', 50))
        self.color = resolve_color(params.get('color', ''))
        self.color_name = params.get('color', 'red')

    def execute(self, canvas) -> str:
        canvas.draw_circle(self.x, self.y, self.radius, color=self.color, width=-1)
        return f"filled circle at ({self.x},{self.y}) r={self.radius}"

    def get_description(self) -> str:
        return f"draw filled {self.color_name} circle"


class DrawSquareCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        side = int(params.get('side', 200))
        cx = int(params.get('x', 400))
        cy = int(params.get('y', 300))
        self.x1 = cx - side // 2
        self.y1 = cy - side // 2
        self.x2 = cx + side // 2
        self.y2 = cy + side // 2
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'green')

    def execute(self, canvas) -> str:
        canvas.draw_rectangle(self.x1, self.y1, self.x2, self.y2,
                               color=self.color, width=self.width, filled=self.filled)
        return f"square at center ({(self.x1 + self.x2) // 2},{(self.y1 + self.y2) // 2})"

    def get_description(self) -> str:
        return f"draw {self.color_name} square"


class DrawRingCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x = int(params.get('x', 200))
        self.y = int(params.get('y', 200))
        self.r_outer = int(params.get('radius', 60))
        self.r_inner = int(params.get('inner', 30))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'red')

    def execute(self, canvas) -> str:
        canvas.draw_ring(self.x, self.y, self.r_outer, self.r_inner, color=self.color, width=self.width)
        return f"ring at ({self.x},{self.y}) outer={self.r_outer} inner={self.r_inner}"

    def get_description(self) -> str:
        return f"draw {self.color_name} ring"


class DrawRegularPolygonCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.cx = int(params.get('cx', 400))
        self.cy = int(params.get('cy', 300))
        self.r = int(params.get('radius', 80))
        self.sides = int(params.get('sides', 6))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'purple')

    def execute(self, canvas) -> str:
        canvas.draw_regular_polygon(self.cx, self.cy, self.r, self.sides,
                                     color=self.color, width=self.width, filled=self.filled)
        return f"{self.sides}-gon at ({self.cx},{self.cy}) r={self.r}"

    def get_description(self) -> str:
        return f"draw {self.color_name} {self.sides}-gon"


class SetColorCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.color_name = params.get('color', 'red')
        self.color = resolve_color(self.color_name)

    def execute(self, canvas) -> str:
        canvas.pen_color = self.color
        canvas.pen_color_name = self.color_name
        return f"color set to {self.color_name}"

    def get_description(self) -> str:
        return f"set color to {self.color_name}"


class SetWidthCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.width = int(params.get('width', 2))

    def execute(self, canvas) -> str:
        canvas.pen_width = self.width
        return f"width set to {self.width}"

    def get_description(self) -> str:
        return f"set width to {self.width}"


class ClearCanvasCommand(Command):
    def __init__(self, params: Dict[str, str] = None):
        pass

    def execute(self, canvas) -> str:
        canvas.clear()
        return "canvas cleared"

    def get_description(self) -> str:
        return "clear canvas"


class UndoCommand(Command):
    def execute(self, canvas) -> str:
        if canvas.undo():
            return "undone"
        return "nothing to undo"

    def get_description(self) -> str:
        return "undo"


class RedoCommand(Command):
    def execute(self, canvas) -> str:
        if canvas.redo():
            return "redone"
        return "nothing to redo"

    def get_description(self) -> str:
        return "redo"


class SaveCommand(Command):
    def __init__(self, params: Dict[str, str] = None):
        self.filename = params.get('filename', 'drawing.png') if params else 'drawing.png'

    def execute(self, canvas) -> str:
        canvas.save(self.filename)
        return f"saved to {self.filename}"

    def get_description(self) -> str:
        return f"save to {self.filename}"


class SetBackgroundCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.color = resolve_color(params.get('color', ''))
        self.color_name = params.get('color', 'gray')

    def execute(self, canvas) -> str:
        canvas.set_background(self.color)
        return f"background set to {self.color_name}"

    def get_description(self) -> str:
        return f"set background to {self.color_name}"


class MoveLastCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.dx = int(params.get('dx', 0))
        self.dy = int(params.get('dy', 0))

    def _shift(self, val, dx, dy):
        nums = extract_numbers(val)
        for i in range(0, len(nums), 2):
            nums[i] += dx
        for i in range(1, len(nums), 2):
            nums[i] += dy
        return ' '.join(str(n) for n in nums)

    def execute(self, canvas) -> str:
        if canvas.last_command_type is None:
            return "nothing to move (draw something first)"
        cmd_type = canvas.last_command_type
        params = dict(canvas.last_command_params)

        if cmd_type is CompositeCommand and 'sub_commands' in params:
            sub_list = params['sub_commands']
            canvas.undo()
            results = []
            sub_commands = []
            for sub_type, sub_params in sub_list:
                shifted = dict(sub_params)
                for key in ('x', 'cx', 'x1', 'x2'):
                    if key in shifted:
                        shifted[key] = str(int(shifted[key]) + self.dx)
                for key in ('y', 'cy', 'y1', 'y2'):
                    if key in shifted:
                        shifted[key] = str(int(shifted[key]) + self.dy)
                if 'points' in shifted:
                    shifted['points'] = self._shift(shifted['points'], self.dx, self.dy)
                sub_cmd = sub_type(shifted)
                sub_commands.append(sub_cmd)
                results.append(sub_cmd.execute(canvas))
            canvas.last_command_type = CompositeCommand
            canvas.last_command_params = {'sub_commands': [(type(sc), getattr(sc, 'params', {})) for sc in sub_commands]}
            return f"scene moved by ({self.dx},{self.dy})"

        for key in ('x', 'cx', 'x1', 'x2'):
            if key in params:
                params[key] = str(int(params[key]) + self.dx)
        for key in ('y', 'cy', 'y1', 'y2'):
            if key in params:
                params[key] = str(int(params[key]) + self.dy)
        if 'points' in params:
            params['points'] = self._shift(params['points'], self.dx, self.dy)
        canvas.undo()
        cmd = cmd_type(params)
        result = cmd.execute(canvas)
        canvas.last_command_type = type(cmd)
        canvas.last_command_params = params
        return f"moved by ({self.dx},{self.dy})"

    def get_description(self) -> str:
        return f"move by ({self.dx}, {self.dy})"


class ScaleLastCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.factor = float(params.get('factor', 1.0))

    def _scale(self, val, factor):
        nums = extract_numbers(val)
        if not nums:
            return val
        cxs = sum(nums[0::2]) / max(len(nums)//2, 1)
        cys = sum(nums[1::2]) / max(len(nums)//2, 1)
        for i in range(0, len(nums), 2):
            nums[i] = max(1, int(cxs + (nums[i] - cxs) * factor))
        for i in range(1, len(nums), 2):
            nums[i] = max(1, int(cys + (nums[i] - cys) * factor))
        return ' '.join(str(n) for n in nums)

    def execute(self, canvas) -> str:
        if canvas.last_command_type is None:
            return "nothing to scale (draw something first)"
        cmd_type = canvas.last_command_type
        params = dict(canvas.last_command_params)

        if cmd_type is CompositeCommand and 'sub_commands' in params:
            sub_list = params['sub_commands']
            canvas.undo()
            results = []
            sub_commands = []
            for sub_type, sub_params in sub_list:
                scaled = dict(sub_params)
                for key in ('radius', 'rx', 'ry', 'side', 'r_outer', 'r_inner'):
                    if key in scaled:
                        scaled[key] = str(max(2, int(int(scaled[key]) * self.factor)))
                if 'points' in scaled:
                    scaled['points'] = self._scale(scaled['points'], self.factor)
                sub_cmd = sub_type(scaled)
                sub_commands.append(sub_cmd)
                results.append(sub_cmd.execute(canvas))
            canvas.last_command_type = CompositeCommand
            canvas.last_command_params = {'sub_commands': [(type(sc), getattr(sc, 'params', {})) for sc in sub_commands]}
            return f"scene scaled x{self.factor}"

        for key in ('radius', 'rx', 'ry', 'side', 'r_outer', 'r_inner'):
            if key in params:
                params[key] = str(max(2, int(int(params[key]) * self.factor)))
        if 'points' in params:
            params['points'] = self._scale(params['points'], self.factor)
        canvas.undo()
        cmd = cmd_type(params)
        result = cmd.execute(canvas)
        canvas.last_command_type = type(cmd)
        canvas.last_command_params = params
        return f"scaled x{self.factor}"

    def get_description(self) -> str:
        return f"scale x{self.factor}"


class ConfirmCommand(Command):
    def execute(self, canvas) -> str:
        return "confirmed"

    def get_description(self) -> str:
        return "confirm"


class MoveCursorCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.dx = int(params.get('dx', 0))
        self.dy = int(params.get('dy', 0))

    def execute(self, canvas) -> str:
        return f"cursor moved by ({self.dx},{self.dy})"

    def get_description(self) -> str:
        return f"move cursor by ({self.dx}, {self.dy})"


class SetCursorCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.x = int(params.get('x', 400))
        self.y = int(params.get('y', 300))

    def execute(self, canvas) -> str:
        canvas.cursor_x = self.x
        canvas.cursor_y = self.y
        return f"cursor set to ({self.x},{self.y})"

    def get_description(self) -> str:
        return f"set cursor to ({self.x}, {self.y})"


class DrawArrowLineCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x1 = int(params.get('x1', 100))
        self.y1 = int(params.get('y1', 300))
        self.x2 = int(params.get('x2', 700))
        self.y2 = int(params.get('y2', 300))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.color_name = params.get('color', 'black')

    def execute(self, canvas) -> str:
        canvas.draw_arrow_line(self.x1, self.y1, self.x2, self.y2,
                                color=self.color, width=self.width)
        return f"arrow line from ({self.x1},{self.y1}) to ({self.x2},{self.y2})"

    def get_description(self) -> str:
        return f"draw {self.color_name} arrow line"


class DrawRoundedRectCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.x1 = int(params.get('x1', 300))
        self.y1 = int(params.get('y1', 100))
        self.x2 = int(params.get('x2', 500))
        self.y2 = int(params.get('y2', 200))
        self.r = int(params.get('radius', 20))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'blue')

    def execute(self, canvas) -> str:
        canvas.draw_rounded_rect(self.x1, self.y1, self.x2, self.y2, r=self.r,
                                  color=self.color, width=self.width, filled=self.filled)
        return f"rounded rect at ({self.x1},{self.y1})-({self.x2},{self.y2})"

    def get_description(self) -> str:
        return f"draw {self.color_name} rounded rect"


class DrawDiamondCommand(Command):
    def __init__(self, params: Dict[str, str]):
        self.params = dict(params)
        self.cx = int(params.get('cx', 400))
        self.cy = int(params.get('cy', 250))
        self.rx = int(params.get('rx', 100))
        self.ry = int(params.get('ry', 60))
        self.color = resolve_color(params.get('color', ''))
        self.width = int(params.get('width', 2))
        self.filled = params.get('filled', 'false') == 'true'
        self.color_name = params.get('color', 'black')

    def execute(self, canvas) -> str:
        pts = [
            self.cx, self.cy - self.ry,
            self.cx + self.rx, self.cy,
            self.cx, self.cy + self.ry,
            self.cx - self.rx, self.cy,
        ]
        canvas.draw_polygon(pts, color=self.color, width=self.width, filled=self.filled)
        return f"diamond at ({self.cx},{self.cy})"

    def get_description(self) -> str:
        return f"draw {self.color_name} diamond"


class SceneTemplate:
    BUILDINGS = [
        ("draw a red rectangle from 100,300 to 300,500", "building body"),
        ("draw a blue rectangle from 50,200 to 100,300", "small building left"),
        ("draw a blue rectangle from 300,250 to 400,400", "small building right"),
    ]
    HOUSE = [
        ("draw a brown rectangle from 150,300 to 350,500", "house body"),
        ("draw a red triangle with points 150,300 250,200 350,300", "roof"),
        ("draw a filled yellow circle at 250,380 radius 20", "window"),
        ("draw a blue rectangle from 230,420 to 270,500", "door"),
    ]
    SUN = [
        ("draw a filled yellow circle at 400,100 radius 50", "sun"),
    ]
    SUN_RAYS = [
        ("draw a filled yellow circle at 400,100 radius 50", "sun"),
        ("draw a orange circle at 400,100 radius 70 width 3", "ray ring"),
    ]
    MOUNTAIN = [
        ("draw a green triangle with points 0,500 150,200 300,500", "mountain"),
        ("draw a green triangle with points 150,500 350,150 500,500", "mountain 2"),
    ]
    TREE = [
        ("draw a brown rectangle from 350,350 to 370,500", "trunk"),
        ("draw a green filled circle at 360,310 radius 60", "crown"),
    ]
    CAR = [
        ("draw a blue rectangle from 200,400 to 400,450", "car body"),
        ("draw a black rectangle from 220,380 to 380,420", "car roof"),
        ("draw a black filled circle at 240,460 radius 15", "wheel left"),
        ("draw a black filled circle at 360,460 radius 15", "wheel right"),
    ]
    FLOWER = [
        ("draw a yellow filled circle at 300,350 radius 20", "center"),
        ("draw a pink ellipse at 300,310 rx 15 ry 25", "petal top"),
        ("draw a pink ellipse at 330,340 rx 25 ry 15", "petal right"),
        ("draw a pink ellipse at 270,340 rx 25 ry 15", "petal left"),
        ("draw a pink ellipse at 320,370 rx 15 ry 25", "petal bottom-right"),
        ("draw a pink ellipse at 280,370 rx 15 ry 25", "petal bottom-left"),
        ("draw a green line from 300,370 to 300,550 width 4", "stem"),
    ]
    SMILEY = [
        ("draw a yellow filled circle at 400,300 radius 120", "face"),
        ("draw a black filled circle at 360,260 radius 15", "eye left"),
        ("draw a black filled circle at 440,260 radius 15", "eye right"),
        ("draw a red ellipse at 400,340 rx 60 ry 30 width 4", "mouth"),
    ]
    PERSON = [
        ("draw a skin filled circle at 400,245 radius 20", "head"),
        ("draw a darkbrown ellipse at 400,234 rx 22 ry 8 filled", "hair"),
        ("draw a skin line from 400,262 to 400,300 width 7", "body"),
        ("draw a skin line from 400,270 to 380,290 width 4", "left arm"),
        ("draw a skin line from 400,270 to 420,290 width 4", "right arm"),
        ("draw a skin line from 400,300 to 394,340 width 6", "left leg"),
        ("draw a skin line from 400,300 to 406,340 width 6", "right leg"),
    ]
    TINY_HOUSE = [
        ("draw a brown rectangle from 150,300 to 350,500", "house body"),
        ("draw a red triangle with points 150,300 250,200 350,300", "roof"),
        ("draw a filled yellow circle at 250,380 radius 20", "window"),
        ("draw a blue rectangle from 230,420 to 270,500", "door"),
    ]
    FLOWCHART = [
        ("draw a blue rounded rect from 300,50 to 500,120", "start"),
        ("draw a black arrow line from 400,120 to 400,200", "arrow1"),
        ("draw a black diamond at 400,300 rx 100 ry 60", "decision"),
        ("draw a black arrow line from 400,360 to 400,450", "arrow2"),
        ("draw a blue rounded rect from 300,450 to 500,520", "end"),
    ]
    FLOWCHART_PROCESS = [
        ("draw a blue rounded rect from 300,30 to 500,100", "start"),
        ("draw a black arrow line from 400,100 to 400,170", "arrow1"),
        ("draw a black rectangle from 260,170 to 540,240", "process1"),
        ("draw a black arrow line from 400,240 to 400,310", "arrow2"),
        ("draw a black diamond at 400,380 rx 100 ry 60", "decision"),
        ("draw a black arrow line from 400,440 to 400,510", "arrow3"),
        ("draw a blue rounded rect from 300,510 to 500,580", "end"),
    ]
    FLOWCHART_IO = [
        ("draw a blue rounded rect from 300,30 to 500,100", "start"),
        ("draw a black arrow line from 400,100 to 400,170", "arrow1"),
        ("draw a black diamond at 400,250 rx 100 ry 60", "decision"),
        ("draw a black arrow line from 500,250 to 600,250", "arrow_yes"),
        ("draw a black rectangle from 600,200 to 750,300", "process_yes"),
        ("draw a black arrow line from 400,310 to 400,380", "arrow_no"),
        ("draw a blue rounded rect from 300,380 to 500,450", "end"),
    ]


class CommandDecomposer:
    def __init__(self, parser: 'CommandParser'):
        self.parser = parser
        self.templates = {
            'house': SceneTemplate.HOUSE,
            'building': SceneTemplate.BUILDINGS,
            'mountain': SceneTemplate.MOUNTAIN,
            'tree': SceneTemplate.TREE,
            'car': SceneTemplate.CAR,
            'sun': SceneTemplate.SUN,
            'flower': SceneTemplate.FLOWER,
            'smiley': SceneTemplate.SMILEY,
            'person': SceneTemplate.PERSON,
            'flowchart': SceneTemplate.FLOWCHART,
            'flow': SceneTemplate.FLOWCHART,
            'process': SceneTemplate.FLOWCHART_PROCESS,
            'io': SceneTemplate.FLOWCHART_IO,
        }
        self.object_aliases = {
            'house': 'house', 'hut': 'house', 'cottage': 'house', 'cabin': 'house',
            'building': 'building', 'skyscraper': 'building',
            'mountain': 'mountain', 'hill': 'mountain',
            'tree': 'tree', 'bush': 'tree',
            'car': 'car', 'truck': 'car', 'vehicle': 'car',
            'sun': 'sun',
            'flower': 'flower', 'blossom': 'flower',
            'smiley': 'smiley', 'smile': 'smiley', 'face': 'smiley',
            'person': 'person', 'man': 'person', 'woman': 'person', 'kid': 'person', 'child': 'person',
            'flowchart': 'flowchart', 'flow': 'flowchart',
            'process': 'process',
        }

    def try_decompose(self, command_text: str) -> Optional[Command]:
        text = command_text.lower().strip()
        for alias, key in self.object_aliases.items():
            pattern = rf'(?:draw|create|make|paint)\s+(?:a\s+|an\s+|the\s+)?(?:simple\s+|tiny\s+|small\s+|little\s+)?{re.escape(alias)}\b'
            if re.match(pattern, text):
                if key in self.templates:
                    cmds = []
                    for sub_cmd_text, desc in self.templates[key]:
                        sub_cmd = self.parser._parse_single(sub_cmd_text)
                        if sub_cmd:
                            cmds.append(sub_cmd)
                    if cmds:
                        return CompositeCommand(cmds, f"scene: {alias}")
        return None


class SceneDescriptionCommand(Command):
    """场景描述命令：用户描述一幅画，系统自动布局所有图形。

    例如："画一幅画：左边一棵树，右边一座山，上面有太阳"
    """

    # 形状关键词映射（按优先级排序，长词优先）
    SHAPE_KEYWORDS = {
        # 复合形状
        '房子': ('house', 'brown'), '房屋': ('house', 'brown'), '小屋': ('house', 'brown'),
        '大楼': ('building', 'gray'), '建筑': ('building', 'gray'), '高楼': ('building', 'gray'),
        '汽车': ('car', 'blue'), '小车': ('car', 'blue'), '轿车': ('car', 'blue'),
        '笑脸': ('smiley', 'yellow'), '笑脸脸': ('smiley', 'yellow'),
        '向日葵': ('flower', 'yellow'), '花朵': ('flower', 'pink'), '小花': ('flower', 'pink'),
        '大树': ('tree', 'green'), '松树': ('tree', 'green'), '柳树': ('tree', 'green'),
        '高山': ('mountain', 'green'), '大山': ('mountain', 'green'), '雪山': ('mountain', 'white'),
        '太阳': ('sun', 'yellow'), '红日': ('sun', 'red'),
        '月亮': ('moon', 'yellow'), '弯月': ('moon', 'yellow'),
        '云朵': ('cloud', 'white'), '白云': ('cloud', 'white'), '乌云': ('cloud', 'gray'),
        '彩虹': ('rainbow', 'red'),
        '小鸟': ('bird', 'blue'), '鸟儿': ('bird', 'blue'), '鸟': ('bird', 'blue'),
        '小鱼': ('fish', 'blue'), '金鱼': ('fish', 'orange'), '鱼': ('fish', 'blue'),
        '蝴蝶': ('butterfly', 'pink'),
        '星星': ('star', 'yellow'), '五角星': ('star', 'yellow'),
        '心形': ('heart', 'red'), '爱心': ('heart', 'red'),
        # 基础形状
        '椭圆': ('ellipse', 'black'),
        '菱形': ('diamond', 'black'),
        '六边形': ('hexagon', 'black'),
        '圆角矩形': ('rounded_rect', 'black'),
        '箭头': ('arrow', 'black'),
        '矩形': ('rectangle', 'black'), '长方形': ('rectangle', 'black'),
        '正方形': ('square', 'black'), '方块': ('square', 'black'),
        '三角形': ('triangle', 'black'), '三角': ('triangle', 'black'),
        '圆形': ('circle', 'black'), '圆圈': ('circle', 'black'),
        '直线': ('line', 'black'), '线条': ('line', 'black'),
        '圆': ('circle', 'black'),
        '方': ('square', 'black'),
        '树': ('tree', 'green'),
        '山': ('mountain', 'green'),
        '花': ('flower', 'pink'),
        '车': ('car', 'blue'),
        '星': ('star', 'yellow'),
        '线': ('line', 'black'),
    }

    # 位置关键词映射 (相对位置 → 绝对坐标区域)
    POSITION_KEYWORDS = {
        '左上角': 'topleft', '左上': 'topleft', '上面左边': 'topleft',
        '右上角': 'topright', '右上': 'topright', '上面右边': 'topright',
        '左下角': 'bottomleft', '左下': 'bottomleft', '下面左边': 'bottomleft',
        '右下角': 'bottomright', '右下': 'bottomright', '下面右边': 'bottomright',
        '左边': 'left', '左侧': 'left', '左面': 'left',
        '右边': 'right', '右侧': 'right', '右面': 'right',
        '上面': 'top', '上方': 'top', '顶部': 'top', '天空': 'top', '天上': 'top',
        '下面': 'bottom', '下方': 'bottom', '底部': 'bottom', '地上': 'bottom',
        '中间': 'center', '正中间': 'center', '中央': 'center', '中间': 'center',
        '远处': 'top', '远景': 'top', '远方': 'top',
        '近处': 'bottom', '近景': 'bottom', '眼前': 'bottom',
        '旁边': 'right', '附近': 'center',
    }

    # 颜色关键词（按优先级排序，长词优先）
    COLOR_KEYWORDS = {
        '红色': 'red', '红色的': 'red',
        '蓝色': 'blue', '蓝色的': 'blue',
        '绿色': 'green', '绿色的': 'green',
        '黄色': 'yellow', '黄色的': 'yellow',
        '紫色': 'purple', '紫色的': 'purple',
        '橙色': 'orange', '橙色的': 'orange',
        '粉色': 'pink', '粉色的': 'pink', '粉红色': 'pink',
        '棕色': 'brown', '棕色的': 'brown', '褐色': 'brown',
        '黑色': 'black', '黑色的': 'black',
        '白色': 'white', '白色的': 'white',
        '灰色': 'gray', '灰色的': 'gray',
        '金色': 'gold', '金色的': 'gold',
        '银色': 'silver', '银色的': 'silver',
        '红': 'red', '蓝': 'blue', '绿': 'green', '黄': 'yellow',
        '紫': 'purple', '橙': 'orange', '粉': 'pink', '棕': 'brown',
        '黑': 'black', '白': 'white', '灰': 'gray',
    }

    # 大小关键词
    SIZE_KEYWORDS = {
        '巨大的': 'huge', '很大的': 'big', '大的': 'big', '大型': 'big',
        '很小的': 'small', '小的': 'small', '小型': 'small', '小小的': 'small',
        '巨大的': 'huge', '超大的': 'huge',
        '大': 'big', '小': 'small',
    }

    def __init__(self, description: str):
        self.description = description

    def execute(self, canvas) -> str:
        # 解析描述，提取形状和位置
        items = self._parse_description(self.description)

        if not items:
            return "无法理解场景描述"

        # 智能布局
        commands = self._layout_items(items, canvas.WIDTH, canvas.HEIGHT)

        # 执行所有命令
        results = []
        for cmd in commands:
            result = cmd.execute(canvas)
            results.append(result)

        return f"场景绘制完成: {len(results)} 个图形"

    def _parse_description(self, desc: str) -> list:
        """解析自然语言描述，提取形状、颜色、位置信息。"""
        items = []

        # 预处理：移除常见填充词（保留形状相关的词）
        # 先移除触发词
        desc = re.sub(r'(?:画一幅画|场景|画一幅|画一个场景)[：:]', '', desc)
        # 移除数量词和填充词，但保留形状关键词
        desc = re.sub(r'(?:有|了|着|一个|一只|一朵|一棵|一座|一条|一辆|一幅)', ' ', desc)

        # 分词：按逗号、顿号、句号分割（不按空格分，因为"左边 树"应该是一起的）
        parts = re.split(r'[,，、。；;]+', desc)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            item = {
                'shape': None,
                'color': None,
                'position': None,
                'size': 'medium',
                'raw': part,
            }

            # 提取形状（按长度优先匹配）
            sorted_shapes = sorted(self.SHAPE_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True)
            for keyword, (shape, default_color) in sorted_shapes:
                if keyword in part:
                    item['shape'] = shape
                    item['color'] = default_color
                    break

            # 提取颜色（覆盖默认颜色）
            sorted_colors = sorted(self.COLOR_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True)
            for keyword, color in sorted_colors:
                if keyword in part:
                    item['color'] = color
                    break

            # 提取位置
            sorted_positions = sorted(self.POSITION_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True)
            for keyword, position in sorted_positions:
                if keyword in part:
                    item['position'] = position
                    break

            # 提取大小
            for keyword, size in self.SIZE_KEYWORDS.items():
                if keyword in part:
                    item['size'] = size
                    break

            if item['shape']:
                items.append(item)

        return items

    def _layout_items(self, items: list, width: int, height: int) -> list:
        """智能布局：根据位置描述分配坐标。"""
        commands = []

        # 定义布局区域（更精细的网格）
        regions = {
            'left': (width * 0.15, height * 0.5),
            'right': (width * 0.85, height * 0.5),
            'top': (width * 0.5, height * 0.15),
            'bottom': (width * 0.5, height * 0.85),
            'center': (width * 0.5, height * 0.5),
            'topleft': (width * 0.15, height * 0.15),
            'topright': (width * 0.85, height * 0.15),
            'bottomleft': (width * 0.15, height * 0.85),
            'bottomright': (width * 0.85, height * 0.85),
        }

        # 默认位置分配（如果没有指定位置，自动分配）
        default_positions = [
            (width * 0.25, height * 0.35),  # 左边
            (width * 0.75, height * 0.35),  # 右边
            (width * 0.5, height * 0.15),   # 上面
            (width * 0.5, height * 0.75),   # 下面
            (width * 0.2, height * 0.65),   # 左下
            (width * 0.8, height * 0.65),   # 右下
            (width * 0.35, height * 0.5),   # 中左
            (width * 0.65, height * 0.5),   # 中右
        ]

        # 大小映射
        size_map = {
            'small': 0.7,
            'medium': 1.0,
            'big': 1.3,
            'huge': 1.6,
        }

        used_positions = []

        for i, item in enumerate(items):
            shape = item['shape']
            color = item['color'] or 'black'
            position = item['position']
            size_factor = size_map.get(item['size'], 1.0)

            # 确定位置
            if position and position in regions:
                cx, cy = regions[position]
            else:
                # 自动分配位置（避免重叠）
                if i < len(default_positions):
                    cx, cy = default_positions[i]
                else:
                    # 循环分配位置
                    cx = width * (0.2 + 0.6 * ((i % 4) / 3))
                    cy = height * (0.3 + 0.4 * ((i // 4) / 2))

            # 添加一些随机偏移，避免完全重叠
            import random
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-20, 20)
            cx += offset_x
            cy += offset_y

            # 确保在画布范围内
            cx = max(60, min(width - 60, cx))
            cy = max(60, min(height - 60, cy))

            used_positions.append((cx, cy))

            # 根据形状类型生成命令
            cmd = self._create_shape_command(shape, color, cx, cy, size_factor)
            if cmd:
                commands.append(cmd)

        return commands

    def _create_shape_command(self, shape: str, color: str, cx: float, cy: float, size_factor: float) -> Optional[Command]:
        """根据形状类型创建具体的绘图命令。"""
        cx, cy = int(cx), int(cy)

        # 基础形状
        if shape == 'circle':
            radius = int(60 * size_factor)
            return DrawCircleCommand({
                'color': color, 'x': str(cx), 'y': str(cy),
                'radius': str(radius), 'width': '2',
            })
        elif shape == 'square':
            side = int(120 * size_factor)
            return DrawSquareCommand({
                'color': color, 'x': str(cx), 'y': str(cy),
                'side': str(side), 'width': '2', 'filled': 'false',
            })
        elif shape == 'triangle':
            size = int(80 * size_factor)
            points = f'{cx},{cy - size} {cx - size},{cy + size} {cx + size},{cy + size}'
            return DrawTriangleCommand({
                'color': color, 'points': points, 'width': '2',
            })
        elif shape == 'star':
            radius = int(50 * size_factor)
            return DrawStarCommand({
                'color': color, 'x': str(cx), 'y': str(cy),
                'radius': str(radius), 'width': '2',
            })
        elif shape == 'line':
            length = int(100 * size_factor)
            return DrawLineCommand({
                'color': color,
                'x1': str(cx - length), 'y1': str(cy),
                'x2': str(cx + length), 'y2': str(cy),
                'width': '2',
            })
        elif shape == 'ellipse':
            rx = int(80 * size_factor)
            ry = int(50 * size_factor)
            return DrawEllipseCommand({
                'color': color, 'x': str(cx), 'y': str(cy),
                'rx': str(rx), 'ry': str(ry), 'width': '2',
            })
        elif shape == 'rectangle':
            w = int(150 * size_factor)
            h = int(100 * size_factor)
            return DrawRectangleCommand({
                'color': color,
                'x1': str(cx - w // 2), 'y1': str(cy - h // 2),
                'x2': str(cx + w // 2), 'y2': str(cy + h // 2),
                'width': '2', 'filled': 'false',
            })
        elif shape == 'diamond':
            rx = int(60 * size_factor)
            ry = int(80 * size_factor)
            return DrawDiamondCommand({
                'color': color, 'cx': str(cx), 'cy': str(cy),
                'rx': str(rx), 'ry': str(ry), 'width': '2', 'filled': 'false',
            })
        elif shape == 'hexagon':
            radius = int(60 * size_factor)
            return DrawRegularPolygonCommand({
                'color': color, 'cx': str(cx), 'cy': str(cy),
                'radius': str(radius), 'sides': '6', 'width': '2', 'filled': 'false',
            })
        elif shape == 'rounded_rect':
            w = int(150 * size_factor)
            h = int(100 * size_factor)
            return DrawRoundedRectCommand({
                'color': color,
                'x1': str(cx - w // 2), 'y1': str(cy - h // 2),
                'x2': str(cx + w // 2), 'y2': str(cy + h // 2),
                'width': '2', 'filled': 'false',
            })
        elif shape == 'arrow':
            length = int(100 * size_factor)
            return DrawArrowLineCommand({
                'color': color,
                'x1': str(cx - length), 'y1': str(cy),
                'x2': str(cx + length), 'y2': str(cy),
                'width': '2',
            })

        # 复合形状
        elif shape == 'tree':
            trunk_h = int(80 * size_factor)
            crown_r = int(60 * size_factor)
            return CompositeCommand([
                DrawRectangleCommand({
                    'color': 'brown',
                    'x1': str(cx - 10), 'y1': str(cy),
                    'x2': str(cx + 10), 'y2': str(cy + trunk_h),
                    'width': '2', 'filled': 'false',
                }),
                DrawCircleCommand({
                    'color': 'green', 'x': str(cx), 'y': str(cy - crown_r // 2),
                    'radius': str(crown_r), 'width': '2',
                }),
            ], "tree")
        elif shape == 'mountain':
            size = int(120 * size_factor)
            points = f'{cx - size},{cy + size // 2} {cx},{cy - size} {cx + size},{cy + size // 2}'
            return DrawTriangleCommand({
                'color': 'green', 'points': points, 'width': '2',
            })
        elif shape == 'sun':
            radius = int(40 * size_factor)
            return DrawFilledCircleCommand({
                'color': 'yellow', 'x': str(cx), 'y': str(cy),
                'radius': str(radius),
            })
        elif shape == 'moon':
            radius = int(35 * size_factor)
            return CompositeCommand([
                DrawFilledCircleCommand({
                    'color': 'yellow', 'x': str(cx), 'y': str(cy),
                    'radius': str(radius),
                }),
                DrawFilledCircleCommand({
                    'color': 'white', 'x': str(cx + radius // 2), 'y': str(cy - radius // 3),
                    'radius': str(int(radius * 0.8)),
                }),
            ], "moon")
        elif shape == 'cloud':
            r = int(30 * size_factor)
            return CompositeCommand([
                DrawFilledCircleCommand({
                    'color': 'white', 'x': str(cx - r), 'y': str(cy),
                    'radius': str(r),
                }),
                DrawFilledCircleCommand({
                    'color': 'white', 'x': str(cx), 'y': str(cy - r // 2),
                    'radius': str(int(r * 1.2)),
                }),
                DrawFilledCircleCommand({
                    'color': 'white', 'x': str(cx + r), 'y': str(cy),
                    'radius': str(r),
                }),
            ], "cloud")
        elif shape == 'flower':
            center_r = int(15 * size_factor)
            petal_r = int(25 * size_factor)
            return CompositeCommand([
                DrawFilledCircleCommand({
                    'color': 'yellow', 'x': str(cx), 'y': str(cy),
                    'radius': str(center_r),
                }),
                DrawEllipseCommand({
                    'color': 'pink', 'x': str(cx), 'y': str(cy - petal_r),
                    'rx': str(petal_r // 2), 'ry': str(petal_r), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': 'pink', 'x': str(cx + petal_r), 'y': str(cy),
                    'rx': str(petal_r), 'ry': str(petal_r // 2), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': 'pink', 'x': str(cx), 'y': str(cy + petal_r),
                    'rx': str(petal_r // 2), 'ry': str(petal_r), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': 'pink', 'x': str(cx - petal_r), 'y': str(cy),
                    'rx': str(petal_r), 'ry': str(petal_r // 2), 'width': '2',
                }),
            ], "flower")
        elif shape == 'smiley':
            face_r = int(80 * size_factor)
            eye_r = int(10 * size_factor)
            return CompositeCommand([
                DrawFilledCircleCommand({
                    'color': 'yellow', 'x': str(cx), 'y': str(cy),
                    'radius': str(face_r),
                }),
                DrawFilledCircleCommand({
                    'color': 'black', 'x': str(cx - face_r // 3), 'y': str(cy - face_r // 4),
                    'radius': str(eye_r),
                }),
                DrawFilledCircleCommand({
                    'color': 'black', 'x': str(cx + face_r // 3), 'y': str(cy - face_r // 4),
                    'radius': str(eye_r),
                }),
                DrawEllipseCommand({
                    'color': 'red', 'x': str(cx), 'y': str(cy + face_r // 4),
                    'rx': str(face_r // 2), 'ry': str(face_r // 4), 'width': '3',
                }),
            ], "smiley")
        elif shape == 'car':
            body_w = int(120 * size_factor)
            body_h = int(40 * size_factor)
            wheel_r = int(15 * size_factor)
            return CompositeCommand([
                DrawRectangleCommand({
                    'color': 'blue',
                    'x1': str(cx - body_w // 2), 'y1': str(cy),
                    'x2': str(cx + body_w // 2), 'y2': str(cy + body_h),
                    'width': '2', 'filled': 'false',
                }),
                DrawRectangleCommand({
                    'color': 'blue',
                    'x1': str(cx - body_w // 3), 'y1': str(cy - body_h),
                    'x2': str(cx + body_w // 3), 'y2': str(cy),
                    'width': '2', 'filled': 'false',
                }),
                DrawFilledCircleCommand({
                    'color': 'black', 'x': str(cx - body_w // 3), 'y': str(cy + body_h + wheel_r),
                    'radius': str(wheel_r),
                }),
                DrawFilledCircleCommand({
                    'color': 'black', 'x': str(cx + body_w // 3), 'y': str(cy + body_h + wheel_r),
                    'radius': str(wheel_r),
                }),
            ], "car")
        elif shape == 'house':
            body_w = int(120 * size_factor)
            body_h = int(100 * size_factor)
            roof_h = int(60 * size_factor)
            return CompositeCommand([
                DrawRectangleCommand({
                    'color': 'brown',
                    'x1': str(cx - body_w // 2), 'y1': str(cy),
                    'x2': str(cx + body_w // 2), 'y2': str(cy + body_h),
                    'width': '2', 'filled': 'false',
                }),
                DrawTriangleCommand({
                    'color': 'red',
                    'points': f'{cx - body_w // 2},{cy} {cx},{cy - roof_h} {cx + body_w // 2},{cy}',
                    'width': '2',
                }),
                DrawRectangleCommand({
                    'color': 'blue',
                    'x1': str(cx - 15), 'y1': str(cy + body_h - 40),
                    'x2': str(cx + 15), 'y2': str(cy + body_h),
                    'width': '2', 'filled': 'false',
                }),
                DrawFilledCircleCommand({
                    'color': 'yellow', 'x': str(cx + body_w // 4), 'y': str(cy + body_h // 4),
                    'radius': '15',
                }),
            ], "house")
        elif shape == 'building':
            body_w = int(100 * size_factor)
            body_h = int(150 * size_factor)
            return CompositeCommand([
                DrawRectangleCommand({
                    'color': 'gray',
                    'x1': str(cx - body_w // 2), 'y1': str(cy - body_h),
                    'x2': str(cx + body_w // 2), 'y2': str(cy + body_h // 2),
                    'width': '2', 'filled': 'false',
                }),
                DrawRectangleCommand({
                    'color': 'blue',
                    'x1': str(cx - body_w // 4), 'y1': str(cy - body_h + 20),
                    'x2': str(cx + body_w // 4), 'y2': str(cy - body_h + 50),
                    'width': '2', 'filled': 'false',
                }),
                DrawRectangleCommand({
                    'color': 'blue',
                    'x1': str(cx - body_w // 4), 'y1': str(cy - body_h + 60),
                    'x2': str(cx + body_w // 4), 'y2': str(cy - body_h + 90),
                    'width': '2', 'filled': 'false',
                }),
            ], "building")
        elif shape == 'bird':
            size = int(20 * size_factor)
            return CompositeCommand([
                DrawEllipseCommand({
                    'color': color, 'x': str(cx), 'y': str(cy),
                    'rx': str(size), 'ry': str(size // 2), 'width': '2',
                }),
                DrawTriangleCommand({
                    'color': color,
                    'points': f'{cx + size},{cy} {cx + size + size // 2},{cy - size // 3} {cx + size + size // 2},{cy + size // 3}',
                    'width': '2',
                }),
            ], "bird")
        elif shape == 'fish':
            size = int(30 * size_factor)
            return CompositeCommand([
                DrawEllipseCommand({
                    'color': color, 'x': str(cx), 'y': str(cy),
                    'rx': str(size), 'ry': str(size // 2), 'width': '2',
                }),
                DrawTriangleCommand({
                    'color': color,
                    'points': f'{cx - size},{cy} {cx - size - size // 2},{cy - size // 2} {cx - size - size // 2},{cy + size // 2}',
                    'width': '2',
                }),
                DrawFilledCircleCommand({
                    'color': 'black', 'x': str(cx + size // 2), 'y': str(cy - size // 4),
                    'radius': '3',
                }),
            ], "fish")
        elif shape == 'butterfly':
            size = int(25 * size_factor)
            return CompositeCommand([
                DrawEllipseCommand({
                    'color': color, 'x': str(cx - size), 'y': str(cy - size // 2),
                    'rx': str(size), 'ry': str(int(size * 0.7)), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': color, 'x': str(cx + size), 'y': str(cy - size // 2),
                    'rx': str(size), 'ry': str(int(size * 0.7)), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': color, 'x': str(cx - size // 2), 'y': str(cy + size // 2),
                    'rx': str(size // 2), 'ry': str(int(size * 0.5)), 'width': '2',
                }),
                DrawEllipseCommand({
                    'color': color, 'x': str(cx + size // 2), 'y': str(cy + size // 2),
                    'rx': str(size // 2), 'ry': str(int(size * 0.5)), 'width': '2',
                }),
                DrawLineCommand({
                    'color': 'black', 'x1': str(cx), 'y1': str(cy - size),
                    'x2': str(cx - size // 2), 'y2': str(cy - size * 2), 'width': '2',
                }),
                DrawLineCommand({
                    'color': 'black', 'x1': str(cx), 'y1': str(cy - size),
                    'x2': str(cx + size // 2), 'y2': str(cy - size * 2), 'width': '2',
                }),
            ], "butterfly")
        elif shape == 'heart':
            size = int(40 * size_factor)
            return CompositeCommand([
                DrawFilledCircleCommand({
                    'color': color, 'x': str(cx - size // 2), 'y': str(cy - size // 4),
                    'radius': str(size // 2),
                }),
                DrawFilledCircleCommand({
                    'color': color, 'x': str(cx + size // 2), 'y': str(cy - size // 4),
                    'radius': str(size // 2),
                }),
                DrawTriangleCommand({
                    'color': color,
                    'points': f'{cx - size},{cy - size // 4} {cx + size},{cy - size // 4} {cx},{cy + size}',
                    'width': '2',
                }),
            ], "heart")
        elif shape == 'rainbow':
            radius = int(100 * size_factor)
            colors = ['red', 'orange', 'yellow', 'green', 'blue', 'purple']
            cmds = []
            for i, c in enumerate(colors):
                r = radius - i * 8
                cmds.append(DrawCircleCommand({
                    'color': c, 'x': str(cx), 'y': str(cy + radius // 2),
                    'radius': str(r), 'width': '4',
                }))
            return CompositeCommand(cmds, "rainbow")

        return None

    def get_description(self) -> str:
        return f"scene: {self.description[:30]}"


_SKIP_WORDS = {'a', 'an', 'the', 'draw', 'paint', 'make', 'create', 'with',
               'set', 'change', 'save', 'export', 'from', 'to', 'at', 'in',
               'on', 'and', 'or', 'for', 'of', 'this', 'that', 'it', 'is',
               'use', 'using', 'add', 'put', 'write', 'let', 'go', 'back',
               'one', 'new', 'some', 'all', 'my', 'i', 'do', 'just', 'up',
               'down', 'out', 'off', 'over', 'by', 'no', 'not', 'be',
               'as', 'into', 'then', 'than', 'had', 'have', 'has', 'did',
               'can', 'will', 'would', 'could', 'should', 'may', 'might',
               'hi', 'hello', 'ok', 'okay', 'yes', 'no',
               'circle', 'square', 'ring', 'triangle', 'star', 'rectangle',
               'ellipse', 'line', 'hexagon', 'diamond', 'polygon', 'arrow',
               'rounded', 'filled', 'hollow',
               'cursor', 'center', 'topleft', 'topright', 'bottomleft', 'bottomright',
               'topcenter', 'bottomcenter', 'centerleft', 'centerright',
               'offset', 'align', 'left', 'right'}


def _find_color(text_l: str) -> Optional[str]:
    for word in text_l.split():
        w = word.strip(',.;:!?，。；：！？')
        if w in _SKIP_WORDS or len(w) < 2:
            continue
        if w in COLOR_MAP:
            return w
    for word in text_l.split():
        w = word.strip(',.;:!?，。；：！？')
        if w in _SKIP_WORDS or len(w) < 3:
            continue
        match = difflib.get_close_matches(w, COLOR_MAP.keys(), n=1, cutoff=0.68)
        if match:
            return match[0]
    return None


_GRID_COLS = {'a': 80, 'b': 240, 'c': 400, 'd': 560, 'e': 720}
_GRID_ROWS = {'1': 60, '2': 180, '3': 300, '4': 420, '5': 540}
_OFFSET_STEP = 50


def _resolve_grid_ref(text_l: str) -> Optional[tuple]:
    m = re.search(r'(?<![a-zA-Z0-9])([a-eA-E])\s*[ ,\-]?([1-5])(?![a-zA-Z0-9])', text_l)
    if m:
        return (_GRID_COLS[m.group(1).lower()], _GRID_ROWS[m.group(2)])
    return None


def _resolve_offset(text_l: str) -> tuple:
    dx = dy = 0
    if re.search(r'\boffset\s+left\b', text_l):
        dx = -_OFFSET_STEP
    if re.search(r'\boffset\s+right\b', text_l):
        dx = _OFFSET_STEP
    if re.search(r'\boffset\s+up\b', text_l):
        dy = -_OFFSET_STEP
    if re.search(r'\boffset\s+down\b', text_l):
        dy = _OFFSET_STEP
    return (dx, dy)


def _find_position(text_l: str, fallback_cx: int = 400, fallback_cy: int = 300) -> tuple:
    grid = _resolve_grid_ref(text_l)
    if grid:
        return grid

    if re.search(r'\bcursor\b', text_l):
        base = (fallback_cx, fallback_cy)
    elif re.search(r'\bcenter\b', text_l):
        base = (400, 300)
    elif re.search(r'\btopcenter\b', text_l) or re.search(r'\btop\s+middle\b', text_l):
        base = (400, 100)
    elif re.search(r'\bbottomcenter\b', text_l) or re.search(r'\bbottom\s+middle\b', text_l):
        base = (400, 500)
    elif re.search(r'\bcenterleft\b', text_l) or re.search(r'\bmiddle\s+left\b', text_l):
        base = (100, 300)
    elif re.search(r'\bcenterright\b', text_l) or re.search(r'\bmiddle\s+right\b', text_l):
        base = (700, 300)
    elif re.search(r'\btopleft\b', text_l) or re.search(r'\bupper\s+left\b', text_l):
        base = (100, 100)
    elif re.search(r'\bbottomleft\b', text_l) or re.search(r'\blower\s+left\b', text_l):
        base = (100, 500)
    elif re.search(r'\btopright\b', text_l) or re.search(r'\bupper\s+right\b', text_l):
        base = (700, 100)
    elif re.search(r'\bbottomright\b', text_l) or re.search(r'\blower\s+right\b', text_l):
        base = (700, 500)
    else:
        base = (fallback_cx, fallback_cy)

    ox, oy = _resolve_offset(text_l)
    return (base[0] + ox, base[1] + oy)


class HelpCommand(Command):
    """Sentinel command returned when the user asks for help."""
    def execute(self, canvas) -> str:
        return ("可用命令: draw circle/rectangle/triangle/line/star/ellipse/square "
                "at X,Y | write 'text' at X,Y | set color/width | clear | undo/redo | "
                "save | help | exit")

    def get_description(self) -> str:
        return "show help"


class SuggestionCommand(Command):
    """Returned when no command matched but close keywords were found."""
    def __init__(self, suggestions: List[str], original: str):
        self.suggestions = suggestions
        self.original = original

    def execute(self, canvas) -> str:
        opts = ', '.join(self.suggestions)
        return f"Did you mean: {opts}?  (original: {self.original})"

    def get_description(self) -> str:
        return f"suggest {', '.join(self.suggestions)}"


# Canonical shape keywords used for did-you-mean suggestions.
_KNOWN_KEYWORDS = [
    'circle', 'square', 'rectangle', 'triangle', 'star', 'ellipse',
    'line', 'hexagon', 'diamond', 'polygon', 'arrow', 'ring',
    'rounded', 'filled', 'clear', 'undo', 'redo', 'save', 'exit',
    'text', 'write', 'draw', 'set', 'color', 'width', 'background',
    'cursor', 'move', 'scale', 'bigger', 'smaller', 'house', 'tree',
    'flower', 'sun', 'mountain', 'car', 'smiley', 'flowchart',
]


class CommandParser:
    def __init__(self):
        self.patterns = []
        self.decomposer = CommandDecomposer(self)
        self.cursor_x = 400
        self.cursor_y = 300
        self._register()
        # 建立拼音索引
        try:
            from .pinyin_matcher import build_pinyin_index
            build_pinyin_index(list(_ZH_EN_ALL.keys()))
        except Exception:
            pass

    def _register(self):
        color_group = r"(?P<color>" + COLOR_NAMES + r")"
        number = r"\d+"
        coord = rf"(?P<x>{number})\s*,\s*(?P<y>{number})"
        points = r"(?P<points>(?:\d+\s*,\s*\d+\s*){2,}(?:\d+\s*,\s*\d+))"

        self.patterns = [
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?filled\s+{color_group}\s+circle\s+(?:at\s+)?\(?{coord}\)?\s*(?:with\s+)?(?:radius\s+)?(?P<radius>{number})",
             lambda m: DrawFilledCircleCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+circle\s+(?:at\s+)?\(?{coord}\)?\s*(?:with\s+)?(?:radius\s+)?(?P<radius>{number})",
             lambda m: DrawCircleCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+ellipse\s+(?:at\s+)?\(?{coord}\)?\s*(?:with\s+)?rx\s*[=:]?\s*(?P<rx>{number})\s*(?:,?\s*ry|ry)\s*[=:]?\s*(?P<ry>{number})",
             lambda m: DrawEllipseCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+line\s+(?:from\s+)?\(?(?P<x1>{number})\s*,\s*(?P<y1>{number})\)?\s+(?:to|->)\s*\(?(?P<x2>{number})\s*,\s*(?P<y2>{number})\)?",
             lambda m: DrawLineCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+(?:filled\s+)?rectangle\s+(?:from\s+)?\(?(?P<x1>{number})\s*,\s*(?P<y1>{number})\)?\s+(?:to|->)\s*\(?(?P<x2>{number})\s*,\s*(?P<y2>{number})\)?",
             lambda m: DrawRectangleCommand({**m.groupdict(), 'filled': 'true' if m.group(0).count('filled') > 0 else 'false'})),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+triangle\s+(?:with\s+)?(?:points\s+)?\(?{points}\)?",
             lambda m: DrawTriangleCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+star\s+(?:at\s+)?\(?{coord}\)?\s*(?:with\s+)?(?:radius\s+)?(?P<radius>{number})",
             lambda m: DrawStarCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+polygon\s+(?:with\s+)?(?:points\s+)?\(?{points}\)?",
             lambda m: DrawPolygonCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+square\s+(?:at\s+)?\(?{coord}\)?\s*(?:side\s+)?(?P<side>{number})?",
             lambda m: DrawSquareCommand(m.groupdict())),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?{color_group}\s+ring\s+(?:at\s+)?\(?{coord}\)?\s*(?:outer\s+|radius\s+)?(?P<radius>{number})?\s*(?:inner\s+)?(?P<inner>{number})?",
             lambda m: DrawRingCommand(m.groupdict())),
            (r"(?:write|draw|add|put)\s+(?:the\s+)?(text\s+)?[\"'](?P<text>[^\"']+)[\"']\s+(?:at\s+)?\(?(?P<x>\d+)\s*,\s*(?P<y>\d+)\)?",
             lambda m: DrawTextCommand(m.groupdict())),
            # Text with "text" keyword but no quotes: "write text hello at 100,200"
            (r"(?:write|draw|add|put)\s+(?:the\s+)?text\s+(?P<text>[^0-9\n]+?)\s+(?:at\s+)?\(?(?P<x>\d+)\s*,\s*(?P<y>\d+)\)?",
             lambda m: DrawTextCommand(m.groupdict())),
            # Chinese text without quotes: "write 你好世界 at 100,200"
            (r"(?:write|draw|add|put)\s+(?:the\s+)?(?P<text>[一-鿿][一-鿿\w\s]*?)\s+(?:at\s+)?\(?(?P<x>\d+)\s*,\s*(?P<y>\d+)\)?",
             lambda m: DrawTextCommand(m.groupdict())),
            (rf"set\s+(?:the\s+)?(?:pen\s+)?color\s+(?:to\s+)?{color_group}",
             lambda m: SetColorCommand(m.groupdict())),
            (r"(?:set|change)\s+(?:the\s+)?(?:pen\s+)?width\s+(?:to\s+)?(?P<width>\d+)",
             lambda m: SetWidthCommand(m.groupdict())),
            (r"(?:clear|erase|reset)\s+(?:the\s+)?(?:canvas|drawing|screen|all)",
             lambda m: ClearCanvasCommand()),
            (r"undo|go\s+back|back",
             lambda m: UndoCommand()),
            (r"redo|forward",
             lambda m: RedoCommand()),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?(?:filled\s+)?{color_group}\s+arrow\s+(?:line\s+)?(?:from\s+)?\(?(?P<x1>{number})\s*,\s*(?P<y1>{number})\)?\s+(?:to|->)\s*\(?(?P<x2>{number})\s*,\s*(?P<y2>{number})\)?",
             lambda m: DrawArrowLineCommand({**m.groupdict(), 'filled': 'true' if 'filled' in m.group(0) else 'false'})),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?(?:filled\s+)?{color_group}\s+rounded\s+rect(?:angle)?\s+(?:from\s+)?\(?(?P<x1>{number})\s*,\s*(?P<y1>{number})\)?\s+(?:to|->)\s*\(?(?P<x2>{number})\s*,\s*(?P<y2>{number})\)?",
             lambda m: DrawRoundedRectCommand({**m.groupdict(), 'filled': 'true' if 'filled' in m.group(0) else 'false'})),
            (rf"(?:draw|make|create|paint)\s+(?:an?\s+)?(?:filled\s+)?{color_group}\s+diamond\s+(?:at\s+)?\(?(?P<cx>{number})\s*,\s*(?P<cy>{number})\)?\s*(?:rx\s*[=:]?\s*(?P<rx>{number})\s*(?:ry\s*[=:]?\s*(?P<ry>{number})?)?)",
             lambda m: DrawDiamondCommand({**m.groupdict(), 'filled': 'true' if 'filled' in m.group(0) else 'false'})),
            (r"(?:save|export)\s+(?:the\s+)?(?:drawing|canvas|file)?\s*(?:as\s+)?(?P<filename>[\w./\\-]+)?",
             lambda m: SaveCommand(m.groupdict())),
            (rf"repeat\s+variation\s+(?P<color>{COLOR_NAMES})",
             lambda m: RepeatLastWithVariationCommand({'color': m.group('color')})),
            (r"repeat\s+variation",
             lambda m: RepeatLastWithVariationCommand()),
            (r"rain", lambda m: StartRainCommand()),
            (r"stop\s+rain", lambda m: StopRainCommand()),
            (r"grow\s+flower", lambda m: GrowFlowerCommand()),
            (r"grow\s+tree", lambda m: GrowTreeCommand()),
            (r"firefl(?:y|ies)", lambda m: StartFirefliesCommand()),
            (r"stop\s+animation", lambda m: StopAllAnimationsCommand()),
            (r"fireworks", lambda m: FireworksCommand()),
            (r"sparkle", lambda m: SparkleCommand()),
            (r"magic\s+circle", lambda m: MagicCircleCommand()),
            (r"starfall", lambda m: StartStarfallCommand()),
            (r"stop\s+starfall", lambda m: StopStarfallCommand()),
            (r"snow", lambda m: StartSnowCommand()),
            (r"stop\s+snow", lambda m: StopSnowCommand()),
            (r"bubbles", lambda m: StartBubblesCommand()),
            (r"stop\s+bubbles", lambda m: StopBubblesCommand()),
            (r"aurora", lambda m: StartAuroraCommand()),
            (r"stop\s+aurora", lambda m: StopAuroraCommand()),
        ]

    def _parse_single(self, text: str) -> Optional[Command]:
        text = text.strip()
        for pattern, handler in self.patterns:
            m = re.match(pattern, text, re.IGNORECASE)
            if m:
                try:
                    return handler(m)
                except Exception:
                    continue
        return None

    def _parse_move_scale(self, text_en: str) -> Optional[Command]:
        text_l = text_en.lower().strip()

        if re.search(r'\bconfirm\b', text_l):
            return ConfirmCommand()

        has_cursor = bool(re.search(r'\bcursor\b', text_l))
        has_shape_keyword = bool(re.search(r'\bshape\b|\bprev\b|\blast\b', text_l))
        has_draw_verb = bool(re.search(r'\b(?:draw|make|create|paint)\b', text_l))

        # --- Shape move/scale (requires "shape"/"prev"/"last" keyword) ---
        if has_shape_keyword:
            move_dx = move_dy = 0
            is_move = False

            if re.search(r'\bmove\s+right\b', text_l) or re.search(r'\bright\b', text_l):
                move_dx = 1; is_move = True
            elif re.search(r'\bmove\s+left\b', text_l) or re.search(r'\bleft\b', text_l):
                move_dx = -1; is_move = True
            elif re.search(r'\bmove\s+up\b', text_l) or re.search(r'\bup\b', text_l):
                move_dy = -1; is_move = True
            elif re.search(r'\bmove\s+down\b', text_l) or re.search(r'\bdown\b', text_l):
                move_dy = 1; is_move = True

            if is_move:
                nums = extract_numbers(text_l)
                if nums:
                    move_dx *= nums[0]; move_dy *= nums[0]
                else:
                    move_dx *= 100; move_dy *= 100
                return MoveLastCommand({'dx': str(move_dx), 'dy': str(move_dy)})

            if re.search(r'\bbigger\b', text_l):
                nums = extract_numbers(text_l)
                factor = parse_number_word(str(nums[0])) if nums else 1.5
                return ScaleLastCommand({'factor': str(factor)})

            if re.search(r'\bsmaller\b', text_l):
                return ScaleLastCommand({'factor': '0.66'})

            if re.search(r'\bscale\s+(?:up|down)\b', text_l):
                nums = extract_numbers(text_l)
                factor = nums[0] if nums else 2
                return ScaleLastCommand({'factor': str(factor)})

            return None

        # --- Cursor move (default for bare "move" + direction) ---
        cursor_dx = cursor_dy = 0
        is_cursor_move = False

        if not has_draw_verb:
            if re.search(r'\bmove\s+right\b', text_l) or (has_cursor and re.search(r'\bright\b', text_l)):
                cursor_dx = 1; is_cursor_move = True
            elif re.search(r'\bmove\s+left\b', text_l) or (has_cursor and re.search(r'\bleft\b', text_l)):
                cursor_dx = -1; is_cursor_move = True
            elif re.search(r'\bmove\s+up\b', text_l) or (has_cursor and re.search(r'\bup\b', text_l)):
                cursor_dy = -1; is_cursor_move = True
            elif re.search(r'\bmove\s+down\b', text_l) or (has_cursor and re.search(r'\bdown\b', text_l)):
                cursor_dy = 1; is_cursor_move = True

        if is_cursor_move:
            nums = extract_numbers(text_l)
            if nums:
                cursor_dx *= nums[0]; cursor_dy *= nums[0]
            else:
                cursor_dx *= 50; cursor_dy *= 50
            return MoveCursorCommand({'dx': str(cursor_dx), 'dy': str(cursor_dy)})

        # Set cursor to absolute position
        if has_cursor:
            # Direct coordinate: "cursor move 200,300" or "cursor set 200,300"
            coord_match = re.search(r'(\d+)\s*,\s*(\d+)', text_l)
            if coord_match:
                return SetCursorCommand({'x': coord_match.group(1), 'y': coord_match.group(2)})
            for keyword, (tx, ty) in [
                ('center', (400, 300)), ('topleft', (50, 50)),
                ('bottomleft', (50, 550)), ('topright', (750, 50)),
                ('bottomright', (750, 550)),
            ]:
                if keyword in text_l:
                    return SetCursorCommand({'x': str(tx), 'y': str(ty)})
            return None

        if re.search(r'\bbigger\b', text_l):
            nums = extract_numbers(text_l)
            factor = parse_number_word(str(nums[0])) if nums else 1.5
            return ScaleLastCommand({'factor': str(factor)})

        if re.search(r'\bsmaller\b', text_l):
            return ScaleLastCommand({'factor': '0.66'})

        if re.search(r'\bscale\s+(?:up|down)\b', text_l):
            nums = extract_numbers(text_l)
            factor = nums[0] if nums else 2
            return ScaleLastCommand({'factor': str(factor)})

        return None

    # Size keyword multipliers relative to default
    _SIZE_RADIUS = {'big': 120, 'small': 40, 'medium': 80, 'large': 120, 'tiny': 30, 'little': 40}
    _SIZE_SIDE = {'big': 200, 'small': 80, 'medium': 150, 'large': 200, 'tiny': 60, 'little': 80}

    def _fuzzy_fallback(self, text_en: str) -> Optional[Command]:
        text_l = text_en.lower().strip()

        mc = self._parse_move_scale(text_en)
        if mc:
            return mc

        if re.search(r'\b(?:clear|erase|reset)\b', text_l):
            return ClearCanvasCommand()
        if re.search(r'\b(?:undo|back)\b', text_l):
            return UndoCommand()
        if re.search(r'\b(?:redo|forward)\b', text_l):
            return RedoCommand()
        if re.search(r'\b(?:exit|quit)\b', text_l):
            return None

        width = '4'
        if re.search(r'\b(?:thick)\b', text_l):
            width = '6'
        elif re.search(r'\b(?:thin)\b', text_l):
            width = '2'

        # Detect size keywords for later use
        size_word = None
        for kw in ('large', 'big', 'tiny', 'small', 'little', 'medium'):
            if re.search(r'\b' + kw + r'\b', text_l):
                size_word = kw
                break

        # "set <color>" without shape → SetColorCommand
        if re.search(r'\b(?:set|change)\b', text_l) and not re.search(r'\b(?:draw|make|create|paint)\b', text_l):
            scm = re.search(r'(?:set|change|设置)\s+(?:\w+\s+)?(?P<color>\w+)$', text_l)
            if scm:
                c = _find_color(scm.group('color'))
                if c:
                    return SetColorCommand({'color': c})

        cx, cy = _find_position(text_l, self.cursor_x, self.cursor_y)

        has_shape = bool(re.search(r'\b(circle|square|ring|triangle|star|rectangle|ellipse|line|hexagon|diamond|polygon|arrow|rounded)\b', text_l))
        cname = _find_color(text_l)
        if cname is None and has_shape:
            cname = 'black'

        if cname:
            # Resolve size-dependent defaults
            _r = lambda dflt: str(self._SIZE_RADIUS.get(size_word, dflt)) if size_word else str(dflt)
            _s = lambda dflt: str(self._SIZE_SIDE.get(size_word, dflt)) if size_word else str(dflt)

            if re.search(r'\bsquare\b', text_l):
                side_val = _s(200)
                return DrawSquareCommand({
                    'color': cname, 'x': str(cx), 'y': str(cy),
                    'side': side_val, 'width': width, 'filled': 'false',
                })
            if re.search(r'\bring\b', text_l):
                r60 = _r(60)
                return DrawRingCommand({
                    'color': cname, 'x': str(cx), 'y': str(cy),
                    'radius': r60, 'inner': str(int(int(r60) // 2)), 'width': width,
                })
            if re.search(r'\bhexagon\b', text_l) or '6' in text_l:
                return DrawRegularPolygonCommand({
                    'color': cname, 'cx': str(cx), 'cy': str(cy),
                    'radius': _r(80), 'sides': '6', 'width': width, 'filled': 'false',
                })
            if re.search(r'\bdiamond\b', text_l):
                r100 = _r(100)
                return DrawDiamondCommand({
                    'color': cname, 'cx': str(cx), 'cy': str(cy),
                    'rx': r100, 'ry': str(int(int(r100) * 0.6)), 'width': width, 'filled': 'false',
                })
            if re.search(r'\btriangle\b', text_l):
                return DrawTriangleCommand({
                    'color': cname, 'width': width,
                    'points': f'{cx},{cy - 100} {cx - 100},{cy + 50} {cx + 100},{cy + 50}',
                })
            if re.search(r'\b(?:arrow|arrow\s+line)\b', text_l):
                return DrawArrowLineCommand({
                    'color': cname, 'x1': str(cx - 200), 'y1': str(cy),
                    'x2': str(cx + 200), 'y2': str(cy), 'width': width,
                })
            if re.search(r'\brounded\b', text_l):
                return DrawRoundedRectCommand({
                    'color': cname, 'x1': str(cx - 120), 'y1': str(cy - 60),
                    'x2': str(cx + 120), 'y2': str(cy + 60),
                    'width': width, 'filled': 'false',
                })
            if re.search(r'\bstar\b', text_l):
                return DrawStarCommand({
                    'color': cname, 'x': str(cx), 'y': str(cy),
                    'radius': _r(60), 'width': width,
                })
            if re.search(r'\brectangle\b', text_l):
                return DrawRectangleCommand({
                    'color': cname, 'x1': str(cx - 150), 'y1': str(cy - 100),
                    'x2': str(cx + 150), 'y2': str(cy + 100),
                    'width': width, 'filled': 'false',
                })
            if re.search(r'\bellipse\b', text_l):
                return DrawEllipseCommand({
                    'color': cname, 'x': str(cx), 'y': str(cy),
                    'rx': '150', 'ry': '80', 'width': width,
                })

            is_horizontal = bool(re.search(r'\bhorizont', text_l))
            is_vertical = bool(re.search(r'\bvertical', text_l))
            is_diagonal = bool(re.search(r'\bdiagonal', text_l))

            if re.search(r'\bline\b', text_l):
                if is_horizontal:
                    return DrawLineCommand({
                        'color': cname, 'x1': '50', 'y1': str(cy),
                        'x2': '750', 'y2': str(cy), 'width': width,
                    })
                if is_vertical:
                    return DrawLineCommand({
                        'color': cname, 'x1': str(cx), 'y1': '50',
                        'x2': str(cx), 'y2': '550', 'width': width,
                    })
                if is_diagonal:
                    return DrawLineCommand({
                        'color': cname, 'x1': '50', 'y1': '50',
                        'x2': '750', 'y2': '550', 'width': width,
                    })
                return DrawLineCommand({
                    'color': cname, 'x1': '100', 'y1': '100',
                    'x2': '700', 'y2': '500', 'width': width,
                })

            # Check for filled circle
            if re.search(r'\bfilled\b', text_l):
                return DrawFilledCircleCommand({
                    'color': cname, 'x': str(cx), 'y': str(cy),
                    'radius': _r(80),
                })

            return DrawCircleCommand({
                'color': cname, 'x': str(cx), 'y': str(cy),
                'radius': _r(80), 'width': width,
            })

        match = re.search(r'(?:set|change|设置)\s+(?:color|颜色|colour)\s+(?:to|为|到)?\s*(?P<color>\w+)', text_l)
        if match:
            cname2 = match.group('color').lower()
            if cname2 in COLOR_MAP or difflib.get_close_matches(cname2, COLOR_MAP.keys(), n=1, cutoff=0.5):
                return SetColorCommand({'color': cname2})

        match = re.search(r'(?:save|保存|export)\s*(?P<filename>[\w./\\-]+)?', text_l)
        if match:
            fn = match.group('filename') or 'drawing.png'
            return SaveCommand({'filename': fn})

        if re.search(r'(?:background|bg)\s+(?:color\s+)?(?:to\s+)?(?P<color>\w+)', text_l):
            m = re.search(r'(?:background|bg)\s+(?:color\s+)?(?:to\s+)?(?P<color>\w+)', text_l)
            if m:
                bc = _find_color(m.group('color'))
                if bc:
                    return SetBackgroundCommand({'color': bc})

        if re.search(r'\bthick\b', text_l):
            return SetWidthCommand({'width': '6'})
        if re.search(r'\bthin\b', text_l):
            return SetWidthCommand({'width': '2'})

        for alias, key in self.decomposer.object_aliases.items():
            if alias in text_l:
                if key in self.decomposer.templates:
                    cmds = []
                    for sub_cmd_text, desc in self.decomposer.templates[key]:
                        sub_cmd = self._parse_single(sub_cmd_text)
                        if sub_cmd:
                            cmds.append(sub_cmd)
                    if cmds:
                        return CompositeCommand(cmds, f"scene: {alias}")

        return None

    def _parse_multi(self, text_en: str) -> Optional[Command]:
        parts = re.split(r'\s+(?:and|then)\s+', text_en.strip(), flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) <= 1:
            return None
        saved_cursor_x = self.cursor_x
        cmds = []
        for part in parts:
            c = (self._parse_single(part) or
                 self._fuzzy_fallback(part))
            if not c:
                self.cursor_x = saved_cursor_x
                return None
            cmds.append(c)
            self.cursor_x += 160
        self.cursor_x = saved_cursor_x
        return CompositeCommand(cmds, f"multi: {text_en}")

    # --- Natural-language exit / help (Chinese, checked before translation) ---
    _EXIT_RE = re.compile(
        r'(?:退出|退出程序|关闭程序|关掉|结束|拜拜|再见|结束程序|'
        r'(?:请|帮我|我要|我想要|想要)(?:退出|关|关闭|结束|拜拜|再见))')
    _HELP_RE = re.compile(
        r'(?:帮助|帮助我|帮帮我|帮我|给我帮助|怎么办|如何使用|怎么用|'
        r'(?:请|帮我|我要|我想要)(?:帮助|帮忙|提示|说明|看一下帮助))')

    def parse_command(self, text: str, cursor_x: int = 400, cursor_y: int = 300) -> Optional[Command]:
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        text = fix_speech_text(text)

        # Early return: natural-language exit phrases (Chinese)
        if self._EXIT_RE.search(text):
            return None  # None signals exit to the caller

        # Early return: natural-language help phrases (Chinese)
        if self._HELP_RE.search(text):
            return HelpCommand()

        # 场景描述模式：多种触发方式
        scene_patterns = [
            r'(?:画一幅画|场景|画一幅|画一个场景)[：:]\s*(.+)',
            r'(?:画一幅画|画一个场景)\s*(.+)',
            r'(?:描述|想象)\s*(.+)',
        ]
        for pattern in scene_patterns:
            scene_match = re.search(pattern, text)
            if scene_match:
                description = scene_match.group(1)
                # 检查是否包含足够的形状关键词
                shape_keywords = ['树', '山', '太阳', '房子', '花', '车', '圆', '方', '三角', '星', '线', '椭圆',
                                  '月亮', '云', '鸟', '鱼', '蝴蝶', '彩虹', '心', '笑脸', '大楼', '汽车']
                if any(kw in description for kw in shape_keywords):
                    return SceneDescriptionCommand(description)

        # 拼音模糊匹配：在直接匹配失败后，用拼音近似度匹配
        # 注意：不在翻译前替换文本，避免破坏已知复合词
        text_en = zh_to_en(text)
        multi = self._parse_multi(text_en)
        if multi:
            return multi
        root = self.decomposer.try_decompose(text_en)
        if root:
            return root
        cmd = self._parse_single(text_en)
        if cmd:
            return cmd
        # 拼音模糊匹配：用原始中文文本做拼音近似匹配
        cmd = self._pinyin_fallback(text)
        if cmd:
            return cmd
        cmd = self._fuzzy_fallback(text_en)
        if cmd:
            return cmd

        # --- Did-you-mean suggestions ---
        return self._suggest(text_en)

    def _pinyin_fallback(self, text: str) -> Optional[Command]:
        """拼音模糊匹配：当直接解析失败时，用拼音编辑距离匹配已知中文命令。"""
        if not text or not any('\u4e00' <= ch <= '\u9fff' for ch in text):
            return None
        try:
            from .pinyin_matcher import _to_pinyin, _edit_distance
        except Exception:
            return None
        # 构建拼音索引（首次调用时缓存）
        if not hasattr(self, '_pinyin_index'):
            self._pinyin_index = {}
            for zh in _ZH_EN_ALL:
                try:
                    py = _to_pinyin(zh)
                    if py:
                        self._pinyin_index[zh] = py
                except Exception:
                    continue
        text_py = _to_pinyin(text)
        if not text_py:
            return None
        best_zh = None
        best_dist = 3  # 最多允许 2 处拼音差异
        for zh_cmd, cmd_py in self._pinyin_index.items():
            if text_py == cmd_py:
                best_zh = zh_cmd
                best_dist = 0
                break
            dist = _edit_distance(text_py, cmd_py)
            if dist < best_dist:
                best_dist = dist
                best_zh = zh_cmd
        if best_zh and best_dist <= 2:
            en = zh_to_en(best_zh) if best_zh in _ZH_EN_ALL else best_zh
            cmd = self._parse_single(en)
            if cmd:
                return cmd
            # 也尝试在模糊匹配上下文中使用
            cmd = self._fuzzy_fallback(en)
            if cmd:
                return cmd
        return None

    def _suggest(self, text_en: str) -> Optional[Command]:
        """Return a SuggestionCommand if close keyword matches are found."""
        words = set(re.findall(r'[a-z]+', text_en.lower()))
        words -= _SKIP_WORDS
        if not words:
            return None
        all_suggestions: List[str] = []
        for w in words:
            matches = difflib.get_close_matches(w, _KNOWN_KEYWORDS, n=3, cutoff=0.6)
            all_suggestions.extend(matches)
        if not all_suggestions:
            return None
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in all_suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return SuggestionCommand(unique[:5], text_en)


class RepeatLastWithVariationCommand(Command):
    """Repeat the last drawn shape with a variation (random position or color)."""

    def __init__(self, params: Dict[str, str] = None):
        self.params = params or {}
        self.color_override = self.params.get('color', '')

    def execute(self, canvas) -> str:
        import random
        if canvas.last_command_type is None:
            return "nothing to repeat (draw something first)"
        cmd_type = canvas.last_command_type
        params = dict(canvas.last_command_params)

        if cmd_type is CompositeCommand and 'sub_commands' in params:
            sub_list = params['sub_commands']
            new_subs = []
            results = []
            if self.color_override:
                for sub_type, sub_params in sub_list:
                    new_params = dict(sub_params)
                    new_params['color'] = self.color_override
                    sub_cmd = sub_type(new_params)
                    new_subs.append(sub_cmd)
                    results.append(sub_cmd.execute(canvas))
            else:
                orig_xs, orig_ys = [], []
                for sub_type, sub_params in sub_list:
                    for key in ('x', 'cx', 'x1'):
                        if key in sub_params:
                            orig_xs.append(int(sub_params[key]))
                            break
                    for key in ('y', 'cy', 'y1'):
                        if key in sub_params:
                            orig_ys.append(int(sub_params[key]))
                            break
                if orig_xs and orig_ys:
                    orig_cx = sum(orig_xs) // len(orig_xs)
                    orig_cy = sum(orig_ys) // len(orig_ys)
                    base_x = random.randint(100, canvas.WIDTH - 100)
                    base_y = random.randint(100, canvas.HEIGHT - 100)
                    dx = base_x - orig_cx
                    dy = base_y - orig_cy
                else:
                    dx = random.randint(-200, 200)
                    dy = random.randint(-200, 200)
                for sub_type, sub_params in sub_list:
                    new_params = dict(sub_params)
                    for key in ('x', 'cx', 'x1', 'x2'):
                        if key in new_params:
                            new_params[key] = str(int(new_params[key]) + dx)
                    for key in ('y', 'cy', 'y1', 'y2'):
                        if key in new_params:
                            new_params[key] = str(int(new_params[key]) + dy)
                    sub_cmd = sub_type(new_params)
                    new_subs.append(sub_cmd)
                    results.append(sub_cmd.execute(canvas))
            canvas.last_command_type = CompositeCommand
            canvas.last_command_params = {
                'sub_commands': [(type(sc), getattr(sc, 'params', {})) for sc in new_subs]
            }
            variation = f"color={self.color_override}" if self.color_override else "random position"
            return f"repeated scene with {variation}"

        if self.color_override:
            params['color'] = self.color_override
            variation_desc = f"color={self.color_override}"
        else:
            rx = random.randint(100, canvas.WIDTH - 100)
            ry = random.randint(100, canvas.HEIGHT - 100)
            for key in ('x', 'cx'):
                if key in params:
                    params[key] = str(rx)
            for key in ('y', 'cy'):
                if key in params:
                    params[key] = str(ry)
            variation_desc = f"random position ({rx},{ry})"

        try:
            cmd = cmd_type(params)
            result = cmd.execute(canvas)
            canvas.last_command_type = type(cmd)
            canvas.last_command_params = params
            return f"repeated with {variation_desc}: {result}"
        except Exception as e:
            return f"repeat failed: {e}"

    def get_description(self) -> str:
        if self.color_override:
            return f"repeat last in {self.color_override}"
        return "repeat last at random position"


# ─── Animation Commands ──────────────────────────────────────────────────────

class StartRainCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import RainAnimation
        canvas.anim_mgr.add(RainAnimation(canvas.WIDTH))
        return "🌧 开始下雨"
    def get_description(self) -> str:
        return "start rain effect"

class StopRainCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import RainAnimation
        before = canvas.anim_mgr.active_count
        canvas.anim_mgr._animations = [
            a for a in canvas.anim_mgr._animations
            if not isinstance(a, RainAnimation)
        ]
        after = canvas.anim_mgr.active_count
        return f"☀ 雨停了 (removed {before - after} rain effects)"
    def get_description(self) -> str:
        return "stop rain effect"

class GrowFlowerCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import GrowFlowerAnimation
        cx, cy = canvas.cursor_x, canvas.cursor_y
        canvas.anim_mgr.add(GrowFlowerAnimation(cx, cy, canvas.pen_color))
        return "🌷 开花啦"
    def get_description(self) -> str:
        return "grow a flower at cursor"

class GrowTreeCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import GrowTreeAnimation
        cx, cy = canvas.cursor_x, canvas.cursor_y
        canvas.anim_mgr.add(GrowTreeAnimation(cx, cy))
        return "🌳 大树长成"
    def get_description(self) -> str:
        return "grow a tree at cursor"

class StartFirefliesCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import FirefliesAnimation
        canvas.anim_mgr.add(FirefliesAnimation(canvas.WIDTH, canvas.HEIGHT))
        return "✨ 萤火虫飞来啦"
    def get_description(self) -> str:
        return "add fireflies effect"

class StopAllAnimationsCommand(Command):
    def execute(self, canvas) -> str:
        count = canvas.anim_mgr.active_count
        canvas.anim_mgr.clear()
        return f"⏹ 停止了 {count} 个动画"
    def get_description(self) -> str:
        return "stop all animations"


# ─── Phase 3: Particle Magic Commands ────────────────────────────────────────

class FireworksCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import FireworksAnimation
        cx, cy = canvas.cursor_x, canvas.cursor_y
        canvas.anim_mgr.add(FireworksAnimation(cx, cy))
        return "🎆 砰！"
    def get_description(self) -> str:
        return "fireworks at cursor"

class SparkleCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import SparkleAnimation
        cx, cy = canvas.cursor_x, canvas.cursor_y
        canvas.anim_mgr.add(SparkleAnimation(cx, cy))
        return "✨ 闪闪发光"
    def get_description(self) -> str:
        return "sparkle effect at cursor"

class MagicCircleCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import MagicCircleAnimation
        cx, cy = canvas.cursor_x, canvas.cursor_y
        canvas.anim_mgr.add(MagicCircleAnimation(cx, cy, canvas.pen_color))
        return "🔮 魔法阵"
    def get_description(self) -> str:
        return "magic circle at cursor"

class StartStarfallCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import StarfallAnimation
        canvas.anim_mgr.add(StarfallAnimation(canvas.WIDTH, canvas.HEIGHT))
        return "🌠 流星划过"
    def get_description(self) -> str:
        return "start starfall effect"

class StopStarfallCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import StarfallAnimation
        before = canvas.anim_mgr.active_count
        canvas.anim_mgr._animations = [
            a for a in canvas.anim_mgr._animations
            if not isinstance(a, StarfallAnimation)
        ]
        after = canvas.anim_mgr.active_count
        return f"☄ 流星停了 (removed {before - after})"
    def get_description(self) -> str:
        return "stop starfall effect"


# ─── Phase 5: Premium Effects ────────────────────────────────────────────────

class StartSnowCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import SnowAnimation
        canvas.anim_mgr.add(SnowAnimation(canvas.WIDTH, canvas.HEIGHT))
        return "❄ 下雪了"
    def get_description(self) -> str:
        return "start snow effect"

class StopSnowCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import SnowAnimation
        before = canvas.anim_mgr.active_count
        canvas.anim_mgr._animations = [
            a for a in canvas.anim_mgr._animations
            if not isinstance(a, SnowAnimation)
        ]
        after = canvas.anim_mgr.active_count
        return f"❄ 雪停了"
    def get_description(self) -> str:
        return "stop snow effect"

class StartBubblesCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import BubblesAnimation
        canvas.anim_mgr.add(BubblesAnimation(canvas.WIDTH, canvas.HEIGHT))
        return "🫧 泡泡飘起来了"
    def get_description(self) -> str:
        return "start bubbles effect"

class StopBubblesCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import BubblesAnimation
        before = canvas.anim_mgr.active_count
        canvas.anim_mgr._animations = [
            a for a in canvas.anim_mgr._animations
            if not isinstance(a, BubblesAnimation)
        ]
        after = canvas.anim_mgr.active_count
        return f"🫧 泡泡没了"
    def get_description(self) -> str:
        return "stop bubbles effect"

class StartAuroraCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import AuroraAnimation
        canvas.anim_mgr.add(AuroraAnimation(canvas.WIDTH, canvas.HEIGHT))
        return "🌌 极光出现了"
    def get_description(self) -> str:
        return "start aurora effect"

class StopAuroraCommand(Command):
    def execute(self, canvas) -> str:
        from .animation import AuroraAnimation
        before = canvas.anim_mgr.active_count
        canvas.anim_mgr._animations = [
            a for a in canvas.anim_mgr._animations
            if not isinstance(a, AuroraAnimation)
        ]
        after = canvas.anim_mgr.active_count
        return f"🌌 极光消失了"
    def get_description(self) -> str:
        return "stop aurora effect"
