import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_filter import process_files


def test_duplicate_file_names(tmp_path):
    """Files mapping to the same remark should not overwrite each other."""

    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    # 两个文件都包含同一标识符并拥有相同扩展名
    (source / "img_1234.jpg").write_text("a")
    (source / "holiday1234.jpg").write_text("b")

    # 构造参考表格
    reference = tmp_path / "ref.csv"
    reference.write_text("id,remark\n1234,beijing\n")

    process_files(str(source), str(target), str(reference))

    assert (target / "beijing.jpg").exists()
    assert (target / "beijing_1.jpg").exists()

