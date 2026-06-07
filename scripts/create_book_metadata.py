#!/usr/bin/env python3
"""为每本书创建 metadata.json"""
import json
import os

BOOKS_DIR = '/workspace/data/books'

metadata = {
    '斗破苍穹': {'author': '天蚕土豆', 'category': '玄幻', 'description': '天才少年萧炎在创造了家族空前绝后的修炼纪录后突然成了废人，种种打击接踵而至。就在他即将绝望的时候，一缕灵魂从他手上的戒指里浮现，一扇全新的大门在面前开启！'},
    '凡人修仙传': {'author': '忘语', 'category': '仙侠', 'description': '一个普通的山村穷小子，偶然之下，跨入到一个江湖小门派，虽然资质平庸，但依靠自身努力和合理算计修炼成仙。'},
    '完美世界': {'author': '辰东', 'category': '玄幻', 'description': '一粒尘可填海，一根草斩尽日月星辰，弹指间天翻地覆。群雄并起，万族林立，诸圣争霸，乱天动地。'},
    '剑来': {'author': '烽火戏诸侯', 'category': '仙侠', 'description': '大千世界，无奇不有。我陈平安，唯有一剑，可搬山，倒海，降妖，镇魔，敕神，摘星，断江，摧城，开天！'},
    '诡秘之主': {'author': '爱潜水的乌贼', 'category': '奇幻', 'description': '蒸汽与机械的浪潮中，谁能触及非凡？历史和黑暗的迷雾里，又是谁在耳语？我从诡秘中醒来，睁眼看见这个世界。'},
    '大奉打更人': {'author': '卖报小郎君', 'category': '玄幻', 'description': '这个世界，有儒；有道；有佛；有妖；有术士。警校毕业的许七安幽幽醒来，发现自己身处牢狱之中，三日后流放边陲……'},
    '庆余年': {'author': '猫腻', 'category': '历史', 'description': '积善之家，必有余庆。留余庆，留余庆，忽遇恩人；幸娘亲，幸娘亲，积得阴功。一个年轻的病人，因为一次毫不意外的经历，重生到一个完全不同的世界。'},
    '雪中悍刀行': {'author': '烽火戏诸侯', 'category': '武侠', 'description': '有个白狐儿脸，佩双刀绣冬春雷，要做那天下第一。湖底有白发老魁爱吃荤。缺门牙老仆背剑匣。还有个世子殿下，日日游手好闲。'},
    '全职高手': {'author': '蝴蝶蓝', 'category': '游戏', 'description': '网游荣耀中被誉为教科书级别的顶尖高手叶修，因为种种原因遭到俱乐部的驱逐。离开职业圈的他寄身于一家网吧成了一个小小的网管。'},
    '盗墓笔记': {'author': '南派三叔', 'category': '悬疑', 'description': '五十年前，一群长沙土夫子挖到一部战国帛书，残篇中记载了一座奇特的战国古墓的位置。五十年后，一个年轻人发现了这个秘密。'},
}

for book_name, info in metadata.items():
    book_dir = os.path.join(BOOKS_DIR, book_name)
    os.makedirs(book_dir, exist_ok=True)
    filepath = os.path.join(book_dir, 'metadata.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    print(f'已创建: {filepath}')

print('\n全部 metadata.json 创建完成！')