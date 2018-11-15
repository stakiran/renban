# -*- coding: utf-8 -*-

import os
import re
import sys

def abort(msg):
    print('Error!: {0}'.format(msg))
    exit(1)

def get_filename(path):
    return os.path.basename(path)

def get_basename(path):
    return os.path.splitext(get_filename(path))[0]

def get_extension(path):
    return os.path.splitext(get_filename(path))[1]

def file2list(filepath):
    ret = []
    with open(filepath, encoding='utf8', mode='r') as f:
        ret = [line.rstrip('\n') for line in f.readlines()]
    return ret

def list2file(filepath, ls):
    with open(filepath, encoding='utf8', mode='w') as f:
        f.writelines(['{:}\n'.format(line) for line in ls] )

def get_matched_groups_with_list(regular_expression, findee_text):
    """ @return [] if no matched. 
    @return A list if matched. """
    pattern = re.compile(regular_expression)
    return pattern.findall(findee_text)

def create_renban_pattern(mark, sectionlevel):
    # [^@](@{1}[0-9a-zA-Z_]+)
    #   |  | |
    #   mark |
    #        |
    #    section depth

    ret = ''
    ret += '[^{}]'.format(mark)
    ret += '('
    ret += '{}'.format(mark)
    ret += '{' + str(sectionlevel) + '}'
    ret += '[0-9a-zA-Z_]+'
    ret += ')'
    return ret

class RenbanMarkCounter:
    def __init__(self):
        self._counters = {}

        # 大見出しの連番が更新されたら中見出し以降はリセットされる.
        # 中見出しの連番が更新されたら小見出しはリセットされる.
        # ……を実現する用.
        self._clearee_counter = []

        self._displaytext_creators = []

    def set_subsection(self, counter):
        self._clearee_counter.append(counter)
        return self

    def set_displayer(self, f):
        """ @param f (key, count) を受け取って表示用文字列を返す関数. """
        self._displaytext_creators.append(f)
        return self

    def get_displaytext(self, key):
        for f in self._displaytext_creators:
            current_count = self._counters[key]
            displaytext = f(key, current_count)
            if displaytext==None:
                continue
            return displaytext
        raise RuntimeError('[RenbanMarkCounter] No displaytext function about "{}" key'.format(key))

    def count(self, key):
        if key in self._counters:
            self._counters[key] += 1
        else:
            self._counters[key] = 1

        self._clear_after_counting(key)

    def clear(self, key):
        if not key in self._counters:
            return
        del self._counters[key]

    def _clear_after_counting(self, key):
        for interpreter in self._clearee_counter:
            interpreter.clear(key)

    def __str__(self):
        return str(self._counters)

class RenbanMan:
    VALID_RENBANMARK_NAMES = ['n', 'p']

    def __init__(self, mark):
        if not isinstance(mark, str) or len(mark)!=1:
            raise RuntimeError('[RenbanMan] `mark` parameter must be a 1-length string.')

        self._mark = mark
        self._mark_sec1 = mark
        self._mark_sec2 = mark*2
        self._mark_sec3 = mark*3

        self._pattern_sec1 = create_renban_pattern(mark, 1)
        self._pattern_sec2 = create_renban_pattern(mark, 2)
        self._pattern_sec3 = create_renban_pattern(mark, 3)

        sec1_counter = RenbanMarkCounter()
        sec2_counter = RenbanMarkCounter()
        sec3_counter = RenbanMarkCounter()
        sec1_counter.set_subsection(sec2_counter).set_subsection(sec3_counter)
        sec2_counter.set_subsection(sec3_counter)
        sec1_counter.set_displayer(Displayers.dai_n_sho_zenkaku) \
                    .set_displayer(Displayers.dai_n_bu_kanji)
        sec2_counter.set_displayer(Displayers.n_setsu_plain_zenkaku)
        sec3_counter.set_displayer(Displayers.empty)
        self._sec1_counter = sec1_counter
        self._sec2_counter = sec2_counter
        self._sec3_counter = sec3_counter

    def __str__(self):
        args = [
            self._mark_sec1, self._pattern_sec1,
            self._mark_sec2, self._pattern_sec2,
            self._mark_sec3, self._pattern_sec3,
        ]
        return """[RenbanMan]
LV1 {} => {}
LV2 {} => {}
LV3 {} => {}""".format(*args)

    def is_renban_target_line(self, line):
        return line.find(self._mark)!=-1

    def _convert_to_renbaned_line(self, line, mark_of_section, pattern_of_section, counter_obj):
        ''' @retval [False, _] 変換不要なので line をそのまま使ってください.
        @retval [True, converted_line] 変換を実行したので, converted_line を使ってください. '''

        # [renbanmark]
        # 
        # @chapter
        # ^^^^^^^^
        # 12222222   1:mark   2:name
        #
        # "renban mark" consists of 1-mark and 1-name.

        retval_skip = [False, None]

        matched_strings = get_matched_groups_with_list(pattern_of_section, line)
        if len(matched_strings)==0:
            return retval_skip

        # とりあえず [0] だけ使う(= 一行に複数の renban mark 指定は無いとみなす)
        renban_mark = matched_strings[0]

        # @hoge -> ['', 'hoge']
        #               ^^^^^^^
        _, name = renban_mark.split(mark_of_section)
        if not name in RenbanMan.VALID_RENBANMARK_NAMES:
            return retval_skip

        counter_obj.count(name)
        before = renban_mark
        after  = counter_obj.get_displaytext(name)

        retval_done = [True, line.replace(before, after)]
        return retval_done

    def convert_to_renbaned_line(self, line):
        result_about_section1 = self._convert_to_renbaned_line(
            line,
            self._mark_sec1,
            self._pattern_sec1,
            self._sec1_counter
        )
        if result_about_section1[0]:
            return result_about_section1[1]

        result_about_section2 = self._convert_to_renbaned_line(
            line,
            self._mark_sec2,
            self._pattern_sec2,
            self._sec2_counter
        )
        if result_about_section2[0]:
            return result_about_section2[1]

        result_about_section3 = self._convert_to_renbaned_line(
            line,
            self._mark_sec3,
            self._pattern_sec3,
            self._sec3_counter
        )
        if result_about_section3[0]:
            return result_about_section3[1]

        return line

class Displayers:
    @staticmethod
    def is_invalid_key(key, validkey):
        return key!=validkey

    @staticmethod
    def empty(key, count):
        return ''

    @staticmethod
    def dai_n_sho_zenkaku(key, count):
        if Displayers.is_invalid_key(key, 'n'):
            return None
        zenkaku_count = str(count)
        zenkaku_count = zenkaku_count.replace('0', '０') \
                                     .replace('1', '１') \
                                     .replace('2', '２') \
                                     .replace('3', '３') \
                                     .replace('4', '４') \
                                     .replace('5', '５') \
                                     .replace('6', '６') \
                                     .replace('7', '７') \
                                     .replace('8', '８') \
                                     .replace('9', '９')
        return '第{}章'.format(zenkaku_count)

    @staticmethod
    def dai_n_bu_kanji(key, count):
        # 十部という大作はさすがに無いと思う.
        if Displayers.is_invalid_key(key, 'p'):
            return None
        zenkaku_count = str(count)
        kanji_count = zenkaku_count.replace('1', '一') \
                                   .replace('2', '二') \
                                   .replace('3', '三') \
                                   .replace('4', '四') \
                                   .replace('5', '五') \
                                   .replace('6', '六') \
                                   .replace('7', '七') \
                                   .replace('8', '八') \
                                   .replace('9', '九')
        return '第{}部'.format(kanji_count)

    @staticmethod
    def n_setsu_plain_zenkaku(key, count):
        if Displayers.is_invalid_key(key, 'n'):
            return None
        zenkaku_count = str(count)
        zenkaku_count = zenkaku_count.replace('0', '０') \
                                     .replace('1', '１') \
                                     .replace('2', '２') \
                                     .replace('3', '３') \
                                     .replace('4', '４') \
                                     .replace('5', '５') \
                                     .replace('6', '６') \
                                     .replace('7', '７') \
                                     .replace('8', '８') \
                                     .replace('9', '９')
        return '{}'.format(zenkaku_count)

def get_renbaned_lines(lines, mark):
    sec1_mark = mark
    sec2_mark = mark*2
    sec3_mark = mark*3

    renbanman = RenbanMan(mark)

    outlines = []
    for i,line in enumerate(lines):
        newline = line
        if renbanman.is_renban_target_line(line):
            newline = renbanman.convert_to_renbaned_line(line)
        outlines.append(newline)

    return outlines

def test():
    pattern_sec1 = '[^@](@{1}[0-9a-zA-Z_]+)'
    pattern_sec2 = '[^@](@{2}[0-9a-zA-Z_]+)'
    pattern_sec3 = '[^@](@{3}[0-9a-zA-Z_]+)'

    print('==== get_matched_groups_with_list ====')

    print('小見出しのみマッチ')
    r = pattern_sec3
    a = get_matched_groups_with_list(r, '# @n 大見出し')
    assert(len(a)==0)
    a = get_matched_groups_with_list(r, '# @@n 中見出し')
    assert(len(a)==0)
    a = get_matched_groups_with_list(r, '# @@@n 小見出し')
    assert(len(a)==1)
    assert(a[0]=='@@@n')

    print('中見出しのみマッチ')
    r = pattern_sec2
    a = get_matched_groups_with_list(r, '# @n 大見出し')
    assert(len(a)==0)
    a = get_matched_groups_with_list(r, '# @@n 中見出し')
    assert(len(a)==1)
    assert(a[0]=='@@n')
    a = get_matched_groups_with_list(r, '# @@@n 小見出し')
    assert(len(a)==0)

    print('大見出しのみマッチ')
    r = pattern_sec1
    a = get_matched_groups_with_list(r, '# @n 大見出し')
    assert(len(a)==1)
    assert(a[0]=='@n')
    a = get_matched_groups_with_list(r, '# @@n 中見出し')
    assert(len(a)==0)
    a = get_matched_groups_with_list(r, '# @@@n 小見出し')
    assert(len(a)==0)

    print('中見出しのみマッチ(2文字以上名でもok)')
    r = pattern_sec2
    a = get_matched_groups_with_list(r, '# @chapter 大見出し')
    assert(len(a)==0)
    a = get_matched_groups_with_list(r, '# @@part 中見出し')
    assert(len(a)==1)
    assert(a[0]=='@@part')
    a = get_matched_groups_with_list(r, '# @@@section 小見出し')
    assert(len(a)==0)

    print('メアドは大見出しにマッチする(しないのが理想だが誤って連番振られるケースは稀だろうから無視)')
    r = pattern_sec1
    a = get_matched_groups_with_list(r, '# test@test.emailaddress.com 大見出し')
    assert(len(a)!=0)

    print('==== create_renban_pattern ====')

    print('@ + レベル1')
    a = create_renban_pattern('@', 1)
    assert(a==pattern_sec1)

    print('@ + レベル3')
    a = create_renban_pattern('@', 3)
    assert(a==pattern_sec3)

    print('==== renban man ====')
    renbanman = RenbanMan('@')
    print(renbanman)

    print('==== renban mark counter ====')
    sec1_counter = RenbanMarkCounter()
    sec2_counter = RenbanMarkCounter()
    sec3_counter = RenbanMarkCounter()
    sec1_counter.set_subsection(sec2_counter).set_subsection(sec3_counter)
    sec2_counter.set_subsection(sec3_counter)
    sec1_counter.set_displayer(Displayers.dai_n_sho_zenkaku) \
                .set_displayer(Displayers.dai_n_bu_kanji)
    sec2_counter.set_displayer(Displayers.n_setsu_plain_zenkaku)

    sec1_counter.count('p') # 第一部
    sec1_counter.count('n') # 1
    sec1_counter.count('n') # 2
    sec2_counter.count('n') # 2-1
    sec2_counter.count('n') # 2-2
    sec3_counter.count('n') # 2-2-1
    sec1_counter.count('p') # 第二部
    sec1_counter.count('n') # 3
    sec2_counter.count('n') # 3-1
    sec3_counter.count('n') # 3-1-1
    sec3_counter.count('n') # 3-1-2
    print(sec1_counter)
    print(sec2_counter)
    print(sec3_counter)
    assert(sec1_counter.get_displaytext('n')=='第３章')
    assert(sec1_counter.get_displaytext('p')=='第二部')
    assert(sec2_counter.get_displaytext('n')=='１')

    print('OK. All test passed!')

def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('-i', '--input', default=None,
        help='An input filename.')

    parser.add_argument('-o', '--output', default=None,
        help='An output filename.')

    parser.add_argument('-m', '--mark', default='@', help='')

    parser.add_argument('--test', default=False, action='store_true',
        help='[DEBUG] Do unittest.')

    args = parser.parse_args()
    return args

def ____main____():
    pass

if __name__ == "__main__":
    args = parse_arguments()

    if args.test:
        test()
        exit(0)

    MYDIR = os.path.abspath(os.path.dirname(__file__))
    infilepath  = args.input
    outfilepath = args.output
    mark = args.mark
    if infilepath == None:
        abort('An input filepath required!')
    if outfilepath == None:
        abort('An output filepath required!')

    if not(os.path.exists(infilepath)):
        abort('The input file "{0}" does not exists.'.format(infilepath))

    lines = file2list(infilepath)

    renbaned_lines = get_renbaned_lines(lines, mark)

    list2file(outfilepath, renbaned_lines)
