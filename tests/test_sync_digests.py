from pathlib import Path

import pytest

from scripts.sync_digests import convert, main, output_name, sync

FIX = Path(__file__).parent / "fixtures" / "digests"
SAMPLE = (FIX / "2026-10-14_ニュースまとめ.md").read_text(encoding="utf-8")


def test_strips_impact_variants():
    out, removed = convert(SAMPLE)
    assert "自分への影響" not in out
    assert "続きの行" not in out
    assert removed == 4  # 3 種類の行 + ぶら下がる 1 行


def test_keeps_notes_and_body():
    out, _ = convert(SAMPLE)
    assert "- 第三者の検証は確認できなかった。" in out
    assert "- Bloombergの元記事にはアクセスしていない。" in out


def test_wikilinks_become_plain_text():
    out, _ = convert(SAMPLE)
    assert "[[" not in out
    assert "2026-10-14_Game Newsサイトの作り直し" in out and "Unity 6 の LTS" in out


def test_source_line_becomes_link():
    out, _ = convert(SAMPLE)
    assert "- 出典：[Google公式ブログ（2026-10-13）](https://blog.google/a)" in out
    assert "- 出典：[Ludeon Studios公式X](https://example.com/x)" in out


def test_frontmatter_is_converted():
    out, _ = convert(SAMPLE)
    fm = out.split("---")[1]
    assert 'title: "ニュースまとめ（2026-10-14）"' in fm  # title は必ずクォート
    assert "date: 2026-10-14" in fm and 'period: "2026-10-12〜2026-10-14"' in fm
    assert 'tags: ["ニュース", "AI", "ゲーム"]' in fm
    assert "type:" not in fm and "created:" not in fm


def test_h1_removed_from_body():  # タイトルはレイアウトが出すので本文からは消す
    body = convert(SAMPLE)[0].split("---", 2)[2]
    assert not any(line.startswith("# ") for line in body.splitlines())


def test_missing_created_raises():
    try:
        convert((FIX / "broken.md").read_text(encoding="utf-8"))
    except ValueError as e:
        assert "created" in str(e)
    else:
        raise AssertionError("ValueError が出ていない")


def test_output_name():
    assert output_name("2026-10-14_ニュースまとめ.md") == "2026-10-14.md"
    assert output_name("2026-10-14_ニュースまとめ_2.md") == "2026-10-14-2.md"


def test_sync_skips_broken_and_reports(tmp_path):
    report = sync(FIX, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-10-14-2.md", "2026-10-14.md"]
    assert any("broken.md" in line and "created" in line for line in report)
    assert any("2026-10-14.md" in line and "取り除いた行" in line and "4" in line for line in report)


def test_sync_reports_overwrite(tmp_path):
    sync(FIX, tmp_path)
    (tmp_path / "2026-10-14.md").write_text("old", encoding="utf-8")
    assert any("上書き" in line for line in sync(FIX, tmp_path))


def test_sync_reports_unchanged(tmp_path):
    sync(FIX, tmp_path)
    assert any("変更なし" in line for line in sync(FIX, tmp_path))


HEAD = "---\ncreated: 2026-10-14\ntags: [AI]\n---\n\n# タイトル\n"


def test_vault_note_lines_removed():
    out, removed = convert(HEAD + "本文\n※保管庫の中のメモ\n  ※保管庫：インデントつき\n次\n")
    assert "※保管庫" not in out and "本文" in out and "次" in out
    assert removed == 2


def test_obsidian_comments_removed():
    out, _ = convert(HEAD + "前%%インライン%%後\n%%\n複数行\nのコメント\n%%\n残る\n")
    assert "%%" not in out and "インライン" not in out and "複数行" not in out
    assert "前後" in out and "残る" in out


def test_html_comments_removed():
    out, _ = convert(HEAD + "前<!-- インライン -->後\n<!--\n複数行\n-->\n残る\n")
    assert "<!--" not in out and "インライン" not in out and "複数行" not in out
    assert "前後" in out and "残る" in out


def test_main_requires_src(monkeypatch, capsys):
    monkeypatch.delenv("DIGEST_SRC", raising=False)
    monkeypatch.setattr("sys.argv", ["sync_digests"])
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 2
    assert "DIGEST_SRC" in capsys.readouterr().err


@pytest.mark.parametrize("env, argv", [
    ("", []),              # 環境変数が空
    ("   ", []),           # 空白だけ
    (None, ["--src", ""]),  # --src に空文字
])
def test_main_rejects_empty_src(monkeypatch, capsys, env, argv):
    # 空の指定が Path("") = 今いるフォルダとして読まれないこと
    if env is None:
        monkeypatch.delenv("DIGEST_SRC", raising=False)
    else:
        monkeypatch.setenv("DIGEST_SRC", env)
    monkeypatch.setattr("sys.argv", ["sync_digests", *argv])
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 2
    assert "DIGEST_SRC" in capsys.readouterr().err
