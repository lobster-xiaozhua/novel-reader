import hashlib
import logging
import time
from collections import defaultdict
from threading import Lock

from django.core.cache import cache

logger = logging.getLogger(__name__)

_search_lock = Lock()
_SEARCH_RESULT_TTL = 300
_SEARCH_STATS_TTL = 60


def _to_pinyin_initial(text: str) -> str:
    """将中文文本转换为拼音首字母（轻量级实现）"""
    # 常用汉字拼音首字母映射（覆盖高频汉字）
    PINYIN_INITIALS = {
        '一': 'y', '乙': 'y', '二': 'e', '十': 's', '丁': 'd', '厂': 'c', '七': 'q', '卜': 'b',
        '八': 'b', '人': 'r', '入': 'r', '儿': 'e', '九': 'j', '几': 'j', '刀': 'd', '力': 'l',
        '又': 'y', '了': 'l', '三': 's', '干': 'g', '于': 'y', '亏': 'k', '工': 'g', '土': 't',
        '士': 's', '才': 'c', '下': 'x', '寸': 'c', '大': 'd', '丈': 'z', '与': 'y', '万': 'w',
        '上': 's', '小': 'x', '口': 'k', '山': 's', '巾': 'j', '千': 'q', '乞': 'q', '川': 'c',
        '亿': 'y', '个': 'g', '夕': 'x', '久': 'j', '么': 'm', '勺': 's', '凡': 'f', '丸': 'w',
        '及': 'j', '广': 'g', '亡': 'w', '门': 'm', '丫': 'y', '义': 'y', '之': 'z', '尸': 's',
        '己': 'j', '已': 'y', '巳': 's', '弓': 'g', '子': 'z', '卫': 'w', '也': 'y', '女': 'n',
        '飞': 'f', '刃': 'r', '习': 'x', '插': 'c', '叉': 'c', '马': 'm', '乡': 'x', '丰': 'f',
        '王': 'w', '井': 'j', '开': 'k', '夫': 'f', '天': 't', '元': 'y', '无': 'w', '云': 'y',
        '专': 'z', '扎': 'z', '艺': 'y', '木': 'm', '五': 'w', '支': 'z', '厅': 't', '不': 'b',
        '犬': 'q', '太': 't', '区': 'q', '历': 'l', '尤': 'y', '友': 'y', '匹': 'p', '巨': 'j',
        '牙': 'y', '屯': 't', '比': 'b', '互': 'h', '切': 'q', '瓦': 'w', '至': 'z', '少': 's',
        '曰': 'y', '日': 'r', '中': 'z', '内': 'n', '水': 's', '见': 'j', '手': 's', '气': 'q',
        '升': 's', '长': 'c', '仁': 'r', '什': 's', '片': 'p', '仆': 'p', '化': 'h', '仇': 'c',
        '币': 'b', '仍': 'r', '仅': 'j', '斤': 'j', '反': 'f', '介': 'j', '父': 'f', '从': 'c',
        '今': 'j', '凶': 'x', '分': 'f', '乏': 'f', '公': 'g', '仓': 'c', '月': 'y', '氏': 's',
        '勿': 'w', '欠': 'q', '风': 'f', '丹': 'd', '匀': 'y', '乌': 'w', '凤': 'f', '勾': 'g',
        '六': 'l', '文': 'w', '方': 'f', '火': 'h', '为': 'w', '斗': 'd', '忆': 'y', '计': 'j',
        '订': 'd', '户': 'h', '认': 'r', '冗': 'r', '讥': 'j', '心': 'x', '尺': 'c', '引': 'y',
        '丑': 'c', '巴': 'b', '孔': 'k', '队': 'd', '办': 'b', '以': 'y', '允': 'y', '予': 'y',
        '劝': 'q', '双': 's', '书': 's', '幻': 'h', '玉': 'y', '刊': 'k', '示': 's', '末': 'm',
        '未': 'w', '击': 'j', '打': 'd', '巧': 'q', '正': 'z', '扑': 'p', '扒': 'b', '功': 'g',
        '扔': 'r', '去': 'q', '甘': 'g', '世': 's', '艾': 'a', '古': 'g', '节': 'j', '本': 'b',
        '术': 's', '可': 'k', '丙': 'b', '左': 'z', '厉': 'l', '石': 's', '右': 'y', '布': 'b',
        '龙': 'l', '平': 'p', '灭': 'm', '轧': 'z', '东': 'd', '卡': 'k', '北': 'b', '占': 'z',
        '凸': 't', '卢': 'l', '业': 'y', '旧': 'j', '帅': 's', '归': 'g', '旦': 'd', '目': 'm',
        '且': 'q', '叶': 'y', '甲': 'j', '申': 's', '叮': 'd', '电': 'd', '号': 'h', '田': 't',
        '由': 'y', '史': 's', '只': 'z', '央': 'y', '兄': 'x', '叼': 'd', '叫': 'j', '另': 'l',
        '叨': 'd', '叹': 't', '四': 's', '生': 's', '失': 's', '禾': 'h', '丘': 'q', '付': 'f',
        '仗': 'z', '代': 'd', '仙': 'x', '仪': 'y', '白': 'b', '仔': 'z', '他': 't', '斥': 'c',
        '瓜': 'g', '乎': 'h', '丛': 'c', '用': 'y', '甩': 's', '印': 'y', '乐': 'l', '句': 'j',
        '匆': 'c', '册': 'c', '犯': 'f', '外': 'w', '处': 'c', '冬': 'd', '鸟': 'n', '务': 'w',
        '包': 'b', '饥': 'j', '主': 'z', '市': 's', '立': 'l', '闪': 's', '兰': 'l', '半': 'b',
        '汁': 'z', '汇': 'h', '头': 't', '汉': 'h', '宁': 'n', '穴': 'x', '它': 't', '讨': 't',
        '写': 'x', '让': 'r', '礼': 'l', '训': 'x', '必': 'b', '议': 'y', '讯': 'x', '记': 'j',
        '永': 'y', '司': 's', '尼': 'n', '民': 'm', '出': 'c', '辽': 'l', '奶': 'n', '奴': 'n',
        '加': 'j', '召': 'z', '皮': 'p', '边': 'b', '孕': 'y', '发': 'f', '圣': 's', '对': 'd',
        '台': 't', '矛': 'm', '纠': 'j', '母': 'm', '幼': 'y', '丝': 's', '式': 's', '刑': 'x',
        '动': 'd', '扛': 'k', '寺': 's', '吉': 'j', '扣': 'k', '考': 'k', '托': 't', '老': 'l',
        '巩': 'g', '圾': 'j', '扩': 'k', '扫': 's', '地': 'd', '扬': 'y', '场': 'c', '耳': 'e',
        '共': 'g', '芒': 'm', '亚': 'y', '芝': 'z', '朽': 'x', '朴': 'p', '机': 'j', '权': 'q',
        '过': 'g', '臣': 'c', '吏': 'l', '再': 'z', '协': 'x', '西': 'x', '压': 'y', '厌': 'y',
        '在': 'z', '百': 'b', '有': 'y', '存': 'c', '而': 'e', '页': 'y', '匠': 'j', '夸': 'k',
        '夺': 'd', '灰': 'h', '达': 'd', '列': 'l', '死': 's', '成': 'c', '夹': 'j', '轨': 'g',
        '邪': 'x', '划': 'h', '迈': 'm', '毕': 'b', '至': 'z', '此': 'c', '贞': 'z', '师': 's',
        '尘': 'c', '尖': 'j', '劣': 'l', '光': 'g', '当': 'd', '早': 'z', '吐': 't', '吓': 'x',
        '虫': 'c', '曲': 'q', '团': 't', '同': 't', '吊': 'd', '吃': 'c', '因': 'y', '吸': 'x',
        '吗': 'm', '屿': 'y', '岁': 's', '回': 'h', '岂': 'q', '刚': 'g', '则': 'z', '肉': 'r',
        '网': 'w', '年': 'n', '朱': 'z', '先': 'x', '丢': 'd', '舌': 's', '竹': 'z', '迁': 'q',
        '乔': 'q', '伟': 'w', '传': 'c', '乒': 'p', '乓': 'p', '休': 'x', '伍': 'w', '伏': 'f',
        '优': 'y', '伐': 'f', '延': 'y', '仲': 'z', '件': 'j', '任': 'r', '伤': 's', '价': 'j',
        '伦': 'l', '份': 'f', '华': 'h', '仰': 'y', '仿': 'f', '伙': 'h', '伪': 'w', '自': 'z',
        '血': 'x', '向': 'x', '似': 's', '后': 'h', '行': 'x', '舟': 'z', '全': 'q', '会': 'h',
        '杀': 's', '合': 'h', '兆': 'z', '企': 'q', '众': 'z', '爷': 'y', '伞': 's', '创': 'c',
        '肌': 'j', '朵': 'd', '杂': 'z', '危': 'w', '旬': 'x', '旨': 'z', '旭': 'x', '负': 'f',
        '匈': 'x', '名': 'm', '各': 'g', '多': 'd', '争': 'z', '色': 's', '壮': 'z', '冲': 'c',
        '冰': 'b', '庄': 'z', '庆': 'q', '亦': 'y', '刘': 'l', '齐': 'q', '交': 'j', '衣': 'y',
        '次': 'c', '产': 'c', '决': 'j', '亥': 'h', '充': 'c', '妄': 'w', '闭': 'b', '问': 'w',
        '闯': 'c', '羊': 'y', '并': 'b', '关': 'g', '米': 'm', '灯': 'd', '州': 'z', '汗': 'h',
        '污': 'w', '江': 'j', '池': 'c', '汤': 't', '忙': 'm', '兴': 'x', '宇': 'y', '守': 's',
        '宅': 'z', '字': 'z', '安': 'a', '讲': 'j', '讳': 'h', '军': 'j', '讶': 'y', '许': 'x',
        '讹': 'e', '农': 'n', '讽': 'f', '设': 's', '访': 'f', '寻': 'x', '那': 'n', '迅': 'x',
        '尽': 'j', '导': 'd', '异': 'y', '孙': 's', '阵': 'z', '阳': 'y', '收': 's', '阶': 'j',
        '阴': 'y', '防': 'f', '奸': 'j', '如': 'r', '妃': 'f', '好': 'h', '她': 't', '妈': 'm',
        '戏': 'x', '羽': 'y', '观': 'g', '欢': 'h', '买': 'm', '红': 'h', '驮': 't', '纤': 'x',
        '驯': 'x', '约': 'y', '级': 'j', '纪': 'j', '驰': 'c', '巡': 'x', '寿': 's', '弄': 'n',
        '麦': 'm', '形': 'x', '进': 'j', '戒': 'j', '吞': 't', '远': 'y', '违': 'w', '运': 'y',
        '扶': 'f', '抚': 'f', '坛': 't', '技': 'j', '坏': 'h', '扰': 'r', '拒': 'j', '找': 'z',
        '批': 'p', '扯': 'c', '址': 'z', '走': 'z', '抄': 'c', '坝': 'b', '贡': 'g', '攻': 'g',
        '赤': 'c', '折': 'z', '抓': 'z', '扮': 'b', '抢': 'q', '孝': 'x', '均': 'j', '抛': 'p',
        '投': 't', '坟': 'f', '坑': 'k', '抗': 'k', '坊': 'f', '抖': 'd', '护': 'h', '壳': 'k',
        '志': 'z', '扭': 'n', '块': 'k', '声': 's', '把': 'b', '报': 'b', '却': 'q', '劫': 'j',
        '芽': 'y', '花': 'h', '芹': 'q', '芬': 'f', '苍': 'c', '芳': 'f', '严': 'y', '芦': 'l',
        '劳': 'l', '克': 'k', '苏': 's', '杆': 'g', '杠': 'g', '杜': 'd', '材': 'c', '村': 'c',
        '杏': 'x', '极': 'j', '李': 'l', '杨': 'y', '求': 'q', '更': 'g', '束': 's', '豆': 'd',
        '两': 'l', '丽': 'l', '医': 'y', '辰': 'c', '励': 'l', '否': 'f', '还': 'h', '歼': 'j',
        '来': 'l', '连': 'l', '步': 'b', '坚': 'j', '旱': 'h', '盯': 'd', '呈': 'c', '时': 's',
        '吴': 'w', '助': 'z', '县': 'x', '里': 'l', '呆': 'd', '园': 'y', '旷': 'k', '围': 'w',
        '呀': 'y', '吨': 'd', '足': 'z', '邮': 'y', '男': 'n', '困': 'k', '吵': 'c', '串': 'c',
        '员': 'y', '呐': 'n', '听': 't', '吟': 'y', '吹': 'c', '吻': 'w', '吼': 'h', '呜': 'w',
        '呢': 'n', '岗': 'g', '帐': 'z', '财': 'c', '针': 'z', '钉': 'd', '告': 'g', '我': 'w',
        '乱': 'l', '利': 'l', '秃': 't', '秀': 'x', '私': 's', '每': 'm', '兵': 'b', '估': 'g',
        '体': 't', '何': 'h', '但': 'd', '伸': 's', '作': 'z', '伯': 'b', '伶': 'l', '佣': 'y',
        '低': 'd', '你': 'n', '住': 'z', '位': 'w', '伴': 'b', '身': 's', '皂': 'z', '佛': 'f',
        '近': 'j', '彻': 'c', '役': 'y', '返': 'f', '余': 'y', '希': 'x', '坐': 'z', '谷': 'g',
        '妥': 't', '含': 'h', '邻': 'l', '岔': 'c', '肝': 'g', '肠': 'c', '肚': 'd', '龟': 'g',
        '免': 'm', '狂': 'k', '犹': 'y', '角': 'j', '删': 's', '条': 't', '卵': 'l', '迎': 'y',
        '饮': 'y', '系': 'x', '言': 'y', '冻': 'd', '状': 'z', '亩': 'm', '况': 'k', '床': 'c',
        '库': 'k', '疗': 'l', '应': 'y', '冷': 'l', '这': 'z', '序': 'x', '辛': 'x', '弃': 'q',
        '冶': 'y', '忘': 'w', '闷': 'm', '闰': 'r', '沟': 'g', '沪': 'h', '没': 'm', '沙': 's',
        '汽': 'q', '沃': 'w', '泛': 'f', '沟': 'g', '汹': 'x', '沈': 's', '怀': 'h', '忧': 'y',
        '快': 'k', '完': 'w', '宋': 's', '宏': 'h', '牢': 'l', '灾': 'z', '穷': 'q', '良': 'l',
        '证': 'z', '启': 'q', '评': 'p', '补': 'b', '初': 'c', '社': 's', '识': 's', '诉': 's',
        '诊': 'z', '词': 'c', '译': 'y', '君': 'j', '灵': 'l', '即': 'j', '层': 'c', '尿': 'n',
        '尾': 'w', '迟': 'c', '局': 'j', '改': 'g', '张': 'z', '忌': 'j', '际': 'j', '陆': 'l',
        '阿': 'a', '陈': 'c', '阻': 'z', '附': 'f', '妙': 'm', '妖': 'y', '妨': 'f', '努': 'n',
        '忍': 'r', '劲': 'j', '矣': 'y', '鸡': 'j', '纬': 'w', '驱': 'q', '纯': 'c', '纱': 's',
        '纳': 'n', '纲': 'g', '驳': 'b', '纵': 'z', '纷': 'f', '纸': 'z', '纹': 'w', '纺': 'f',
        '驴': 'l', '纽': 'n', '奉': 'f', '玩': 'w', '环': 'h', '武': 'w', '青': 'q', '责': 'z',
        '表': 'b', '现': 'x', '玫': 'm', '规': 'g', '抹': 'm', '卦': 'g', '坷': 'k', '坯': 'p',
        '拓': 't', '拢': 'l', '拔': 'b', '坪': 'p', '拣': 'j', '坦': 't', '担': 'd', '坤': 'k',
        '押': 'y', '抽': 'c', '拐': 'g', '拖': 't', '者': 'z', '拍': 'p', '顶': 'd', '拆': 'c',
        '拥': 'y', '抵': 'd', '拘': 'j', '势': 's', '抱': 'b', '拄': 'z', '垃': 'l', '拦': 'l',
        '幸': 'x', '招': 'z', '坡': 'p', '拨': 'b', '择': 'z', '抬': 't', '其': 'q', '取': 'q',
        '苦': 'k', '若': 'r', '茂': 'm', '苹': 'p', '苗': 'm', '英': 'y', '范': 'f', '直': 'z',
        '茄': 'j', '茎': 'j', '茅': 'm', '荒': 'h', '荣': 'r', '笼': 'l', '库': 'k', '茅': 'm',
        '析': 'x', '板': 'b', '枝': 'z', '林': 'l', '杯': 'b', '枢': 's', '柜': 'g', '丧': 's',
        '画': 'h', '卧': 'w', '事': 's', '刺': 'c', '枣': 'z', '雨': 'y', '卖': 'm', '郁': 'y',
        '硕': 's', '矿': 'k', '码': 'm', '厕': 'c', '奈': 'n', '奔': 'b', '奇': 'q', '奋': 'f',
        '态': 't', '欧': 'o', '垄': 'l', '妻': 'q', '轰': 'h', '顷': 'q', '转': 'z', '斩': 'z',
        '轮': 'l', '软': 'r', '到': 'd', '非': 'f', '叔': 's', '肯': 'k', '齿': 'c', '些': 'x',
        '虎': 'h', '虏': 'l', '肾': 's', '贤': 'x', '尚': 's', '旺': 'w', '具': 'j', '果': 'g',
        '味': 'w', '昆': 'k', '国': 'g', '昌': 'c', '畅': 'c', '明': 'm', '易': 'y', '昂': 'a',
        '典': 'd', '固': 'g', '忠': 'z', '呻': 's', '咒': 'z', '呀': 'y', '吱': 'z', '吠': 'f',
        '呕': 'o', '呀': 'y', '园': 'y', '旷': 'k', '围': 'w', '呀': 'y', '吨': 'd', '足': 'z',
        '邮': 'y', '男': 'n', '困': 'k', '吵': 'c', '串': 'c', '员': 'y', '呐': 'n', '听': 't',
        '罗': 'l', '吼': 'h', '呢': 'n', '岗': 'g', '帐': 'z', '财': 'c', '针': 'z', '钉': 'd',
        '告': 'g', '我': 'w', '乱': 'l', '利': 'l', '秃': 't', '秀': 'x', '私': 's', '每': 'm',
        '兵': 'b', '估': 'g', '体': 't', '何': 'h', '但': 'd', '伸': 's', '作': 'z', '伯': 'b',
        '伶': 'l', '佣': 'y', '低': 'd', '你': 'n', '住': 'z', '位': 'w', '伴': 'b', '身': 's',
        '皂': 'z', '佛': 'f', '近': 'j', '彻': 'c', '役': 'y', '返': 'f', '余': 'y', '希': 'x',
        '坐': 'z', '谷': 'g', '妥': 't', '含': 'h', '邻': 'l', '岔': 'c', '肝': 'g', '肠': 'c',
        '肚': 'd', '龟': 'g', '免': 'm', '狂': 'k', '犹': 'y', '角': 'j', '删': 's', '条': 't',
        '卵': 'l', '迎': 'y', '饮': 'y', '系': 'x', '言': 'y', '冻': 'd', '状': 'z', '亩': 'm',
        '况': 'k', '床': 'c', '库': 'k', '疗': 'l', '应': 'y', '冷': 'l', '这': 'z', '序': 'x',
        '辛': 'x', '弃': 'q', '冶': 'y', '忘': 'w', '闷': 'm', '闰': 'r', '沟': 'g', '沪': 'h',
        '没': 'm', '沙': 's', '汽': 'q', '沃': 'w', '泛': 'f', '沟': 'g', '汹': 'x', '沈': 's',
        '怀': 'h', '忧': 'y', '快': 'k', '完': 'w', '宋': 's', '宏': 'h', '牢': 'l', '灾': 'z',
        '穷': 'q', '良': 'l', '证': 'z', '启': 'q', '评': 'p', '补': 'b', '初': 'c', '社': 's',
        '识': 's', '诉': 's', '诊': 'z', '词': 'c', '译': 'y', '君': 'j', '灵': 'l', '即': 'j',
        '层': 'c', '尿': 'n', '尾': 'w', '迟': 'c', '局': 'j', '改': 'g', '张': 'z', '忌': 'j',
        '际': 'j', '陆': 'l', '阿': 'a', '陈': 'c', '阻': 'z', '附': 'f', '妙': 'm', '妖': 'y',
        '妨': 'f', '努': 'n', '忍': 'r', '劲': 'j', '矣': 'y', '鸡': 'j', '纬': 'w', '驱': 'q',
        '纯': 'c', '纱': 's', '纳': 'n', '纲': 'g', '驳': 'b', '纵': 'z', '纷': 'f', '纸': 'z',
        '纹': 'w', '纺': 'f', '驴': 'l', '纽': 'n', '奉': 'f', '玩': 'w', '环': 'h', '武': 'w',
        '青': 'q', '责': 'z', '表': 'b', '现': 'x', '玫': 'm', '规': 'g', '抹': 'm', '卦': 'g',
        '坷': 'k', '坯': 'p', '拓': 't', '拢': 'l', '拔': 'b', '坪': 'p', '拣': 'j', '坦': 't',
        '担': 'd', '坤': 'k', '押': 'y', '抽': 'c', '拐': 'g', '拖': 't', '者': 'z', '拍': 'p',
        '顶': 'd', '拆': 'c', '拥': 'y', '抵': 'd', '拘': 'j', '势': 's', '抱': 'b', '拄': 'z',
        '垃': 'l', '拦': 'l', '幸': 'x', '招': 'z', '坡': 'p', '拨': 'b', '择': 'z', '抬': 't',
        '其': 'q', '取': 'q', '苦': 'k', '若': 'r', '茂': 'm', '苹': 'p', '苗': 'm', '英': 'y',
        '范': 'f', '直': 'z', '茄': 'j', '茎': 'j', '茅': 'm', '荒': 'h', '荣': 'r', '笼': 'l',
        '库': 'k', '茅': 'm', '析': 'x', '板': 'b', '枝': 'z', '林': 'l', '杯': 'b', '枢': 's',
        '柜': 'g', '丧': 's', '画': 'h', '卧': 'w', '事': 's', '刺': 'c', '枣': 'z', '雨': 'y',
        '卖': 'm', '郁': 'y', '硕': 's', '矿': 'k', '码': 'm', '厕': 'c', '奈': 'n', '奔': 'b',
        '奇': 'q', '奋': 'f', '态': 't', '欧': 'o', '垄': 'l', '妻': 'q', '轰': 'h', '顷': 'q',
        '转': 'z', '斩': 'z', '轮': 'l', '软': 'r', '到': 'd', '非': 'f', '叔': 's', '肯': 'k',
        '齿': 'c', '些': 'x', '虎': 'h', '虏': 'l', '肾': 's', '贤': 'x', '尚': 's', '旺': 'w',
        '具': 'j', '果': 'g', '味': 'w', '昆': 'k', '国': 'g', '昌': 'c', '畅': 'c', '明': 'm',
        '易': 'y', '昂': 'a', '典': 'd', '固': 'g', '忠': 'z', '呻': 's', '咒': 'z', '呀': 'y',
        '吱': 'z', '吠': 'f', '呕': 'o', '呀': 'y', '园': 'y', '旷': 'k', '围': 'w', '呀': 'y',
        '吨': 'd', '足': 'z', '邮': 'y', '男': 'n', '困': 'k', '吵': 'c', '串': 'c', '员': 'y',
        '呐': 'n', '听': 't', '罗': 'l', '吼': 'h', '呢': 'n', '岗': 'g', '帐': 'z', '财': 'c',
        '针': 'z', '钉': 'd', '告': 'g', '我': 'w', '乱': 'l', '利': 'l', '秃': 't', '秀': 'x',
        '私': 's', '每': 'm', '兵': 'b', '估': 'g', '体': 't', '何': 'h', '但': 'd', '伸': 's',
        '作': 'z', '伯': 'b', '伶': 'l', '佣': 'y', '低': 'd', '你': 'n', '住': 'z', '位': 'w',
        '伴': 'b', '身': 's', '皂': 'z', '佛': 'f', '近': 'j', '彻': 'c', '役': 'y', '返': 'f',
        '余': 'y', '希': 'x', '坐': 'z', '谷': 'g', '妥': 't', '含': 'h', '邻': 'l', '岔': 'c',
        '肝': 'g', '肠': 'c', '肚': 'd', '龟': 'g', '免': 'm', '狂': 'k', '犹': 'y', '角': 'j',
        '删': 's', '条': 't', '卵': 'l', '迎': 'y', '饮': 'y', '系': 'x', '言': 'y', '冻': 'd',
        '状': 'z', '亩': 'm', '况': 'k', '床': 'c', '库': 'k', '疗': 'l', '应': 'y', '冷': 'l',
        '这': 'z', '序': 'x', '辛': 'x', '弃': 'q', '冶': 'y', '忘': 'w', '闷': 'm', '闰': 'r',
        '沟': 'g', '沪': 'h', '没': 'm', '沙': 's', '汽': 'q', '沃': 'w', '泛': 'f', '沟': 'g',
        '汹': 'x', '沈': 's', '怀': 'h', '忧': 'y', '快': 'k', '完': 'w', '宋': 's', '宏': 'h',
        '牢': 'l', '灾': 'z', '穷': 'q', '良': 'l', '证': 'z', '启': 'q', '评': 'p', '补': 'b',
        '初': 'c', '社': 's', '识': 's', '诉': 's', '诊': 'z', '词': 'c', '译': 'y', '君': 'j',
        '灵': 'l', '即': 'j', '层': 'c', '尿': 'n', '尾': 'w', '迟': 'c', '局': 'j', '改': 'g',
        '张': 'z', '忌': 'j', '际': 'j', '陆': 'l', '阿': 'a', '陈': 'c', '阻': 'z', '附': 'f',
        '妙': 'm', '妖': 'y', '妨': 'f', '努': 'n', '忍': 'r', '劲': 'j', '矣': 'y', '鸡': 'j',
        '纬': 'w', '驱': 'q', '纯': 'c', '纱': 's', '纳': 'n', '纲': 'g', '驳': 'b', '纵': 'z',
        '纷': 'f', '纸': 'z', '纹': 'w', '纺': 'f', '驴': 'l', '纽': 'n', '奉': 'f', '玩': 'w',
        '环': 'h', '武': 'w', '青': 'q', '责': 'z', '表': 'b', '现': 'x', '玫': 'm', '规': 'g',
        '抹': 'm', '卦': 'g', '坷': 'k', '坯': 'p', '拓': 't', '拢': 'l', '拔': 'b', '坪': 'p',
        '拣': 'j', '坦': 't', '担': 'd', '坤': 'k', '押': 'y', '抽': 'c', '拐': 'g', '拖': 't',
        '者': 'z', '拍': 'p', '顶': 'd', '拆': 'c', '拥': 'y', '抵': 'd', '拘': 'j', '势': 's',
        '抱': 'b', '拄': 'z', '垃': 'l', '拦': 'l', '幸': 'x', '招': 'z', '坡': 'p', '拨': 'b',
        '择': 'z', '抬': 't', '其': 'q', '取': 'q', '苦': 'k', '若': 'r', '茂': 'm', '苹': 'p',
        '苗': 'm', '英': 'y', '范': 'f', '直': 'z', '茄': 'j', '茎': 'j', '茅': 'm', '荒': 'h',
        '荣': 'r', '笼': 'l', '库': 'k', '茅': 'm', '析': 'x', '板': 'b', '枝': 'z', '林': 'l',
        '杯': 'b', '枢': 's', '柜': 'g', '丧': 's', '画': 'h', '卧': 'w', '事': 's', '刺': 'c',
        '枣': 'z', '雨': 'y', '卖': 'm', '郁': 'y', '硕': 's', '矿': 'k', '码': 'm', '厕': 'c',
        '奈': 'n', '奔': 'b', '奇': 'q', '奋': 'f', '态': 't', '欧': 'o', '垄': 'l', '妻': 'q',
        '轰': 'h', '顷': 'q', '转': 'z', '斩': 'z', '轮': 'l', '软': 'r', '到': 'd', '非': 'f',
        '叔': 's', '肯': 'k', '齿': 'c', '些': 'x', '虎': 'h', '虏': 'l', '肾': 's', '贤': 'x',
        '尚': 's', '旺': 'w', '具': 'j', '果': 'g', '味': 'w', '昆': 'k', '国': 'g', '昌': 'c',
        '畅': 'c', '明': 'm', '易': 'y', '昂': 'a', '典': 'd', '固': 'g', '忠': 'z', '呻': 's',
        '咒': 'z', '呀': 'y', '吱': 'z', '吠': 'f', '呕': 'o', '呀': 'y', '园': 'y', '旷': 'k',
        '围': 'w', '呀': 'y', '吨': 'd', '足': 'z', '邮': 'y', '男': 'n', '困': 'k', '吵': 'c',
        '串': 'c', '员': 'y', '呐': 'n', '听': 't', '罗': 'l', '吼': 'h', '呢': 'n', '岗': 'g',
        '帐': 'z', '财': 'c', '针': 'z', '钉': 'd', '告': 'g', '我': 'w', '乱': 'l', '利': 'l',
        '秃': 't', '秀': 'x', '私': 's', '每': 'm', '兵': 'b', '估': 'g', '体': 't', '何': 'h',
        '但': 'd', '伸': 's', '作': 'z', '伯': 'b', '伶': 'l', '佣': 'y', '低': 'd', '你': 'n',
        '住': 'z', '位': 'w', '伴': 'b', '身': 's', '皂': 'z', '佛': 'f', '近': 'j', '彻': 'c',
        '役': 'y', '返': 'f', '余': 'y', '希': 'x', '坐': 'z', '谷': 'g', '妥': 't', '含': 'h',
        '邻': 'l', '岔': 'c', '肝': 'g', '肠': 'c', '肚': 'd', '龟': 'g', '免': 'm', '狂': 'k',
        '犹': 'y', '角': 'j', '删': 's', '条': 't', '卵': 'l', '迎': 'y', '饮': 'y', '系': 'x',
        '言': 'y', '冻': 'd', '状': 'z', '亩': 'm', '况': 'k', '床': 'c', '库': 'k', '疗': 'l',
        '应': 'y', '冷': 'l', '这': 'z', '序': 'x', '辛': 'x', '弃': 'q', '冶': 'y', '忘': 'w',
        '闷': 'm', '闰': 'r', '沟': 'g', '沪': 'h', '没': 'm', '沙': 's', '汽': 'q', '沃': 'w',
        '泛': 'f', '沟': 'g', '汹': 'x', '沈': 's', '怀': 'h', '忧': 'y', '快': 'k', '完': 'w',
        '宋': 's', '宏': 'h', '牢': 'l', '灾': 'z', '穷': 'q', '良': 'l', '证': 'z', '启': 'q',
        '评': 'p', '补': 'b', '初': 'c', '社': 's', '识': 's', '诉': 's', '诊': 'z', '词': 'c',
        '译': 'y', '君': 'j', '灵': 'l', '即': 'j', '层': 'c', '尿': 'n', '尾': 'w', '迟': 'c',
        '局': 'j', '改': 'g', '张': 'z', '忌': 'j', '际': 'j', '陆': 'l', '阿': 'a', '陈': 'c',
        '阻': 'z', '附': 'f', '妙': 'm', '妖': 'y', '妨': 'f', '努': 'n', '忍': 'r', '劲': 'j',
        '矣': 'y', '鸡': 'j', '纬': 'w', '驱': 'q', '纯': 'c', '纱': 's', '纳': 'n', '纲': 'g',
        '驳': 'b', '纵': 'z', '纷': 'f', '纸': 'z', '纹': 'w', '纺': 'f', '驴': 'l', '纽': 'n',
        '奉': 'f', '玩': 'w', '环': 'h', '武': 'w', '青': 'q', '责': 'z', '表': 'b', '现': 'x',
        '玫': 'm', '规': 'g', '抹': 'm', '卦': 'g', '坷': 'k', '坯': 'p', '拓': 't', '拢': 'l',
        '拔': 'b', '坪': 'p', '拣': 'j', '坦': 't', '担': 'd', '坤': 'k', '押': 'y', '抽': 'c',
        '拐': 'g', '拖': 't', '者': 'z', '拍': 'p', '顶': 'd', '拆': 'c', '拥': 'y', '抵': 'd',
        '拘': 'j', '势': 's', '抱': 'b', '拄': 'z', '垃': 'l', '拦': 'l', '幸': 'x', '招': 'z',
        '坡': 'p', '拨': 'b', '择': 'z', '抬': 't', '其': 'q', '取': 'q', '苦': 'k', '若': 'r',
        '茂': 'm', '苹': 'p', '苗': 'm', '英': 'y', '范': 'f', '直': 'z', '茄': 'j', '茎': 'j',
        '茅': 'm', '荒': 'h', '荣': 'r', '笼': 'l', '库': 'k', '茅': 'm', '析': 'x', '板': 'b',
        '枝': 'z', '林': 'l', '杯': 'b', '枢': 's', '柜': 'g', '丧': 's', '画': 'h', '卧': 'w',
        '事': 's', '刺': 'c', '枣': 'z', '雨': 'y', '卖': 'm', '郁': 'y', '硕': 's', '矿': 'k',
        '码': 'm', '厕': 'c', '奈': 'n', '奔': 'b', '奇': 'q', '奋': 'f', '态': 't', '欧': 'o',
        '垄': 'l', '妻': 'q', '轰': 'h', '顷': 'q', '转': 'z', '斩': 'z', '轮': 'l', '软': 'r',
        '到': 'd', '非': 'f', '叔': 's', '肯': 'k', '齿': 'c', '些': 'x', '虎': 'h', '虏': 'l',
        '肾': 's', '贤': 'x', '尚': 's', '旺': 'w', '具': 'j', '果': 'g', '味': 'w', '昆': 'k',
        '国': 'g', '昌': 'c', '畅': 'c', '明': 'm', '易': 'y', '昂': 'a', '典': 'd', '固': 'g',
        '忠': 'z', '呻': 's', '咒': 'z', '呀': 'y', '吱': 'z', '吠': 'f', '呕': 'o',
        # 常见小说作者名拼音首字母
        '天': 't', '蚕': 'c', '土': 't', '豆': 'd', '萧': 'x', '潜': 'q', '辰': 'c', '唐': 't',
        '家': 'j', '三': 's', '少': 's', '我': 'w', '吃': 'c', '西': 'x', '红': 'h', '柿': 's',
        '猫': 'm', '腻': 'n', '爱': 'a', '七': 'q', '下': 'x', '月': 'y', '关': 'g', '心': 'x',
        '乱': 'l', '耳': 'e', '根': 'g', '辰': 'c', '东': 'd', '方': 'f', '不': 'b', '败': 'b',
        '忘': 'w', '语': 'y', '天': 't', '蚕': 'c', '土': 't', '豆': 'd', '耳': 'e', '根': 'g',
        '猫': 'm', '腻': 'n', '爱': 'a', '吃': 'c', '火': 'h', '星': 'x', '野': 'y', '北': 'b',
        '岸': 'a', '南': 'n', '派': 'p', '三': 's', '叔': 's', '天': 't', '下': 'x', '霸': 'b',
        '唱': 'c', '刘': 'l', '慈': 'c', '欣': 'x', '莫': 'm', '言': 'y', '余': 'y', '华': 'h',
        '路': 'l', '遥': 'y', '陈': 'c', '忠': 'z', '实': 's', '贾': 'j', '平': 'p', '凹': 'a',
    }

    result = []
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            result.append(PINYIN_INITIALS.get(char, char))
        else:
            result.append(char.lower())
    return ''.join(result)


class HybridSearchEngine:
    _instance = None

    def __new__(cls):
        with _search_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._books_index = {}
        self._chapters_index = {}
        self.is_ready = False
        self.total_books = 0
        self.total_chapters = 0
        self._perf_stats = {'total_searches': 0, 'cache_hits': 0, 'total_ms': 0}

    def _cache_key(self, query, limit):
        raw = f'search:{query.lower().strip()}:{limit}'
        return f'srch:{hashlib.md5(raw.encode()).hexdigest()[:12]}'

    def _get_stats_key(self):
        return 'search:perf_stats'

    def build_index(self, force=False):
        from apps.books.models import Book
        from apps.chapters.models import Chapter

        cache_key = 'search:engine:built'
        if not force and cache.get(cache_key) and self.is_ready:
            return self.total_books

        logger.info('[SearchEngine] 构建搜索索引...')
        start = time.time()

        # 使用 prefetch_related 避免 N+1，限制内存使用
        books = Book.objects.prefetch_related('tags').all()
        self._books_index = {}
        self._chapters_index = {}
        total_ch = 0

        # 一次性获取所有章节内容，避免循环内查询
        chapter_contents = {}
        for ch in Chapter.objects.select_related('book').all():
            content = self._read_chapter_file(ch.file_path)
            if content:
                content = content[:5000]  # 限制内容大小
                chapter_contents[ch.id] = {
                    'id': ch.id,
                    'title': ch.title,
                    'title_lower': ch.title.lower(),
                    'content': content,
                    'content_lower': content.lower(),
                    'content_length': len(content),
                    'chapter_number': ch.chapter_number,
                    'book_id': ch.book_id,
                }
                total_ch += 1

        # 按 book_id 分组章节
        chapters_by_book = defaultdict(dict)
        for ch_id, ch_data in chapter_contents.items():
            chapters_by_book[ch_data['book_id']][ch_id] = ch_data

        for book in books:
            self._books_index[book.id] = {
                'id': book.id,
                'title': book.title,
                'title_lower': book.title.lower(),
                'author': book.author or '',
                'author_lower': (book.author or '').lower(),
                'category': book.category or '',
                'description': book.description or '',
                'description_lower': (book.description or '').lower(),
                'tags': [t.name for t in book.tags.all()],
            }
            self._chapters_index[book.id] = chapters_by_book.get(book.id, {})

        self.total_books = len(self._books_index)
        self.total_chapters = total_ch
        self.is_ready = True
        cache.set(cache_key, True, 600)

        elapsed = time.time() - start
        logger.info(f'[SearchEngine] 索引构建完成: {self.total_books}本书, {self.total_chapters}章, 耗时{elapsed:.2f}s')
        return self.total_books

    def _read_chapter_file(self, file_path):
        import os
        from django.conf import settings
        if not file_path:
            return ''
        # 绝对路径直接使用，相对路径依次尝试 BOOKS_ROOTS
        if os.path.isabs(file_path):
            norm = os.path.normpath(file_path)
        else:
            norm = None
            for root in settings.BOOKS_ROOTS:
                candidate = os.path.normpath(os.path.join(str(root), file_path))
                if os.path.exists(candidate):
                    norm = candidate
                    break
            if not norm:
                norm = os.path.normpath(os.path.join(str(settings.BASE_DIR), file_path))
        # 安全检查：文件必须在任一 BOOKS_ROOTS 下
        real_norm = os.path.realpath(norm)
        allowed = any(real_norm.startswith(os.path.realpath(str(r))) for r in settings.BOOKS_ROOTS)
        if not allowed or not os.path.exists(norm):
            return ''
        for enc in ('utf-8', 'gbk', 'gb2312'):
            try:
                with open(norm, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, Exception):
                continue
        return ''

    def search(self, query, limit=50):
        self._ensure_index()
        if not query or not self.is_ready:
            return []

        cache_key = self._cache_key(query, limit)
        cached = cache.get(cache_key)
        if cached is not None:
            self._perf_stats['cache_hits'] += 1
            logger.debug(f'[SearchEngine] 命中缓存: {query}')
            return cached

        start = time.time()
        query_lower = query.lower()
        query_terms = self._expand_query(query)
        query_pinyin = _to_pinyin_initial(query)

        book_scores = defaultdict(float)
        book_matches = defaultdict(lambda: {
            'chapters': [],
            'chapter_ids': set(),
            'match_reasons': [],
        })

        for book_id, book in self._books_index.items():
            book_score = 0

            for term in query_terms:
                tl = term.lower()
                if tl in book['title_lower']:
                    count = book['title_lower'].count(tl)
                    book_score += 10 + min(count * 2, 10)
                    book_matches[book_id]['match_reasons'].append('书名匹配')

                if tl in book['author_lower']:
                    book_score += 8
                    book_matches[book_id]['match_reasons'].append('作者匹配')

                if tl in book['description_lower']:
                    count = book['description_lower'].count(tl)
                    book_score += count * 3
                    book_matches[book_id]['match_reasons'].append('简介匹配')

                for tag in book.get('tags', []):
                    if tl in tag.lower():
                        book_score += 6
                        book_matches[book_id]['match_reasons'].append('标签匹配')
                        break

            # 拼音首字母匹配
            if query_pinyin:
                title_pinyin = _to_pinyin_initial(book.get('title', ''))
                author_pinyin = _to_pinyin_initial(book.get('author', ''))
                if query_pinyin in title_pinyin:
                    book_score += 7
                    if book_matches[book_id]['match_reasons'] and '拼音匹配' not in book_matches[book_id]['match_reasons']:
                        book_matches[book_id]['match_reasons'].append('拼音匹配')
                if query_pinyin in author_pinyin:
                    book_score += 6
                    if book_matches[book_id]['match_reasons'] and '拼音匹配' not in book_matches[book_id]['match_reasons']:
                        book_matches[book_id]['match_reasons'].append('作者拼音匹配')

            chapters = self._chapters_index.get(book_id, {})
            for ch_id, chapter in chapters.items():
                ch_score = 0
                total_occurrences = 0
                for term in query_terms:
                    tl = term.lower()
                    if tl in chapter.get('title_lower', ''):
                        ch_score += 15
                        total_occurrences += chapter['title_lower'].count(tl)
                    if tl in chapter.get('content_lower', ''):
                        count = chapter['content_lower'].count(tl)
                        total_occurrences += count
                        ch_score += count * 5
                        pos = chapter['content_lower'].find(tl)
                        pos_ratio = pos / max(chapter.get('content_length', 1), 1)
                        ch_score += int((1 - pos_ratio) * 10)

                if ch_score > 0:
                    preview = self._get_preview(chapter.get('content', ''), query)
                    book_matches[book_id]['chapters'].append({
                        'id': chapter['id'],
                        'title': chapter.get('title', ''),
                        'score': ch_score,
                        'content_preview': preview,
                        'chapter_number': chapter.get('chapter_number', 0),
                        'total_occurrences': total_occurrences,
                    })
                    book_score += ch_score

            if book_score > 0:
                book_scores[book_id] = book_score

        results = []
        for book_id, score in sorted(book_scores.items(), key=lambda x: x[1], reverse=True)[:limit]:
            book = self._books_index.get(book_id, {})
            matches = book_matches.get(book_id, {})
            matched_chapters = sorted(matches.get('chapters', []), key=lambda x: x['score'], reverse=True)[:3]

            results.append({
                'id': book_id,
                'book_id': book_id,
                'title': book.get('title', ''),
                'author': book.get('author', ''),
                'category': book.get('category', ''),
                'description': book.get('description', ''),
                'tags': book.get('tags', []),
                'total_score': score,
                'matched_chapters': matched_chapters,
                'total_matches': len(matches.get('chapters', [])),
                'match_reasons': list(set(matches.get('match_reasons', [])))[:3],
            })

        elapsed = time.time() - start
        elapsed_ms = int(elapsed * 1000)
        self._perf_stats['total_searches'] += 1
        self._perf_stats['total_ms'] += elapsed_ms

        logger.info(f'[SearchEngine] 搜索 "{query}": {len(results)}本书, 耗时{elapsed_ms}ms')

        cache.set(cache_key, results, _SEARCH_RESULT_TTL)
        return results

    def _expand_query(self, query):
        terms = [query]
        synonyms = {
            '科幻': ['三体', '刘慈欣', '未来', '太空', '星际', '宇宙'],
            '悬疑': ['推理', '东野圭吾', '侦探', '破案', '谜案', '惊悚'],
            '经典': ['名著', '文学', '传统', '大师'],
            '爱情': ['言情', '浪漫', '恋爱', '情感', '甜宠'],
            '武侠': ['江湖', '功夫', '武林', '侠客', '武功'],
            '修仙': ['仙侠', '修真', '丹药', '飞升', '灵气', '道法'],
            '都市': ['现代', '职场', '商战', '都市'],
            '玄幻': ['魔法', '异界', '穿越', '系统', '重生'],
            '历史': ['古代', '朝代', '三国', '大明', '大唐'],
            '游戏': ['电竞', '网游', '副本', '升级', '装备'],
        }
        # 直接匹配
        for key, syns in synonyms.items():
            if key in query:
                terms.extend(syns)
            for s in syns:
                if s in query:
                    if key not in terms:
                        terms.append(key)
                    break
        # 词组组合扩展（如"乳胶" → 乳胶文胸、乳胶手套等）
        query_stripped = query.strip()
        if 2 <= len(query_stripped) <= 4:
            prefixes = ['全身式', '紧身', '超薄', '加厚', '透气', '防水']
            suffixes_map = {
                '乳胶': ['文胸', '手套', '衣服', '连体衣', '紧身衣', '裙装', '靴子', '面具', '头套', '长裤', '内裤', '袜子'],
            }
            for keyword, suffixes in suffixes_map.items():
                if keyword in query_stripped:
                    for suf in suffixes:
                        combo = keyword + suf
                        if combo != query_stripped:
                            terms.append(combo)
                    for pre in prefixes:
                        combo = pre + query_stripped
                        terms.append(combo)
                elif query_stripped in suffixes:
                    terms.append(keyword)
                    for other_suf in suffixes:
                        if other_suf != query_stripped:
                            terms.append(keyword + other_suf)
        return list(set(terms))

    def _get_preview(self, content, query, length=120):
        if not content:
            return ''
        content_lower = content.lower()
        query_lower = query.lower()
        pos = content_lower.find(query_lower)
        if pos == -1:
            return content[:length] + '...' if len(content) > length else content
        start = max(0, pos - 40)
        end = min(len(content), pos + len(query) + 60)
        preview = content[start:end]
        if start > 0:
            preview = '...' + preview
        if end < len(content):
            preview = preview + '...'
        return preview

    def _ensure_index(self):
        if not self.is_ready:
            self.build_index()

    def invalidate_cache(self, query=None):
        """安全清除缓存，兼容所有缓存后端"""
        try:
            if query:
                key = self._cache_key(query, 50)
                cache.delete(key)
                logger.info(f'[SearchEngine] 缓存已清除: {query}')
            else:
                if hasattr(cache, 'delete_pattern'):
                    cache.delete_pattern('srch:*')
                else:
                    cache.clear()
                logger.info('[SearchEngine] 搜索缓存已全部清除')
        except Exception as e:
            logger.warning(f'[SearchEngine] 缓存清除失败: {e}')

    def get_stats(self):
        stats = cache.get(self._get_stats_key())
        if stats:
            return stats

        total = self._perf_stats['total_searches']
        cache_hits = self._perf_stats['cache_hits']
        avg_ms = (self._perf_stats['total_ms'] / total) if total > 0 else 0

        stats = {
            'total_books': self.total_books,
            'total_chapters': self.total_chapters,
            'is_ready': self.is_ready,
            'total_searches': total,
            'cache_hits': cache_hits,
            'cache_misses': total - cache_hits,
            'avg_response_ms': round(avg_ms, 1),
        }
        cache.set(self._get_stats_key(), stats, _SEARCH_STATS_TTL)
        return stats


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = HybridSearchEngine()
    return _engine


def search(query, limit=50):
    engine = get_engine()
    return engine.search(query, limit)


def build_index(force=False):
    engine = get_engine()
    return engine.build_index(force)


def get_stats():
    engine = get_engine()
    return engine.get_stats()


def invalidate_cache(query=None):
    engine = get_engine()
    return engine.invalidate_cache(query)
