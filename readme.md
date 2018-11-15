# renban
テキストファイル中の見出しに指定フォーマットで連番を振る。

## Demo

```
$ python renban.py -i sample_input.md -o sample_output.md
```

- [sample_input.md](sample_input.md)
- [sample_output.md](sample_output.md)

## Requirement
- Python 3.6+

## Configuration

### Mark (@n や @@n の '@') を変える
たとえば '$' に変えたい場合は、

```
$ python --mark `$`
```

### @n で「第一章」を表示 ← この一連のロジックはどうなっている？
まだ優しいインターフェースは無い。コードを変える必要がある。ざっくり書いておく。

必要な作業は二つ。

一つ目。「@n で "第一章"」にあたる設定をつくる。

```python
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
```

RenbanMarkCounter() を使う。set_displayer() にコールバック関数をセットする。set_subsection() は「大見出しの番号を増やしたら中見出しや小見出しの番号はリセットする」的な依存を指定するもの。

二つ目。RenbanMarkCounter を組み込む。

```python
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
```

convert_to_renbaned_line() 関数。連番を挿入しない行だった場合は line を返す。連番を挿入する行だった場合は、_convert_to_renbaned_line() でつくった「（連番が付与された）新しい行内容」を返す。

## License
[MIT License](LICENSE)

## Author
[stakiran](https://github.com/stakiran)
