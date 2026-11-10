# -*- coding: utf-8 -*-
"""pptx → pdf → 每页 png，用于目检。

本机没有 Microsoft YaHei，预览时在临时副本里把字体换成 Hiragino Sans GB，正式文件不动。
"""
import pathlib, shutil, subprocess, sys, tempfile, zipfile

PREVIEW_FONT = "Hiragino Sans GB"


def _preview_copy(src, dst):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".xml"):
                data = data.replace(b'typeface="Microsoft YaHei"',
                                    f'typeface="{PREVIEW_FONT}"'.encode())
            zout.writestr(item, data)


def render(pptx_path, out_dir, dpi=60):
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(pptx_path).stem
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td) / f"{stem}.pptx"
        _preview_copy(pptx_path, tmp)
        profile = pathlib.Path(td) / "lo-profile"          # 独立配置目录，避免与其他 soffice 实例冲突
        subprocess.run(["soffice", f"-env:UserInstallation={profile.as_uri()}", "--headless",
                        "--convert-to", "pdf", "--outdir", str(out), str(tmp)],
                       check=True, capture_output=True)
    pdf = out / f"{stem}.pdf"
    for old in out.glob("s-*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf), str(out / "s")], check=True)
    return sorted(out.glob("s-*.png"), key=lambda p: int(p.stem.split("-")[1]))


if __name__ == "__main__":
    print("\n".join(str(p) for p in render(sys.argv[1], sys.argv[2])))
