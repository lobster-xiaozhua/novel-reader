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
        '傲': 'a', '凹': 'a', '奥': 'a', '安': 'a', '岸': 'a', '挨': 'a', '昂': 'a', '暗': 'a', '爱': 'a', '矮': 'a', '碍': 'a', '艾': 'a',
        '袄': 'a', '阿': 'a', '不': 'b', '丙': 'b', '伯': 'b', '伴': 'b', '便': 'b', '保': 'b', '倍': 'b', '傍': 'b', '八': 'b', '兵': 'b',
        '冰': 'b', '别': 'b', '剥': 'b', '办': 'b', '勃': 'b', '包': 'b', '北': 'b', '半': 'b', '博': 'b', '卜': 'b', '变': 'b', '坝': 'b',
        '埠': 'b', '堡': 'b', '壁': 'b', '备': 'b', '奔': 'b', '宝': 'b', '宾': 'b', '崩': 'b', '巴': 'b', '币': 'b', '布': 'b', '帮': 'b',
        '并': 'b', '弊': 'b', '彼': 'b', '必': 'b', '怖': 'b', '悲': 'b', '扁': 'b', '扒': 'b', '扮': 'b', '把': 'b', '报': 'b', '抱': 'b',
        '拌': 'b', '拔': 'b', '拜': 'b', '拨': 'b', '捕': 'b', '掰': 'b', '搏': 'b', '搬': 'b', '摆': 'b', '播': 'b', '斑': 'b', '暴': 'b',
        '本': 'b', '杯': 'b', '板': 'b', '柄': 'b', '柏': 'b', '标': 'b', '棒': 'b', '榜': 'b', '步': 'b', '比': 'b', '毕': 'b', '毙': 'b',
        '泊': 'b', '波': 'b', '滨': 'b', '爆': 'b', '爸': 'b', '版': 'b', '玻': 'b', '班': 'b', '瓣': 'b', '疤': 'b', '病': 'b', '白': 'b',
        '百': 'b', '碑': 'b', '笔': 'b', '笨': 'b', '簿': 'b', '绑': 'b', '编': 'b', '罢': 'b', '背': 'b', '胞': 'b', '脖': 'b', '膀': 'b',
        '臂': 'b', '般': 'b', '菠': 'b', '薄': 'b', '补': 'b', '表': 'b', '被': 'b', '贝': 'b', '败': 'b', '蹦': 'b', '辈': 'b', '辨': 'b',
        '辩': 'b', '边': 'b', '逼': 'b', '遍': 'b', '避': 'b', '邦': 'b', '部': 'b', '鄙': 'b', '闭': 'b', '雹': 'b', '霸': 'b', '鞭': 'b',
        '饱': 'b', '饼': 'b', '驳': 'b', '鼻': 'b', '丑': 'c', '丛': 'c', '串': 'c', '乘': 'c', '产': 'c', '仇': 'c', '从': 'c', '仓': 'c',
        '传': 'c', '侧': 'c', '促': 'c', '倡': 'c', '偿': 'c', '储': 'c', '催': 'c', '充': 'c', '册': 'c', '冲': 'c', '凑': 'c', '出': 'c',
        '创': 'c', '初': 'c', '刺': 'c', '匆': 'c', '匙': 'c', '厂': 'c', '厕': 'c', '厨': 'c', '参': 'c', '叉': 'c', '吃': 'c', '吵': 'c',
        '吹': 'c', '呈': 'c', '唇': 'c', '唱': 'c', '场': 'c', '垂': 'c', '城': 'c', '处': 'c', '存': 'c', '察': 'c', '寸': 'c', '尘': 'c',
        '尝': 'c', '尺': 'c', '层': 'c', '岔': 'c', '崇': 'c', '川': 'c', '差': 'c', '常': 'c', '床': 'c', '彩': 'c', '彻': 'c', '惨': 'c',
        '惩': 'c', '愁': 'c', '慈': 'c', '成': 'c', '才': 'c', '扯': 'c', '承': 'c', '抄': 'c', '抽': 'c', '拆': 'c', '持': 'c', '插': 'c',
        '摧': 'c', '撑': 'c', '撤': 'c', '操': 'c', '擦': 'c', '敞': 'c', '斥': 'c', '昌': 'c', '春': 'c', '朝': 'c', '材': 'c', '村': 'c',
        '查': 'c', '柴': 'c', '楚': 'c', '槽': 'c', '次': 'c', '此': 'c', '残': 'c', '池': 'c', '沉': 'c', '测': 'c', '潮': 'c', '灿': 'c',
        '炊': 'c', '炒': 'c', '炽': 'c', '猖': 'c', '猜': 'c', '畅': 'c', '畜': 'c', '疮': 'c', '瞅': 'c', '磁': 'c', '秤': 'c', '称': 'c',
        '程': 'c', '稠': 'c', '穿': 'c', '窗': 'c', '窜': 'c', '策': 'c', '筹': 'c', '粗': 'c', '纯': 'c', '绸': 'c', '缠': 'c', '翅': 'c',
        '翠': 'c', '耻': 'c', '肠': 'c', '脆': 'c', '臣': 'c', '舱': 'c', '苍': 'c', '茶': 'c', '草': 'c', '菜': 'c', '藏': 'c', '虫': 'c',
        '蚕': 'c', '蠢': 'c', '衬': 'c', '裁': 'c', '触': 'c', '词': 'c', '诚': 'c', '财': 'c', '赤': 'c', '趁': 'c', '超': 'c', '踩': 'c',
        '车': 'c', '辞': 'c', '辰': 'c', '迟': 'c', '酬': 'c', '醋': 'c', '采': 'c', '钞': 'c', '铲': 'c', '锄': 'c', '错': 'c', '锤': 'c',
        '长': 'c', '闯': 'c', '阐': 'c', '陈': 'c', '除': 'c', '雌': 'c', '颤': 'c', '餐': 'c', '馋': 'c', '驰': 'c', '齿': 'c', '丁': 'd',
        '东': 'd', '丢': 'd', '丹': 'd', '代': 'd', '但': 'd', '低': 'd', '倒': 'd', '党': 'd', '典': 'd', '冬': 'd', '冻': 'd', '凳': 'd',
        '刀': 'd', '到': 'd', '动': 'd', '单': 'd', '叠': 'd', '叨': 'd', '叮': 'd', '叼': 'd', '吊': 'd', '吨': 'd', '呆': 'd', '地': 'd',
        '垫': 'd', '堆': 'd', '堕': 'd', '堤': 'd', '堵': 'd', '多': 'd', '大': 'd', '夺': 'd', '定': 'd', '对': 'd', '导': 'd', '岛': 'd',
        '帝': 'd', '带': 'd', '底': 'd', '店': 'd', '度': 'd', '弟': 'd', '弹': 'd', '当': 'd', '待': 'd', '得': 'd', '德': 'd', '怠': 'd',
        '悼': 'd', '惰': 'd', '懂': 'd', '戴': 'd', '打': 'd', '抖': 'd', '抵': 'd', '担': 'd', '挡': 'd', '捣': 'd', '掉': 'd', '搭': 'd',
        '敌': 'd', '斗': 'd', '断': 'd', '旦': 'd', '朵': 'd', '杜': 'd', '栋': 'd', '档': 'd', '段': 'd', '殿': 'd', '毒': 'd', '沌': 'd',
        '洞': 'd', '淀': 'd', '淡': 'd', '渡': 'd', '滴': 'd', '灯': 'd', '点': 'd', '爹': 'd', '独': 'd', '电': 'd', '登': 'd', '的': 'd',
        '盗': 'd', '盯': 'd', '盾': 'd', '督': 'd', '瞪': 'd', '短': 'd', '祷': 'd', '稻': 'd', '端': 'd', '笛': 'd', '第': 'd', '等': 'd',
        '答': 'd', '缎': 'd', '耽': 'd', '肚': 'd', '胆': 'd', '荡': 'd', '董': 'd', '蛋': 'd', '蝶': 'd', '袋': 'd', '订': 'd', '诞': 'd',
        '读': 'd', '调': 'd', '豆': 'd', '贷': 'd', '赌': 'd', '跌': 'd', '蹈': 'd', '蹲': 'd', '躲': 'd', '达': 'd', '迪': 'd', '递': 'd',
        '逗': 'd', '逮': 'd', '道': 'd', '都': 'd', '钉': 'd', '钓': 'd', '队': 'd', '陡': 'd', '雕': 'd', '顶': 'd', '顿': 'd', '颠': 'd',
        '二': 'e', '儿': 'e', '尔': 'e', '恩': 'e', '恶': 'e', '而': 'e', '耳': 'e', '蛾': 'e', '讹': 'e', '额': 'e', '饿': 'e', '鹅': 'e',
        '丰': 'f', '乏': 'f', '付': 'f', '份': 'f', '仿': 'f', '伏': 'f', '伐': 'f', '佛': 'f', '俘': 'f', '傅': 'f', '冯': 'f', '凡': 'f',
        '凤': 'f', '分': 'f', '副': 'f', '匪': 'f', '反': 'f', '发': 'f', '吠': 'f', '否': 'f', '坊': 'f', '坟': 'f', '复': 'f', '夫': 'f',
        '奉': 'f', '奋': 'f', '妃': 'f', '妇': 'f', '妨': 'f', '富': 'f', '封': 'f', '峰': 'f', '帆': 'f', '幅': 'f', '府': 'f', '废': 'f',
        '愤': 'f', '房': 'f', '扶': 'f', '抚': 'f', '放': 'f', '斧': 'f', '方': 'f', '服': 'f', '沸': 'f', '法': 'f', '泛': 'f', '浮': 'f',
        '烦': 'f', '烽': 'f', '父': 'f', '犯': 'f', '番': 'f', '疯': 'f', '福': 'f', '符': 'f', '粉': 'f', '粪': 'f', '繁': 'f', '纷': 'f',
        '纺': 'f', '缝': 'f', '罚': 'f', '翻': 'f', '肤': 'f', '肥': 'f', '肺': 'f', '腐': 'f', '腹': 'f', '芬': 'f', '芳': 'f', '范': 'f',
        '蜂': 'f', '覆': 'f', '讽': 'f', '访': 'f', '负': 'f', '贩': 'f', '费': 'f', '赴': 'f', '辅': 'f', '辐': 'f', '返': 'f', '逢': 'f',
        '锋': 'f', '阀': 'f', '防': 'f', '附': 'f', '非': 'f', '风': 'f', '飞': 'f', '饭': 'f', '个': 'g', '乖': 'g', '估': 'g', '供': 'g',
        '光': 'g', '公': 'g', '共': 'g', '关': 'g', '冠': 'g', '刚': 'g', '刮': 'g', '割': 'g', '功': 'g', '勾': 'g', '卦': 'g', '古': 'g',
        '各': 'g', '告': 'g', '哥': 'g', '固': 'g', '国': 'g', '够': 'g', '姑': 'g', '孤': 'g', '官': 'g', '宫': 'g', '岗': 'g', '工': 'g',
        '巩': 'g', '干': 'g', '广': 'g', '弓': 'g', '归': 'g', '怪': 'g', '恭': 'g', '惯': 'g', '感': 'g', '戈': 'g', '拐': 'g', '拱': 'g',
        '挂': 'g', '搞': 'g', '改': 'g', '攻': 'g', '故': 'g', '敢': 'g', '更': 'g', '杆': 'g', '杠': 'g', '构': 'g', '果': 'g', '柜': 'g',
        '根': 'g', '格': 'g', '桂': 'g', '棍': 'g', '概': 'g', '歌': 'g', '沟': 'g', '港': 'g', '溉': 'g', '滚': 'g', '灌': 'g', '狗': 'g',
        '瓜': 'g', '甘': 'g', '盖': 'g', '稿': 'g', '竿': 'g', '管': 'g', '糕': 'g', '纲': 'g', '给': 'g', '缸': 'g', '罐': 'g', '耕': 'g',
        '肝': 'g', '股': 'g', '胳': 'g', '膏': 'g', '裹': 'g', '观': 'g', '规': 'g', '诡': 'g', '该': 'g', '谷': 'g', '贡': 'g', '购': 'g',
        '贯': 'g', '贵': 'g', '赶': 'g', '跟': 'g', '轨': 'g', '过': 'g', '钙': 'g', '钢': 'g', '钩': 'g', '锅': 'g', '闺': 'g', '阁': 'g',
        '隔': 'g', '雇': 'g', '革': 'g', '顾': 'g', '馆': 'g', '骨': 'g', '高': 'g', '鬼': 'g', '鸽': 'g', '鼓': 'g', '龟': 'g', '乎': 'h',
        '互': 'h', '亥': 'h', '伙': 'h', '会': 'h', '何': 'h', '侯': 'h', '划': 'h', '化': 'h', '华': 'h', '号': 'h', '合': 'h', '后': 'h',
        '含': 'h', '吼': 'h', '和': 'h', '唤': 'h', '回': 'h', '坏': 'h', '好': 'h', '宏': 'h', '宦': 'h', '幻': 'h', '怀': 'h', '恒': 'h',
        '悍': 'h', '户': 'h', '护': 'h', '旱': 'h', '欢': 'h', '毁': 'h', '汇': 'h', '汉': 'h', '汗': 'h', '沪': 'h', '河': 'h', '浩': 'h',
        '混': 'h', '湖': 'h', '火': 'h', '灰': 'h', '环': 'h', '画': 'h', '皇': 'h', '禾': 'h', '红': 'h', '花': 'h', '荒': 'h', '虎': 'h',
        '蝴': 'h', '讳': 'h', '话': 'h', '轰': 'h', '还': 'h', '魂': 'h', '鸿': 'h', '黑': 'h', '久': 'j', '九': 'j', '井': 'j', '交': 'j',
        '仅': 'j', '今': 'j', '介': 'j', '件': 'j', '价': 'j', '具': 'j', '军': 'j', '决': 'j', '几': 'j', '击': 'j', '剑': 'j', '加': 'j',
        '劫': 'j', '劲': 'j', '匠': 'j', '即': 'j', '及': 'j', '句': 'j', '叫': 'j', '吉': 'j', '君': 'j', '圾': 'j', '均': 'j', '坚': 'j',
        '基': 'j', '夹': 'j', '奸': 'j', '家': 'j', '将': 'j', '尖': 'j', '尽': 'j', '局': 'j', '巨': 'j', '己': 'j', '巾': 'j', '忌': 'j',
        '戒': 'j', '技': 'j', '拒': 'j', '拘': 'j', '拣': 'j', '教': 'j', '斤': 'j', '旧': 'j', '机': 'j', '极': 'j', '歼': 'j', '江': 'j',
        '甲': 'j', '界': 'j', '监': 'j', '祭': 'j', '箭': 'j', '纠': 'j', '级': 'j', '纪': 'j', '肌': 'j', '节': 'j', '茄': 'j', '茎': 'j',
        '见': 'j', '觉': 'j', '角': 'j', '计': 'j', '讥': 'j', '记': 'j', '讲': 'j', '诀': 'j', '贾': 'j', '近': 'j', '进': 'j', '郡': 'j',
        '金': 'j', '阶': 'j', '际': 'j', '降': 'j', '饥': 'j', '鸡': 'j', '亏': 'k', '克': 'k', '况': 'k', '刊': 'k', '卡': 'k', '口': 'k',
        '可': 'k', '困': 'k', '坑': 'k', '块': 'k', '坤': 'k', '坷': 'k', '壳': 'k', '夸': 'k', '孔': 'k', '客': 'k', '库': 'k', '开': 'k',
        '快': 'k', '恐': 'k', '扛': 'k', '扣': 'k', '扩': 'k', '抗': 'k', '旷': 'k', '昆': 'k', '狂': 'k', '矿': 'k', '科': 'k', '空': 'k',
        '考': 'k', '肯': 'k', '苦': 'k', '两': 'l', '临': 'l', '丽': 'l', '乐': 'l', '乱': 'l', '了': 'l', '伦': 'l', '伶': 'l', '侣': 'l',
        '六': 'l', '兰': 'l', '冷': 'l', '列': 'l', '刘': 'l', '利': 'l', '力': 'l', '劣': 'l', '励': 'l', '劳': 'l', '卢': 'l', '卵': 'l',
        '历': 'l', '厉': 'l', '另': 'l', '吏': 'l', '垃': 'l', '垄': 'l', '戮': 'l', '拢': 'l', '拦': 'l', '李': 'l', '来': 'l', '林': 'l',
        '沦': 'l', '流': 'l', '灵': 'l', '炼': 'l', '牢': 'l', '理': 'l', '疗': 'l', '礼': 'l', '立': 'l', '笼': 'l', '罗': 'l', '老': 'l',
        '良': 'l', '芦': 'l', '落': 'l', '蓝': 'l', '虏': 'l', '裂': 'l', '路': 'l', '轮': 'l', '辽': 'l', '连': 'l', '邻': 'l', '郎': 'l',
        '里': 'l', '陆': 'l', '驴': 'l', '龙': 'l', '么': 'm', '买': 'm', '亩': 'm', '免': 'm', '卖': 'm', '名': 'm', '吗': 'm', '命': 'm',
        '墓': 'm', '妈': 'm', '妙': 'm', '忙': 'm', '抹': 'm', '明': 'm', '木': 'm', '末': 'm', '梦': 'm', '母': 'm', '每': 'm', '民': 'm',
        '没': 'm', '灭': 'm', '牧': 'm', '猫': 'm', '玫': 'm', '目': 'm', '矛': 'm', '码': 'm', '秘': 'm', '米': 'm', '美': 'm', '脉': 'm',
        '芒': 'm', '苗': 'm', '茂': 'm', '茅': 'm', '莫': 'm', '蒙': 'm', '迈': 'm', '门': 'm', '闷': 'm', '马': 'm', '魔': 'm', '麦': 'm',
        '你': 'n', '内': 'n', '农': 'n', '努': 'n', '南': 'n', '呐': 'n', '呢': 'n', '奈': 'n', '女': 'n', '奴': 'n', '奶': 'n', '宁': 'n',
        '尼': 'n', '尿': 'n', '年': 'n', '弄': 'n', '念': 'n', '扭': 'n', '男': 'n', '纳': 'n', '纽': 'n', '能': 'n', '腻': 'n', '逆': 'n',
        '那': 'n', '难': 'n', '鸟': 'n', '呕': 'o', '欧': 'o', '乒': 'p', '乓': 'p', '仆': 'p', '匹': 'p', '坡': 'p', '坪': 'p', '坯': 'p',
        '平': 'p', '扑': 'p', '批': 'p', '抛': 'p', '拍': 'p', '朴': 'p', '派': 'p', '片': 'p', '皮': 'p', '盘': 'p', '破': 'p', '苹': 'p',
        '评': 'p', '辟': 'p', '七': 'q', '且': 'q', '丘': 'q', '乔': 'q', '乞': 'q', '企': 'q', '全': 'q', '其': 'q', '切': 'q', '劝': 'q',
        '区': 'q', '千': 'q', '却': 'q', '去': 'q', '取': 'q', '启': 'q', '器': 'q', '奇': 'q', '契': 'q', '妻': 'q', '岂': 'q', '巧': 'q',
        '庆': 'q', '弃': 'q', '情': 'q', '抢': 'q', '曲': 'q', '权': 'q', '枪': 'q', '欠': 'q', '气': 'q', '求': 'q', '汽': 'q', '潜': 'q',
        '犬': 'q', '穷': 'q', '穹': 'q', '芹': 'q', '迁': 'q', '青': 'q', '顷': 'q', '驱': 'q', '骑': 'q', '齐': 'q', '人': 'r', '仁': 'r',
        '仍': 'r', '任': 'r', '入': 'r', '冗': 'r', '刃': 'r', '如': 'r', '忍': 'r', '扔': 'r', '扰': 'r', '日': 'r', '肉': 'r', '若': 'r',
        '荣': 'r', '融': 'r', '认': 'r', '让': 'r', '软': 'r', '闰': 'r', '三': 's', '上': 's', '世': 's', '丝': 's', '丧': 's', '书': 's',
        '事': 's', '什': 's', '伞': 's', '伤': 's', '伸': 's', '似': 's', '使': 's', '僧': 's', '删': 's', '势': 's', '勺': 's', '十': 's',
        '升': 's', '双': 's', '叔': 's', '史': 's', '司': 's', '呻': 's', '善': 's', '噬': 's', '四': 's', '圣': 's', '士': 's', '声': 's',
        '失': 's', '始': 's', '孙': 's', '守': 's', '宋': 's', '实': 's', '宿': 's', '寺': 's', '寿': 's', '射': 's', '少': 's', '尚': 's',
        '尸': 's', '山': 's', '岁': 's', '巳': 's', '市': 's', '帅': 's', '师': 's', '式': 's', '手': 's', '扫': 's', '收': 's', '时': 's',
        '术': 's', '杀': 's', '束': 's', '枢': 's', '柿': 's', '森': 's', '死': 's', '氏': 's', '水': 's', '沈': 's', '沙': 's', '生': 's',
        '甩': 's', '申': 's', '石': 's', '硕': 's', '碎': 's', '示': 's', '社': 's', '神': 's', '私': 's', '纱': 's', '肾': 's', '舌': 's',
        '色': 's', '苏': 's', '誓': 's', '设': 's', '识': 's', '诉': 's', '诗': 's', '说': 's', '身': 's', '闪': 's', '他': 't', '体': 't',
        '凸': 't', '厅': 't', '台': 't', '叹': 't', '同': 't', '吐': 't', '吞': 't', '听': 't', '唐': 't', '团': 't', '土': 't', '坛': 't',
        '坦': 't', '塌': 't', '天': 't', '太': 't', '头': 't', '她': 't', '妥': 't', '它': 't', '屠': 't', '屯': 't', '态': 't', '托': 't',
        '投': 't', '抬': 't', '拓': 't', '拖': 't', '推': 't', '条': 't', '汤': 't', '特': 't', '田': 't', '秃': 't', '突': 't', '统': 't',
        '讨': 't', '驮': 't', '万': 'w', '丸': 'w', '为': 'w', '乌': 'w', '五': 'w', '亡': 'w', '伍': 'w', '伟': 'w', '伪': 'w', '位': 'w',
        '务': 'w', '勿': 'w', '卧': 'w', '卫': 'w', '危': 'w', '吴': 'w', '吻': 'w', '呜': 'w', '味': 'w', '围': 'w', '外': 'w', '妄': 'w',
        '完': 'w', '尾': 'w', '巫': 'w', '忘': 'w', '我': 'w', '文': 'w', '无': 'w', '旺': 'w', '未': 'w', '武': 'w', '污': 'w', '沃': 'w',
        '王': 'w', '玩': 'w', '瓦': 'w', '纬': 'w', '纹': 'w', '网': 'w', '违': 'w', '问': 'w', '下': 'x', '习': 'x', '乡': 'x', '些': 'x',
        '仙': 'x', '休': 'x', '侠': 'x', '修': 'x', '兄': 'x', '先': 'x', '兴': 'x', '写': 'x', '凶': 'x', '刑': 'x', '匈': 'x', '协': 'x',
        '县': 'x', '向': 'x', '吓': 'x', '吸': 'x', '夕': 'x', '孝': 'x', '寻': 'x', '小': 'x', '巡': 'x', '希': 'x', '幸': 'x', '序': 'x',
        '形': 'x', '心': 'x', '悬': 'x', '戏': 'x', '旬': 'x', '旭': 'x', '星': 'x', '朽': 'x', '杏': 'x', '析': 'x', '欣': 'x', '汹': 'x',
        '现': 'x', '秀': 'x', '穴': 'x', '系': 'x', '纤': 'x', '萧': 'x', '血': 'x', '行': 'x', '西': 'x', '训': 'x', '讯': 'x', '许': 'x',
        '贤': 'x', '辛': 'x', '迅': 'x', '邪': 'x', '醒': 'x', '雄': 'x', '雪': 'x', '驯': 'x', '一': 'y', '与': 'y', '业': 'y', '严': 'y',
        '丫': 'y', '义': 'y', '乙': 'y', '也': 'y', '予': 'y', '于': 'y', '云': 'y', '亚': 'y', '亦': 'y', '亿': 'y', '以': 'y', '仪': 'y',
        '仰': 'y', '优': 'y', '余': 'y', '佣': 'y', '允': 'y', '元': 'y', '冶': 'y', '勇': 'y', '匀': 'y', '医': 'y', '印': 'y', '压': 'y',
        '厌': 'y', '原': 'y', '又': 'y', '友': 'y', '右': 'y', '叶': 'y', '吟': 'y', '呀': 'y', '员': 'y', '因': 'y', '园': 'y', '央': 'y',
        '妖': 'y', '婴': 'y', '孕': 'y', '宇': 'y', '尤': 'y', '屿': 'y', '已': 'y', '幼': 'y', '应': 'y', '延': 'y', '异': 'y', '引': 'y',
        '役': 'y', '忆': 'y', '忧': 'y', '怨': 'y', '扬': 'y', '押': 'y', '拥': 'y', '易': 'y', '曰': 'y', '月': 'y', '有': 'y', '杨': 'y',
        '永': 'y', '洋': 'y', '游': 'y', '爷': 'y', '牙': 'y', '犹': 'y', '玉': 'y', '用': 'y', '由': 'y', '疑': 'y', '矣': 'y', '约': 'y',
        '缘': 'y', '羊': 'y', '羽': 'y', '艺': 'y', '芽': 'y', '英': 'y', '药': 'y', '衣': 'y', '言': 'y', '议': 'y', '讶': 'y', '译': 'y',
        '语': 'y', '越': 'y', '迎': 'y', '运': 'y', '远': 'y', '遥': 'y', '邮': 'y', '郁': 'y', '野': 'y', '银': 'y', '阳': 'y', '阴': 'y',
        '陨': 'y', '隐': 'y', '雨': 'y', '页': 'y', '饮': 'y', '丈': 'z', '专': 'z', '中': 'z', '主': 'z', '之': 'z', '争': 'z', '仔': 'z',
        '仗': 'z', '仲': 'z', '众': 'z', '住': 'z', '作': 'z', '兆': 'z', '再': 'z', '则': 'z', '助': 'z', '占': 'z', '只': 'z', '召': 'z',
        '吱': 'z', '咒': 'z', '在': 'z', '址': 'z', '坐': 'z', '坠': 'z', '壮': 'z', '子': 'z', '字': 'z', '宅': 'z', '宙': 'z', '尊': 'z',
        '州': 'z', '左': 'z', '帐': 'z', '庄': 'z', '座': 'z', '张': 'z', '志': 'z', '忠': 'z', '战': 'z', '扎': 'z', '执': 'z', '找': 'z',
        '抓': 'z', '折': 'z', '拄': 'z', '招': 'z', '择': 'z', '支': 'z', '斩': 'z', '旨': 'z', '早': 'z', '智': 'z', '朱': 'z', '杂': 'z',
        '枝': 'z', '枣': 'z', '正': 'z', '殖': 'z', '汁': 'z', '灾': 'z', '状': 'z', '皂': 'z', '直': 'z', '真': 'z', '知': 'z', '祖': 'z',
        '竹': 'z', '筑': 'z', '纵': 'z', '纸': 'z', '者': 'z', '职': 'z', '自': 'z', '至': 'z', '舟': 'z', '芝': 'z', '证': 'z', '诊': 'z',
        '诸': 'z', '贞': 'z', '责': 'z', '贼': 'z', '走': 'z', '足': 'z', '轧': 'z', '转': 'z', '这': 'z', '重': 'z', '针': 'z', '阵': 'z',
        '阻': 'z',
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

    def _get_content_hash(self):
        combined = str(len(self._books_index)) + str(len(self._chapters_index))
        if self._books_index:
            first_book = next(iter(self._books_index.values()))
            combined += first_book.get('title', '')
        return hashlib.md5(combined.encode()).hexdigest()[:8]

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
            current_hash = self._get_content_hash()
            cached_hash = cache.get(f'{cache_key}:hash')
            if cached_hash == current_hash:
                self._perf_stats['cache_hits'] += 1
                logger.debug(f'[SearchEngine] 命中缓存: {query}')
                return cached
            else:
                logger.debug(f'[SearchEngine] 缓存已过期（索引变更）: {query}')
                cache.delete(cache_key)

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
                # 全拼匹配：去掉元音字母后匹配（如 doupo→dp, dp∈dpcq）
                query_consonants = ''.join(c for c in query_pinyin if c not in 'aeiou')
                if len(query_consonants) >= 2 and query_consonants in title_pinyin:
                    book_score += 7
                    if book_matches[book_id]['match_reasons'] and '拼音匹配' not in book_matches[book_id]['match_reasons']:
                        book_matches[book_id]['match_reasons'].append('拼音匹配')
                if query_pinyin in author_pinyin:
                    book_score += 6
                    if book_matches[book_id]['match_reasons'] and '拼音匹配' not in book_matches[book_id]['match_reasons']:
                        book_matches[book_id]['match_reasons'].append('作者拼音匹配')
                # 作者全拼匹配
                if len(query_consonants) >= 2 and query_consonants in author_pinyin:
                    book_score += 6
                    if book_matches[book_id]['match_reasons'] and '作者拼音匹配' not in book_matches[book_id]['match_reasons']:
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
        cache.set(f'{cache_key}:hash', self._get_content_hash(), _SEARCH_RESULT_TTL)
        return results

    def _expand_query(self, query):
        terms = [query]
        synonyms = {
            '玄幻': ['魔法', '异界', '穿越', '系统', '重生', '斗气', '武魂', '血脉', '奇遇', '金手指', '开挂', '逆天'],
            '仙侠': ['修真', '修仙', '丹药', '飞升', '灵气', '道法', '法宝', '飞剑', '阵法', '符箓', '渡劫', '元婴'],
            '武侠': ['江湖', '功夫', '武林', '侠客', '武功', '内力', '轻功', '门派', '帮派', '盟主', '兵器', '秘籍'],
            '科幻': ['三体', '刘慈欣', '未来', '太空', '星际', '宇宙', '机甲', 'AI', '人工智能', '机器人', '外星', '文明'],
            '悬疑': ['推理', '侦探', '破案', '谜案', '惊悚', '犯罪', '谋杀', '失踪', '反转', '真相', '密室', '暗号'],
            '都市': ['现代', '职场', '商战', '总裁', '豪门', '校园', '青春', '逆袭', '奋斗', '创业', '升职', '恋爱'],
            '历史': ['古代', '朝代', '三国', '大明', '大唐', '秦朝', '汉朝', '宋朝', '元朝', '清朝', '战国', '宫廷'],
            '游戏': ['电竞', '网游', '副本', '升级', '装备', '公会', 'PK', 'BOSS', '打怪', '任务', '技能', '职业'],
            '灵异': ['恐怖', '鬼怪', '惊悚', '诡异', '阴间', '冥界', '招魂', '附身', '驱魔', '阴阳', '道士', '僵尸'],
            '军事': ['战争', '特种兵', '部队', '战场', '枪战', '谍战', '间谍', '佣兵', '坦克', '战机', '航母', '特种部队'],
            '竞技': ['体育', '篮球', '足球', '电竞', '比赛', '冠军', '联赛', '世界杯', '奥运会', '运动员', '教练', '战队'],
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
