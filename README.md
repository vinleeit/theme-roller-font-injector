# jQuery Theme

Convert theme from Theme Roller and webfont to Sales Force ready, just run and upload.

## Instruction

### Dependencies

### Running

> It is recommended to get [Python UV](https://docs.astral.sh/uv/) to run the following program.

Usage:

```sh
> uv run main.py --help
========================
usage: main.py [-h] --font-name FONT_NAME --font-zip FONT_ZIP --theme-zip THEME_ZIP --url URL

jQuery Theme

options:
  -h, --help            show this help message and exit
  --font-zip FONT_ZIP   The zip file for your webfont
  --theme-zip THEME_ZIP The zip file for your theme
```

Example:

```shell
uv run main.py \
--font-zip assets/webfontkit-20260729-011415.zip \
--theme-zip assets/jquery-mobile-theme-224859-0.zip
```

There are 2 folders generated:

- `.temp/`: if anything is wrong, you can check the modified/generated files.

- `output/`: where all the result is, upload these to your SF static resource.

### Contact

Arvin Lee | me@arvinlee.com
