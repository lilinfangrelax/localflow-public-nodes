def execute(self, input_data):
    """读取 Excel / CSV 文件并输出 rows、columns、row_count 等结构化结果"""
    return {**input_data, self.config.get("output_var", "table_data"): {"rows": [], "columns": [], "row_count": 0}}
