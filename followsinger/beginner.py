"""Phonetic proximity to common Mandarin syllables, without tone matching.

These are first-pass mnemonics, not translations or accurate pronunciations.
Clusters, final stops, nasal vowels and non-Mandarin sounds lose information.
"""
from functools import lru_cache
import re
import unicodedata

from .phonetics import ipa
from .pronunciation import _kakasi

# A familiar character for each usable Mandarin syllable; no rare characters.
SYLLABLES = """
a啊 o哦 e额 ai爱 ei诶 ao奥 ou欧 an安 en恩 ang昂 eng嗯 er尔
ba吧 bo波 bai白 bei贝 bao包 ban班 ben本 bang邦 beng崩 bi比 bie别 biao标 bian边 bin宾 bing冰 bu布
pa趴 po坡 pai拍 pei配 pao跑 pou剖 pan潘 pen喷 pang旁 peng朋 pi皮 pie撇 piao飘 pian偏 pin拼 ping平 pu普
ma妈 mo摸 me么 mai麦 mei美 mao猫 mou某 man慢 men门 mang忙 meng萌 mi米 mie灭 miao喵 miu谬 mian棉 min民 ming明 mu木
fa发 fo佛 fei飞 fou否 fan凡 fen芬 fang方 feng风 fu夫
da达 de德 dai戴 dei得 dao刀 dou豆 dan丹 deng登 dang当 di迪 die蝶 dia嗲 diao雕 diu丢 dian点 ding丁 dong东 du都 duo多 dui对 duan端 dun敦
ta塔 te特 tai太 tao涛 tou偷 tan坦 tang汤 teng腾 ti提 tie贴 tiao挑 tian天 ting听 tong通 tu图 tuo托 tui推 tuan团 tun吞
na娜 ne呢 nai奈 nei内 nao闹 nou耨 nan南 nen嫩 nang囊 neng能 ni尼 nie涅 niao鸟 niu牛 nian年 nin您 niang娘 ning宁 nong农 nu努 nuo诺 nuan暖 nv女 nve虐
la拉 lo咯 le勒 lai莱 lei雷 lao劳 lou楼 lan兰 lang朗 leng冷 li里 lie列 liao聊 liu流 lian连 lin林 liang凉 ling灵 long龙 lu鲁 luo罗 luan鸾 lun轮 lv吕 lve略
ga嘎 ge哥 gai盖 gei给 gao高 gou勾 gan干 gen根 gang刚 geng更 gong公 gu古 gua瓜 guo郭 guai乖 gui归 guan关 gun滚 guang光
ka卡 ke科 kai开 kao考 kou扣 kan看 ken肯 kang康 keng坑 kong空 ku库 kua夸 kuo阔 kuai快 kui亏 kuan宽 kun昆 kuang框
ha哈 he赫 hai嗨 hei嘿 hao好 hou侯 han韩 hen很 hang杭 heng恒 hong红 hu呼 hua花 huo霍 huai怀 hui灰 huan欢 hun昏 huang黄
ji吉 jia加 jie杰 jiao交 jiu纠 jian坚 jin金 jiang江 jing京 jiong炯 ju居 jue觉 juan娟 jun君
qi七 qia恰 qie切 qiao敲 qiu秋 qian千 qin亲 qiang枪 qing青 qiong穷 qu曲 que缺 quan圈 qun群
xi西 xia夏 xie谢 xiao肖 xiu休 xian仙 xin新 xiang香 xing星 xiong兄 xu虚 xue薛 xuan宣 xun勋
zha扎 zhe哲 zhai摘 zhao招 zhou周 zhan詹 zhen真 zhang张 zheng争 zhong中 zhu朱 zhua抓 zhuo卓 zhuai拽 zhui追 zhuan专 zhun准 zhuang庄
cha查 che车 chai柴 chao超 chou抽 chan禅 chen陈 chang昌 cheng成 chong冲 chu出 chua欻 chuo戳 chuai揣 chui吹 chuan川 chun春 chuang窗
sha沙 she舍 shai晒 shao稍 shou收 shan山 shen申 shang商 sheng声 shu书 shua刷 shuo说 shuai摔 shui谁 shuan栓 shun顺 shuang双
re热 rao饶 rou柔 ran然 ren人 rang让 reng仍 rong荣 ru茹 ruo若 rui瑞 ruan软 run润
za杂 ze则 zai再 zao早 zou走 zan赞 zen怎 zang藏 zeng增 zong宗 zu足 zuo佐 zui嘴 zuan钻 zun尊
ca擦 ce策 cai才 cao曹 cou凑 can餐 cen岑 cang苍 ceng层 cong聪 cu粗 cuo搓 cui崔 cuan窜 cun村
sa萨 se瑟 sai赛 sao骚 sou搜 san三 sen森 sang桑 seng僧 song松 su苏 suo索 sui随 suan酸 sun孙
yi伊 ya呀 ye耶 yao瑶 you优 yan烟 yin因 yang央 ying英 yong拥 yu鱼 yue约 yuan元 yun云
wu乌 wa哇 wo沃 wai歪 wei威 wan万 wen温 wang王 weng翁
"""

INITIALS = {"zh": "ʈʂ", "ch": "ʈʂʰ", "sh": "ʂ", "r": "ʐ", "z": "ts", "c": "tsʰ", "s": "s",
            "b": "b", "p": "p", "m": "m", "f": "f", "d": "d", "t": "t", "n": "n", "l": "l",
            "g": "ɡ", "k": "k", "h": "h", "j": "tɕ", "q": "tɕʰ", "x": "ɕ", "y": "j", "w": "w"}
FINALS = {"a": "a", "o": "o", "e": "ə", "ai": "aɪ", "ei": "eɪ", "ao": "aʊ", "ou": "oʊ",
          "an": "an", "en": "ən", "ang": "ɑŋ", "eng": "əŋ", "ong": "uŋ", "i": "i", "u": "u", "v": "y",
          "ia": "ja", "ie": "jɛ", "iao": "jaʊ", "iu": "joʊ", "ian": "jɛn", "in": "in", "iang": "jɑŋ", "ing": "iŋ", "iong": "juŋ",
          "ua": "wa", "uo": "wo", "uai": "waɪ", "ui": "weɪ", "uan": "wan", "un": "wən", "uang": "wɑŋ", "ve": "yɛ", "er": "ɚ"}
VOWELS = set("aeiouyɑɒæɛəɜɞɐɔʊɪɯɤøœɚʌɨ")
MULTI = ("ʈʂʰ", "tɕʰ", "tsʰ", "tʃ", "dʒ", "tɕ", "dʑ", "ʈʂ", "ts", "dz", "aɪ", "aʊ", "eɪ", "oʊ", "ɔɪ")
NASALS = {"ɑ̃": "ɑŋ", "ɔ̃": "ɔŋ", "ɛ̃": "ɛn", "œ̃": "ən"}
ISOLATED = {"p": "普", "b": "布", "t": "特", "d": "德", "k": "克", "ɡ": "格", "m": "姆", "n": "恩", "ŋ": "嗯",
            "l": "尔", "ɹ": "尔", "r": "尔", "ʁ": "尔", "ɾ": "尔", "ʐ": "尔", "f": "夫", "v": "夫", "s": "斯", "z": "兹",
            "ʃ": "什", "ʒ": "日", "θ": "斯", "ð": "兹", "h": "赫", "x": "赫", "ɕ": "西", "tʃ": "吃", "dʒ": "吉", "j": "伊", "w": "乌"}


def tokens(value):
    value = value.replace("g", "ɡ").replace("ɐ", "a").replace("ɯ", "u")
    for source, replacement in NASALS.items():
        value = value.replace(source, replacement)
    value = "".join(c for c in unicodedata.normalize("NFD", value) if c not in "ˈˌːˑʲ̩̃͜͡" and not unicodedata.combining(c))
    result = []
    while value:
        symbol = next((part for part in MULTI if value.startswith(part)), value[0])
        result.append(symbol)
        value = value[len(symbol):]
    return result


def _pinyin_sound(spelling):
    initial = next((key for key in INITIALS if spelling.startswith(key)), "")
    final = spelling[len(initial):]
    if initial == "y":
        special = {"i": "i", "in": "in", "ing": "iŋ", "ong": "juŋ", "u": "y", "ue": "yɛ", "uan": "yɛn", "un": "yn"}
        return special.get(final, "j" + FINALS.get(final, final))
    if initial == "w":
        return "u" if final == "u" else "w" + FINALS.get(final, final)
    if initial in {"j", "q", "x"} and final.startswith("u"):
        final_sound = {"u": "y", "ue": "yɛ", "uan": "yɛn", "un": "yn"}.get(final, final)
    elif initial in {"zh", "ch", "sh", "r", "z", "c", "s"} and final == "i":
        final_sound = "ɨ"
    else:
        final_sound = FINALS.get(final, final)
    return INITIALS.get(initial, "") + final_sound


# Rough articulatory neighborhoods. Exact matches always score best.
NEIGHBORS = (set("aɑɒɐæ"), set("eɛæ"), set("əɜɞɤɚɨ"), set("oɔ"), set("uʊɯ"), set("iɪ"), set("yøœ"),
             set("pb"), set("td"), set("kɡ"), set("fvɸ"), set("szθð"), set("ʂʃɕʒʐ"), set("lrɹʁɾʐ"), set("hxχ"), set("nŋɲ"))


def _distance(a, b):
    if a == b:
        return 0
    if {a, b} == {"ʒ", "ʐ"}:
        return .15
    if a[0] in VOWELS and b[0] in VOWELS and (len(a) > 1 or len(b) > 1):
        return _distance(a[0], b[0]) + .4 * abs(len(a) - len(b))
    if any(a in group and b in group for group in NEIGHBORS):
        return .35
    if a[0] in VOWELS and b[0] in VOWELS:
        positions = {"i": (0, 1), "ɪ": (.2, .85), "e": (.4, 1), "ɛ": (.6, 1), "æ": (.8, 1), "a": (1, .5), "ɑ": (1, 0), "ɒ": (.9, 0), "o": (.4, 0), "ɔ": (.6, 0), "u": (0, 0), "ʊ": (.2, .1), "y": (0, .8), "ø": (.4, .7), "œ": (.6, .7), "ʌ": (.7, .3)}
        x, y = positions.get(a, (.5, .5)), positions.get(b, (.5, .5))
        return .3 + abs(x[0] - y[0]) + .7 * abs(x[1] - y[1])
    if a in {"tʃ", "dʒ", "tɕ", "dʑ", "ʈʂ"} and b in {"tʃ", "dʒ", "tɕ", "dʑ", "ʈʂ"}:
        return .4
    return 1.6


def _edit_distance(source, target):
    previous = [i * 1.4 for i in range(len(target) + 1)]
    for i, a in enumerate(source, 1):
        current = [i * 1.4]
        for j, b in enumerate(target, 1):
            current.append(min(previous[j] + 1.4, current[j-1] + 1.4, previous[j-1] + _distance(a, b)))
        previous = current
    return previous[-1]


@lru_cache(maxsize=1)
def _candidates():
    return [(tokens(_pinyin_sound(entry[:-1])), entry[-1]) for entry in SYLLABLES.split()]


@lru_cache(maxsize=4096)
def _nearest(syllable):
    source = list(syllable)
    # Common teaching conventions for sequences Mandarin cannot represent
    # with one syllable (not spelling-based substitutions).
    familiar = {("k", "o", "n"): "空", ("w", "ɜ"): "沃", ("t", "w", "a"): "图哇"}
    if syllable in familiar:
        return familiar[syllable]
    # Do not add an absent initial/coda merely to improve the vowel match.
    return min(_candidates(), key=lambda candidate: _edit_distance(source, candidate[0]))[1]


def chinese_hint(phonemes):
    result = []
    for word in re.split(r"[\s·,;.!?，。！？]+", phonemes):
        sounds = tokens(word.replace("-", ""))
        sounds = [s for s in sounds if s[0] in VOWELS or s in ISOLATED or s in {"tɕ", "tɕʰ", "dʑ", "ts", "dz", "ɲ", "ɸ", "ʂ", "ʈʂ"}]
        pieces = []
        cursor = 0
        while cursor < len(sounds):
            nucleus = next((i for i in range(cursor, len(sounds)) if sounds[i][0] in VOWELS), None)
            if nucleus is None:
                pieces.extend(ISOLATED.get(s, "") for s in sounds[cursor:])
                break
            onset = sounds[cursor:nucleus]
            # Keep a glide attached to the nucleus (French toi, Korean nyeong).
            keep = 2 if len(onset) >= 2 and onset[-1] in {"j", "w"} else 1
            pieces.extend(ISOLATED.get(s, "") for s in onset[:-keep])
            syllable = onset[-keep:] + [sounds[nucleus]]
            cursor = nucleus + 1
            if cursor < len(sounds) and sounds[cursor] in {"n", "ŋ", "m"} and (cursor+1 == len(sounds) or sounds[cursor+1][0] not in VOWELS):
                syllable.append("n" if sounds[cursor] == "m" else sounds[cursor])
                cursor += 1
            pieces.append(_nearest(tuple(syllable)))
        if pieces:
            result.append("".join(pieces))
    return " · ".join(result)


def _japanese_ipa(text):
    roman = " ".join(part["hepburn"] for part in _kakasi().convert(text))
    roman = roman.replace("konnichiha", "konnichiwa").replace("konbanha", "konbanwa")
    rules = {"shi": "ɕi", "chi": "tɕʰi", "tsu": "tsu", "fu": "ɸu", "ji": "dʑi",
             "sha": "ɕa", "shu": "ɕu", "sho": "ɕo", "cha": "tɕa", "chu": "tɕu", "cho": "tɕo", "ja": "dʑa", "ju": "dʑu", "jo": "dʑo"}
    roman = roman.lower()
    for spelling, sound in rules.items():
        roman = roman.replace(spelling, sound)
    roman = re.sub(r"([ktsp])\1", r"\1", roman)
    return roman.replace("y", "j").replace("r", "ɾ")


@lru_cache(maxsize=4096)
def beginner_reading(text, language):
    if not text.strip():
        return ""
    sounds = _japanese_ipa(text) if language == "ja" else ipa(text, language)
    result = chinese_hint(sounds)
    return result if result else "暂无可用谐音"
