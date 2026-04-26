def execute(self, input_data):
    """使用 {{var}} 模板变量替换生成文本"""
    return {**input_data, self.config.get("output_var", "rendered_text"): ""}
