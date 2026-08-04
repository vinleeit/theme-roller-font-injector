import argparse
import os
import re
import shutil
import zipfile
from pathlib import Path


def set_font_source_url(css_content: str, prefix: str) -> str:
    pattern = r"url\((['\"]?)([^'\")]+)\1\)"

    def replacer(match):
        quote = match.group(1)
        path = match.group(2)
        if path.startswith(("http://", "https://", "data:", "//")):
            return match.group(0)  # leave untouched
        return f"url({quote}{prefix}/{path}{quote})"

    return re.sub(pattern, replacer, css_content)


def extract_font_faces(css_content: str) -> list[str]:
    # Matches @font-face { ... } blocks (non-greedy, handles nested braces poorly but fine for font-face which has no nesting)
    pattern = r"@font-face\s*\{[^}]*\}"
    matches: list[str] = re.findall(pattern, css_content, re.DOTALL)
    return [set_font_source_url(m.strip(), "/font") for m in matches]


def insert_font_faces_into_theme(theme_content, font_face_blocks):
    """
    Insert font_face_blocks right after the `html { ... }` rule
    and before the `body,\ninput, ...` rule.
    """
    marker_pattern = r"(html\s*\{[^}]*\}\s*)(body\s*,)"
    match = re.search(marker_pattern, theme_content)

    if not match:
        raise ValueError(
            "Could not find insertion point (html {...} followed by body, ...)"
        )

    font_faces_text = "\n\n".join(font_face_blocks)

    new_theme = (
        theme_content[: match.end(1)]
        + "\n"
        + font_faces_text
        + "\n\n"
        + theme_content[match.start(2) :]
    )
    return new_theme


def zip_folder_contents(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # arcname = path relative to folder_path (not including folder_path itself)
                arcname = os.path.relpath(file_path, start=folder_path)
                zf.write(file_path, arcname=arcname)


def extract_font_family_name(font_face_blocks: list[str]):
    """
    Extracts the font-family value from a single @font-face block.
    e.g. from "@font-face { font-family: 'wildcrazymedium'; ... }"
    returns "'wildcrazymedium'"
    """

    result = []
    for font_face_block in font_face_blocks:
        match = re.search(r"font-family:\s*([^;]+);", font_face_block)
        if not match:
            raise ValueError("No font-family found in @font-face block")
        result.append(match.group(1).strip())
    return ",".join(result)


def update_global_font_family(css_content, new_font_family):
    """
    Updates the font-family value inside the
    body, input, select, textarea, button, .ui-btn { ... } rule,
    preserving the /*{global-font-family}*/ comment.
    """
    pattern = r"(font-family:\s*)[^;]+?(\s*/\*\{global-font-family\}\*/)"
    replacement = rf"\1{new_font_family}\2"
    return re.sub(pattern, replacement, css_content, count=1)


def should_include(item):
    if item.endswith("jquery.mobile.icons.min.css"):
        return True
    # Excludes the mininmized css
    return not item.endswith(".min.css")


def process_theme(
    output: str,
    temp_path: str,
    theme_name: str,
    zip_theme_path: str,
    zip_font_path: str,
):
    temp_path_theme = f"{temp_path}/themes"
    temp_path_font = f"{temp_path_theme}/font"
    os.mkdir(temp_path_theme)
    os.mkdir(temp_path_font)
    theme_filename = ""

    # Extract all themes to temporary location
    with zipfile.ZipFile(zip_theme_path, "r") as zip_ref:
        all_files = zip_ref.namelist()
        folder_files = [
            item
            for item in all_files
            # Must be in themes folder
            if item.startswith("themes/")
            # Excludes empty folders
            and not item.endswith("/")
            and should_include(item)
        ]
        zip_ref.extractall(path=temp_path, members=folder_files)

        files = [
            f.stem
            for f in Path(temp_path_theme).glob("*.css")
            if f.is_file() and f.name not in ["jquery.mobile.icons.min.css"]
        ]

        if len(files) != 1:
            exit(0)

        theme_filename = f"{temp_path_theme}/{files[0]}.css"

    # Extract all font to folder inside temporary themes
    with zipfile.ZipFile(zip_font_path, "r") as zip_ref:
        zip_ref.extractall(path=temp_path_font)

    stylesheet_path = f"{temp_path_font}/stylesheet.css"
    fonts = []
    with open(stylesheet_path, "r") as f:
        css = f.read()
        fonts = extract_font_faces(css)

    # Add font face and update the font-family property
    with open(theme_filename, "r") as f:
        theme_css = f.read()

        updated_theme = insert_font_faces_into_theme(theme_css, fonts)
        font_family_name = extract_font_family_name(fonts)
        updated_theme = update_global_font_family(
            updated_theme,
            font_family_name,
        )

        with open(theme_filename, "w") as f:
            f.write(updated_theme)

    # Rename the CustomTheme.css file with theme name
    os.rename(theme_filename, f"{temp_path_theme}/{theme_name}.css")

    # Zip the modified files
    zip_folder_contents(temp_path_theme, f"{output}/{theme_name}.zip")


def main():
    THEME_NAME = "jquery-ui.custom"
    TEMP_PATH = Path("./.temp/")
    OUTPUT_PATH = Path("./output/")

    parser = argparse.ArgumentParser(description="jQuery Theme")
    _ = parser.add_argument(
        "--font-zip", required=True, help="The zip file for your webfont", type=str
    )
    _ = parser.add_argument(
        "--theme-zip", required=True, help="The zip file for your theme", type=str
    )

    args = parser.parse_args()
    font_zip = str(args.font_zip)
    theme_zip = str(args.theme_zip)

    if TEMP_PATH.exists():
        shutil.rmtree(TEMP_PATH)
    TEMP_PATH.mkdir(parents=True, exist_ok=True)

    if OUTPUT_PATH.exists():
        shutil.rmtree(OUTPUT_PATH)
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    process_theme(
        output=OUTPUT_PATH,
        temp_path=str(TEMP_PATH),
        theme_name=THEME_NAME,
        zip_theme_path=theme_zip,
        zip_font_path=font_zip,
    )


if __name__ == "__main__":
    main()
