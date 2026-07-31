import argparse
import re
import os
import shutil
import zipfile
from pathlib import Path
from yarl import URL


def set_font_source_url(css_content, prefix):
    # Matches url('...') or url("...") or url(...) without quotes
    pattern = r"url\((['\"]?)([^'\")]+)\1\)"

    def replacer(match):
        quote = match.group(1)
        path = match.group(2)
        return f"url({quote}{prefix}/{path}{quote})"

    return re.sub(pattern, replacer, css_content)


def extract_font_faces(css_content):
   # Matches @font-face { ... } blocks (non-greedy, handles nested braces poorly but fine for font-face which has no nesting)
    pattern = r"@font-face\s*\{[^}]*\}"

    matches = re.findall(pattern, css_content, re.DOTALL)
    return [m.strip() for m in matches]


def insert_font_faces_into_theme(theme_content, font_face_blocks):
    """
    Insert font_face_blocks right after the `html { ... }` rule
    and before the `body,\ninput, ...` rule.
    """
    marker_pattern = r"(html\s*\{[^}]*\}\s*)(body\s*,)"
    match = re.search(marker_pattern, theme_content)

    if not match:
        raise ValueError(
            "Could not find insertion point (html {...} followed by body, ...)")

    font_faces_text = "\n\n".join(font_face_blocks)

    new_theme = (
        theme_content[:match.end(1)]
        + "\n" + font_faces_text + "\n\n"
        + theme_content[match.start(2):]
    )
    return new_theme


def zip_folder_contents(folder_path, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                # arcname = path relative to folder_path (not including folder_path itself)
                arcname = os.path.relpath(file_path, start=folder_path)
                zf.write(file_path, arcname=arcname)


def extract_font_family_name(font_face_block):
    """
    Extracts the font-family value from a single @font-face block.
    e.g. from "@font-face { font-family: 'wildcrazymedium'; ... }"
    returns "'wildcrazymedium'"
    """
    match = re.search(r"font-family:\s*([^;]+);", font_face_block)
    if not match:
        raise ValueError("No font-family found in @font-face block")
    return match.group(1).strip()


def update_global_font_family(css_content, new_font_family):
    """
    Updates the font-family value inside the
    body, input, select, textarea, button, .ui-btn { ... } rule,
    preserving the /*{global-font-family}*/ comment.
    """
    pattern = r"(font-family:\s*)[^;]+?(\s*/\*\{global-font-family\}\*/)"
    replacement = rf"\1{new_font_family}\2"
    return re.sub(pattern, replacement, css_content, count=1)


def process_font(
        font_name: str,
        output: str,
        temp_path: str,
        url: URL,
        zip_path: str,):

    temp_path_font = f'{temp_path}/font'
    os.mkdir(temp_path_font)

    # Extract all to temporary folder
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(path=temp_path_font)

    # Set the font source url
    stylesheet_path = f'{temp_path_font}/stylesheet.css'
    with open(stylesheet_path, 'r') as f:
        css = f.read()
        new_css = set_font_source_url(css, url/'resource' / font_name)
        with open(stylesheet_path, 'w') as f:
            f.write(new_css)

    # Zip the modified files
    zip_folder_contents(temp_path_font, f'{output}/{font_name}.zip')

    # Get all the font faces in the stylesheet
    return extract_font_faces(new_css)


def process_theme(
        output: str,
        temp_path: str,
        theme_name: str,
        zip_path: str,
        fonts: list[str] = [],):
    temp_path_theme = f'{temp_path}/themes'

    # Extract all to temporary folder
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        all_files = zip_ref.namelist()
        folder_files = [
            item for item in all_files
            # Must be in themes folder
            if item.startswith('themes/')
            # Excludes empty folders
            and not item.endswith('/')
            # Excludes the mininmized css
            and not item.endswith('CustomTheme.min.css')
        ]
        zip_ref.extractall(path=temp_path, members=folder_files)

    # Add font face and update the font-family property
    with open(f'{temp_path}/themes/CustomTheme.css', 'r') as f:
        theme_css = f.read()

        updated_theme = insert_font_faces_into_theme(theme_css, fonts)
        font_family_name = extract_font_family_name(fonts[0])
        updated_theme = update_global_font_family(
            updated_theme,
            font_family_name,
        )

        with open(f'{temp_path}/themes/CustomTheme.css', 'w') as f:
            f.write(updated_theme)

    # Rename the CustomTheme.css file with theme name
    os.rename(f'{temp_path}/themes/CustomTheme.css',
              f'{temp_path}/themes/{theme_name}.css')

    # Zip the modified files
    zip_folder_contents(temp_path_theme, f'{output}/{theme_name}.zip')


def main():
    THEME_NAME = 'jquery-ui.custom'
    TEMP_PATH = Path('./.temp/')
    OUTPUT_PATH = Path('./output/')

    parser = argparse.ArgumentParser(description='jQuery Theme')
    parser.add_argument('--font-name',
                        required=True,
                        help='The name for your font resource')
    parser.add_argument('--font-zip',
                        required=True,
                        help='The zip file for your webfont')
    parser.add_argument('--theme-zip',
                        required=True,
                        help='The zip file for your theme')
    parser.add_argument(
        '--url',
        required=True,
        help='The url to your Payment2us Merchang Facility'
    )

    args = parser.parse_args()
    font_name = args.font_name
    font_zip = args.font_zip
    theme_zip = args.theme_zip
    url = URL(args.url)

    if TEMP_PATH.exists():
        shutil.rmtree(TEMP_PATH)
    TEMP_PATH.mkdir(parents=True, exist_ok=True)

    if OUTPUT_PATH.exists():
        shutil.rmtree(OUTPUT_PATH)
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    # Processed first, neeeded by theme
    fonts = process_font(
        font_name=font_name,
        output=OUTPUT_PATH,
        temp_path=str(TEMP_PATH),
        url=url,
        zip_path=font_zip,)

    process_theme(
        fonts=fonts,
        output=OUTPUT_PATH,
        temp_path=str(TEMP_PATH),
        theme_name=THEME_NAME,
        zip_path=theme_zip,)


if __name__ == "__main__":
    main()
