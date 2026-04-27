import re

VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\}\}")


def _resolve_path(data, path):
    current = data
    for segment in path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            raise KeyError(path)
    return current


def execute(self, input_data):
    """富文本模板渲染 - 替换{{变量}}并复制到剪贴板"""
    template_html = str(self.config.get("rich_text", "") or "")
    output_var = str(self.config.get("output_var", "rendered_html") or "rendered_html")
    missing_key_mode = str(
        self.config.get("missing_key_mode", "keep_placeholder")
        or "keep_placeholder"
    ).lower()
    data_var = str(self.config.get("data_var", "") or "")

    data_context = input_data
    if data_var:
        data_context = input_data.get(data_var)
        if data_context is None:
            raise ValueError(f"未找到模板数据变量: {data_var}")
        if not isinstance(data_context, dict):
            raise ValueError("模板数据必须是对象")

    def _replace(match):
        key = match.group(1)
        try:
            value = _resolve_path(data_context, key)
            return "" if value is None else str(value)
        except KeyError:
            if missing_key_mode == "keep_placeholder":
                return match.group(0)
            if missing_key_mode == "empty":
                return ""
            raise ValueError(f"模板变量缺失: {key}")

    rendered_html = VARIABLE_PATTERN.sub(_replace, template_html)

    try:
        import pyperclip
        pyperclip.copy(rendered_html)
        clipboard_status = "copied"
    except Exception:
        clipboard_status = "copy_failed"

    return {
        **input_data,
        output_var: rendered_html,
        f"{output_var}_clipboard_status": clipboard_status,
    }
